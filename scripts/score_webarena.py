"""Publish blinded verdicts with human labels joined only after execution."""

import argparse
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ARMS = ("baseline", "selective", "review_all")
BINARY = {"Successful": True, "Unsuccessful": False}


def tokens(calls):
    return sum(c["prompt_tokens"] + c["completion_tokens"] for c in calls)


def export_rows(catalog, runs):
    records = []
    for item in catalog:
        name = item["task"] + "__" + item["agent"] + ".json"
        labels = [pair[1].strip() for pair in item["labels"]]
        row = {
            "task": item["task"],
            "agent": item["agent"],
            "split": item["split"],
            "labels": labels,
        }
        path = runs / name
        if path.is_file():
            trace = json.loads(path.read_text())
            if any(trace[k] != item[k] for k in ("task", "agent", "split")):
                raise ValueError("Result identity mismatch")
            row.update(
                {
                    k: trace[k]
                    for k in (*ARMS, "trigger", "citations", "source_sha256", "model")
                }
            )
            for prefix in ("base", "review"):
                calls = trace[prefix + "_calls"]
                row[prefix + "_tokens"] = tokens(calls)
                row[prefix + "_call_count"] = len(calls)
            row["screening_parse_errors"] = trace["frame_scores"].count(0)
            row["status"] = "complete"
        else:
            error = runs / "errors" / name
            row["status"] = (
                json.loads(error.read_text())["error"]
                if error.is_file()
                else "no_completed_verdict"
            )
        records.append(row)
    return records


def stats(rows, arm):
    scored = [r for r in rows if r["labels"][0] in BINARY]
    positives = [r for r in scored if BINARY[r["labels"][0]]]
    negatives = [r for r in scored if not BINARY[r["labels"][0]]]
    tp = sum(r[arm] for r in positives)
    fp = sum(r[arm] for r in negatives)
    reviewed = [
        r
        for r in rows
        if not r["baseline"]
        and (arm == "review_all" or (arm == "selective" and r["trigger"]))
    ]
    return {
        "completed": len(rows),
        "positives": len(positives),
        "negatives": len(negatives),
        "true_accept": tp,
        "false_accept": fp,
        "false_reject": len(positives) - tp,
        "recall": tp / len(positives) if positives else None,
        "false_accept_rate": fp / len(negatives) if negatives else None,
        "success_precision": tp / (tp + fp) if tp + fp else None,
        "rescued": sum(not r["baseline"] and r[arm] for r in positives),
        "new_false_accept": sum(not r["baseline"] and r[arm] for r in negatives),
        "reread": len(reviewed),
        "logical_tokens": sum(r["base_tokens"] for r in rows)
        + sum(r["review_tokens"] for r in reviewed),
        "logical_calls": sum(r["base_call_count"] for r in rows)
        + sum(r["review_call_count"] for r in reviewed),
    }


def paired_intervals(rows, arm, draws=5000):
    groups = defaultdict(lambda: [0, 0, 0, 0])
    for row in rows:
        label = row["labels"][0]
        if label not in BINARY:
            continue
        offset = 0 if BINARY[label] else 2
        group = groups[row["task"]]
        group[offset] += int(row[arm]) - int(row["baseline"])
        group[offset + 1] += 1
    values = list(groups.values())
    samples = [[], []]
    rng = random.Random(20261105)
    for _ in range(draws):
        selected = rng.choices(values, k=len(values)) if values else []
        totals = [sum(v[j] for v in selected) for j in range(4)]
        for j in (0, 1):
            if totals[2 * j + 1]:
                samples[j].append(100 * totals[2 * j] / totals[2 * j + 1])

    def bounds(sample):
        x = sorted(sample)
        return (
            [round(x[int(p * (len(x) - 1))], 3) for p in (0.025, 0.975)] if x else None
        )

    return {
        "task_groups": len(values),
        "draws": draws,
        "recall_delta_pp": bounds(samples[0]),
        "false_accept_delta_pp": bounds(samples[1]),
    }


def check_protocol(records):
    identities = [(row["task"], row["agent"]) for row in records]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate trajectory in public export")
    task_split = {}
    for row in records:
        if task_split.setdefault(row["task"], row["split"]) != row["split"]:
            raise ValueError("A task crossed the development/test boundary")
        if row["status"] != "complete":
            continue
        if any(type(row[a]) is not bool for a in ARMS):
            raise ValueError("Expected a binary final verdict in each arm")
        if row["baseline"] and not (row["selective"] and row["review_all"]):
            raise ValueError("A baseline success must bypass review")
        selective = row["review_all"] if row["trigger"] else row["baseline"]
        if row["selective"] != selective:
            raise ValueError("Selective verdict does not match the frozen trigger")


def summarize(records):
    check_protocol(records)
    report = {}
    for split in ("dev", "test"):
        members = [r for r in records if r["split"] == split]
        rows = [r for r in members if r["status"] == "complete"]
        group = {
            "expected": len(members),
            "status": dict(Counter(r["status"] for r in members)),
            "expected_tasks": len({r["task"] for r in members}),
            "completed_tasks": len({r["task"] for r in rows}),
            "ambiguous_primary": sum(r["labels"][0] not in BINARY for r in rows),
            "disputed_completed": sum(len(set(r["labels"])) > 1 for r in rows),
            "screening_parse_errors": sum(r["screening_parse_errors"] for r in rows),
        }
        group["arms"] = {a: stats(rows, a) for a in ARMS}
        unanimous = [r for r in rows if len(set(r["labels"])) == 1]
        group["unanimous_only"] = {a: stats(unanimous, a) for a in ARMS}
        group["intervals"] = {a: paired_intervals(rows, a) for a in ARMS[1:]}
        if split == "test":
            selective = group["arms"]["selective"]
            group["release_guard"] = {
                "full_coverage": len(rows) == len(members) and bool(members),
                "recovered_any": selective["rescued"] > 0,
                "no_new_false_accepts": selective["new_false_accept"] == 0,
            }
            group["recommend_automatic_reversal"] = all(group["release_guard"].values())
        report[split] = group
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", type=Path, help="Public, per-trajectory JSONL")
    parser.add_argument("summary", type=Path)
    parser.add_argument("--catalog", type=Path)
    parser.add_argument("--runs", type=Path)
    args = parser.parse_args()
    if (args.catalog is None) != (args.runs is None):
        parser.error("Supply --catalog and --runs together.")
    if args.catalog:
        records = export_rows(json.loads(args.catalog.read_text()), args.runs)
        args.records.parent.mkdir(parents=True, exist_ok=True)
        args.records.write_text(
            "".join(json.dumps(r, sort_keys=True) + "\n" for r in records)
        )
    else:
        records = [json.loads(line) for line in args.records.read_text().splitlines()]
    args.summary.write_text(json.dumps(summarize(records), indent=2) + "\n")


if __name__ == "__main__":
    main()
