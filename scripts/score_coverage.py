"""Join annotations after inference; retain coverage gaps and paired task units."""

import argparse
import json
from pathlib import Path

from score_webarena import BINARY, paired_intervals, tokens


def export(catalog, baseline, runs, variants):
    rows = []
    for item in catalog:
        name = item["task"] + "__" + item["agent"] + ".json"
        row = {k: item[k] for k in ("task", "agent", "split")}
        row["labels"] = [v.strip() for _, v in item["labels"]]
        path = baseline / name
        if not path.exists():
            row["status"] = "missing_baseline"
            rows.append(row)
            continue
        if path.exists():
            first = json.loads(path.read_text())
            row.update(
                {
                    k: first[k]
                    for k in ("baseline", "selective", "review_all", "source_sha256")
                }
            )
            row["baseline_tokens"] = tokens(first["base_calls"])
            row["review_all_tokens"] = row["baseline_tokens"] + tokens(
                first["review_calls"]
            )
            row["selective_tokens"] = row["baseline_tokens"] + (
                tokens(first["review_calls"]) if first["trigger"] else 0
            )
        for variant in variants:
            path = runs / ("audited" if variant == "unaudited" else variant) / name
            if path.exists():
                v = json.loads(path.read_text())
                if (
                    v["source_sha256"] != row["source_sha256"]
                    or v["baseline"] != row["baseline"]
                ):
                    raise ValueError("Mismatched trajectory or baseline")
                if type(v["accepted"]) is not bool or (
                    row["baseline"] and not v["accepted"]
                ):
                    raise ValueError(
                        "Invalid final verdict or modified baseline acceptance"
                    )
                candidate = v.get("candidate")
                calls = v["new_calls"]
                row[variant] = v["accepted"]
                if variant == "unaudited" and candidate:
                    row[variant] = candidate["accepted_without_audit"]
                    calls = calls[:-1]
                row[variant + "_tokens"] = row["baseline_tokens"] + tokens(calls)
                row[variant + "_calls"] = len(calls)
        rows.append(row)
    keys = [(r["task"], r["agent"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate trajectory")
    return rows


def metrics(rows, arm):
    complete = [r for r in rows if arm in r]
    scored = [r for r in complete if r["labels"][0] in BINARY]
    pos = [r for r in scored if BINARY[r["labels"][0]]]
    neg = [r for r in scored if not BINARY[r["labels"][0]]]
    tp, fp = sum(r[arm] for r in pos), sum(r[arm] for r in neg)
    return {
        "expected": len(rows),
        "complete": len(complete),
        "unscored_primary": len(complete) - len(scored),
        "positives": len(pos),
        "negatives": len(neg),
        "true_accept": tp,
        "false_accept": fp,
        "recall": tp / len(pos) if pos else None,
        "false_accept_rate": fp / len(neg) if neg else None,
        "rescued": sum(r[arm] and not r["baseline"] for r in pos),
        "new_false_accept": sum(r[arm] and not r["baseline"] for r in neg),
        "logical_tokens": sum(r[arm + "_tokens"] for r in complete),
        "task_count": len({r["task"] for r in complete}),
        "intervals": paired_intervals(complete, arm),
    }


def summarize(rows, variants):
    result = {}
    for split in sorted({r["split"] for r in rows}):
        selected = [r for r in rows if r["split"] == split]
        arms = ["baseline", "selective", "review_all", *variants]
        result[split] = {
            "arms": {a: metrics(selected, a) for a in arms},
            "unanimous": {
                a: metrics([r for r in selected if len(set(r["labels"])) == 1], a)
                for a in arms
            },
            "disputed": sum(len(set(r["labels"])) > 1 for r in selected),
        }
    return result


def main():
    p = argparse.ArgumentParser()
    for name in ("catalog", "baseline", "runs", "out"):
        p.add_argument(name, type=Path)
    p.add_argument("--variants", nargs="+", required=True)
    args = p.parse_args()
    rows = export(
        json.loads(args.catalog.read_text()), args.baseline, args.runs, args.variants
    )
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "trajectories.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    )
    (args.out / "summary.json").write_text(
        json.dumps(summarize(rows, args.variants), indent=2) + "\n"
    )
    print("Exported", len(rows), "trajectories")


if __name__ == "__main__":
    main()
