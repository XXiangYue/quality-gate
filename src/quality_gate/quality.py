"""Independent result verification. Candidate output is never its own oracle."""

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import random
import time

from .common import ROOT, digest, freeze, percentile, rate, read_jsonl, write_json


def scores(labels, predictions):
    """Verifier implementation, independently checked against sklearn reference."""
    n = len(labels)
    tp = sum(a == b == 1 for a, b in zip(labels, predictions))
    fp = sum(a == 0 and b == 1 for a, b in zip(labels, predictions))
    fn = sum(a == 1 and b == 0 for a, b in zip(labels, predictions))
    return {
        "accuracy": sum(a == b for a, b in zip(labels, predictions)) / n,
        "precision": tp / (tp + fp) if tp + fp else 0,
        "recall": tp / (tp + fn) if tp + fn else 0,
        "f1": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0,
    }


def verify_artifact(candidate, oracle):
    c, o = candidate, oracle
    checks = {}
    rows = c.get("predictions", [])
    ids = [r.get("id") for r in rows if isinstance(r, dict)]
    checks["prediction_rows"] = (
        isinstance(rows, list) and len(ids) == len(rows) and bool(rows)
    )
    checks["unique_ids"] = len(ids) == len(set(map(str, ids)))
    checks["sample_ids"] = set(ids) == set(o["labels"])
    checks["label_values"] = all(
        type(r.get("prediction")) is int and r["prediction"] in (0, 1)
        for r in rows
        if isinstance(r, dict)
    )
    checks["data_version"] = c.get("data_sha256") == o["data_sha256"]
    checks["split_version"] = c.get("split_id") == o["split_id"]
    checks["source_links"] = c.get("report_prediction_sha256") == digest(rows)
    checks["run_receipt"] = c.get("run_receipt") == o["run_receipt"]
    claimed = c.get("metrics", {})
    checks["denominator"] = type(claimed.get("n")) is int and claimed.get("n") == len(
        o["labels"]
    )
    if checks["sample_ids"] and checks["unique_ids"] and checks["label_values"]:
        by_id = {r["id"]: r["prediction"] for r in rows}
        wanted = scores(list(o["labels"].values()), [by_id[i] for i in o["labels"]])
    else:
        wanted = {}
    for name in ("accuracy", "precision", "recall", "f1"):
        value = claimed.get(name)
        checks["metric_" + name] = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and name in wanted
            and abs(value - wanted[name]) <= 1e-6
        )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failures": [k for k, v in checks.items() if not v],
    }


def verify_business(candidate, oracle):
    c, o = candidate, oracle
    checks = {
        "ticket_status": c.get("ticket", {}).get("status") == o["ticket_status"],
        "ticket_version": c.get("ticket", {}).get("version") == o["ticket_version"],
        "knowledge_version": c.get("knowledge", {}).get("version")
        == o["knowledge_version"],
        "knowledge_hash": c.get("knowledge", {}).get("content_hash")
        == o["knowledge_hash"],
        "linked_version": c.get("ticket", {}).get("knowledge_version")
        == o["linked_version"],
        "scope_integrity": c.get("ticket", {}).get("scope") == o["scope"],
        "no_unauthorized_write": c.get("unauthorized_writes") == 0,
        "one_business_effect": c.get("new_versions") == o["new_versions"],
        "approval_bound": c.get("approval_digest") == o["approval_digest"],
        "operation_receipt": c.get("receipt_hash") == o["receipt_hash"],
        "index_current": c.get("knowledge", {}).get("indexed_version")
        == o["knowledge_version"],
        "complete_state": c.get("operation_state") == o["operation_state"],
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "failures": [k for k, v in checks.items() if not v],
    }


class OracleError(ValueError):
    pass


def verify(domain, candidate, oracle, *, required_checks=None):
    required = (
        ("labels", "data_sha256", "split_id", "run_receipt")
        if domain == "artifact"
        else (
            "ticket_status",
            "ticket_version",
            "knowledge_version",
            "knowledge_hash",
            "linked_version",
            "scope",
            "new_versions",
            "approval_digest",
            "receipt_hash",
            "operation_state",
        )
    )
    if not isinstance(oracle, dict) or any(k not in oracle for k in required):
        raise OracleError(
            "The independent oracle is invalid; do not count a candidate failure"
        )
    if domain == "artifact" and (
        not isinstance(oracle["labels"], dict) or not oracle["labels"]
    ):
        raise OracleError("Empty/invalid label oracle")
    if not isinstance(candidate, dict):
        return {
            "passed": False,
            "checks": {"parse_contract": False},
            "failures": ["parse_contract"],
        }
    try:
        result = (verify_artifact if domain == "artifact" else verify_business)(
            candidate, oracle
        )
        if required_checks is not None:
            result["checks"] = {
                k: v for k, v in result["checks"].items() if k in required_checks
            }
            result["passed"] = all(result["checks"].values())
            result["failures"] = [k for k, v in result["checks"].items() if not v]
        return result
    except (ValueError, TypeError, KeyError, AttributeError, ZeroDivisionError):
        return {
            "passed": False,
            "checks": {"parse_contract": False},
            "failures": ["parse_contract"],
        }


def format_only(domain, candidate):
    if domain == "artifact":
        return bool(candidate.get("predictions")) and isinstance(
            candidate.get("metrics"), dict
        )
    return candidate.get("success") is True and isinstance(
        candidate.get("ticket"), dict
    )


def reference_artifact(rng, group):
    # Trusted reference uses sklearn's implementation, not scores()/the verifier.
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

    y = [rng.randrange(2) for _ in range(24)]
    pred = [a if rng.random() < 0.8 else 1 - a for a in y]
    labels = {f"{group}-{i}": a for i, a in enumerate(y)}
    rows = [{"id": key, "prediction": b} for key, b in zip(labels, pred)]
    metrics = dict(
        n=len(y),
        accuracy=accuracy_score(y, pred),
        precision=precision_score(y, pred, zero_division=0),
        recall=recall_score(y, pred, zero_division=0),
        f1=f1_score(y, pred, zero_division=0),
    )
    oracle = {
        "labels": labels,
        "split_id": "test-" + group,
        "data_sha256": digest(group),
        "run_receipt": digest([group, "trusted-run"]),
    }
    candidate = {
        "predictions": rows,
        "metrics": metrics,
        "split_id": oracle["split_id"],
        "data_sha256": oracle["data_sha256"],
        "run_receipt": oracle["run_receipt"],
        "report_prediction_sha256": digest(rows),
    }
    return candidate, oracle


def reference_business(rng, group):
    v = rng.randrange(2, 100)
    o = {
        "ticket_status": "closed",
        "ticket_version": v + 1,
        "knowledge_version": v + 1,
        "knowledge_hash": digest(group),
        "linked_version": v + 1,
        "scope": "team-" + group,
        "new_versions": 1,
        "approval_digest": digest([group, "approved"]),
        "receipt_hash": digest([group, "receipt"]),
        "operation_state": "verified",
    }
    c = {
        "success": True,
        "ticket": {
            "status": "closed",
            "version": v + 1,
            "knowledge_version": v + 1,
            "scope": o["scope"],
        },
        "knowledge": {
            "version": v + 1,
            "content_hash": o["knowledge_hash"],
            "indexed_version": v + 1,
        },
        "unauthorized_writes": 0,
        "new_versions": 1,
        "approval_digest": o["approval_digest"],
        "receipt_hash": o["receipt_hash"],
        "operation_state": "verified",
    }
    return c, o


def build_corpus():
    """Labels follow controlled construction/mutation, never V1 predictions."""
    rng = random.Random(2026110103)
    output = []
    for split, count in (("dev", 50), ("test", 100)):
        for domain in ("artifact", "business"):
            for i in range(count):
                group = f"{split}-{domain}-{i}"
                candidate, oracle = (
                    reference_artifact if domain == "artifact" else reference_business
                )(rng, group)
                valid = i % 2 == 0
                mutation = None
                if valid and domain == "artifact":
                    rng.shuffle(candidate["predictions"])
                    candidate["report_prediction_sha256"] = digest(
                        candidate["predictions"]
                    )
                    candidate["irrelevant_notes"] = "合法元数据不影响结果"
                if not valid:
                    mutation = (i // 2) % 5 + (0 if split == "dev" else 5)
                    if domain == "artifact":
                        actions = [
                            lambda: candidate["predictions"].pop(),
                            lambda: candidate["predictions"].append(
                                copy.deepcopy(candidate["predictions"][0])
                            ),
                            lambda: candidate.update(split_id="wrong"),
                            lambda: candidate.update(data_sha256="wrong"),
                            lambda: candidate.update(run_receipt="wrong"),
                            lambda: candidate.update(report_prediction_sha256="wrong"),
                            lambda: candidate["metrics"].update(n=1),
                            lambda: candidate["metrics"].update(accuracy=1.5),
                            lambda: candidate["metrics"].update(f1=-1),
                            lambda: candidate["predictions"][0].update(prediction=2),
                        ]
                    else:
                        actions = [
                            lambda: candidate["ticket"].update(status="open"),
                            lambda: candidate["ticket"].update(version=0),
                            lambda: candidate["knowledge"].update(version=0),
                            lambda: candidate["knowledge"].update(content_hash="wrong"),
                            lambda: candidate["ticket"].update(knowledge_version=0),
                            lambda: candidate["ticket"].update(scope="other"),
                            lambda: candidate.update(unauthorized_writes=1),
                            lambda: candidate.update(new_versions=2),
                            lambda: candidate.update(approval_digest="wrong"),
                            lambda: candidate.update(receipt_hash="wrong"),
                        ]
                    actions[mutation]()
                output.append(
                    {
                        "id": group,
                        "parent_group": group,
                        "split": split,
                        "domain": domain,
                        "origin": "constructed_reference_and_controlled_mutation",
                        "valid": valid,
                        "mutation": mutation,
                        "candidate": candidate,
                        "oracle": oracle,
                    }
                )
    return output


def evaluate_lab(out: Path):
    cases = build_corpus()
    metric_checks = [
        "metric_accuracy",
        "metric_precision",
        "metric_recall",
        "metric_f1",
    ]
    mutant_config = {
        "artifact": [
            ["sample_ids", "source_links", *metric_checks],
            ["unique_ids", "source_links", *metric_checks],
            ["split_version"],
            ["data_version"],
            ["run_receipt"],
            ["source_links"],
            ["denominator"],
            ["metric_accuracy"],
            ["metric_f1"],
            ["label_values", "source_links", *metric_checks],
        ],
        "business": [
            [x]
            for x in (
                "ticket_status",
                "ticket_version",
                "knowledge_version",
                "knowledge_hash",
                "linked_version",
                "scope_integrity",
                "no_unauthorized_write",
                "one_business_effect",
                "approval_bound",
                "operation_receipt",
            )
        ],
    }
    freeze(
        out,
        {
            "project": "P3",
            "seed": 2026110103,
            "corpus_sha256": digest(cases),
            "dev": 100,
            "test": 200,
            "arms": ["V0", "V1"],
            "primary": "false acceptance and false rejection",
            "origin": "constructed labeled artifacts, not production incidents",
            "mutant_config": mutant_config,
            "code_sha256": digest(Path(__file__).read_bytes()),
        },
    )
    if (out / "summary.json").exists():
        return json.loads((out / "summary.json").read_text())
    write_json(out / "corpus.json", cases)
    records = []
    for case in cases:
        for arm in ("V0", "V1"):
            t = time.perf_counter()
            verdict = (
                {"passed": format_only(case["domain"], case["candidate"])}
                if arm == "V0"
                else verify(case["domain"], case["candidate"], case["oracle"])
            )
            records.append(
                {
                    "id": case["id"],
                    "split": case["split"],
                    "domain": case["domain"],
                    "arm": arm,
                    "valid": case["valid"],
                    "passed": verdict["passed"],
                    "correct": verdict["passed"] == case["valid"],
                    "failures": verdict.get("failures", []),
                    "ms": (time.perf_counter() - t) * 1000,
                }
            )
    write_json(out / "verdicts.json", records)
    summary = {}
    for arm in ("V0", "V1"):
        rows = [r for r in records if r["split"] == "test" and r["arm"] == arm]
        invalid = [r for r in rows if not r["valid"]]
        valid = [r for r in rows if r["valid"]]
        summary[arm] = {
            "false_acceptance": rate(sum(r["passed"] for r in invalid), len(invalid)),
            "false_rejection": rate(sum(not r["passed"] for r in valid), len(valid)),
            "p95_static_ms": percentile([r["ms"] for r in rows], 0.95),
            "n": len(rows),
        }
    # Explicit code/config mutations remove one verification requirement. Their
    # detection is a release-regression experiment, separate from artifact labels.
    mutations = []
    test_invalid = [c for c in cases if not c["valid"]]
    for domain in ("artifact", "business"):
        for kind in range(10):
            # Predeclared defective releases omit a check/group. No label or
            # observed failure is used to choose what to disable after test.
            disabled = set(mutant_config[domain][kind])
            changed = []
            for c in [x for x in test_invalid if x["domain"] == domain]:
                before = verify(domain, c["candidate"], c["oracle"])
                required_checks = set(before["checks"]) - disabled
                changed_release = verify(
                    domain, c["candidate"], c["oracle"], required_checks=required_checks
                )
                if changed_release["passed"] != before["passed"]:
                    changed.append(c["id"])
            mutations.append(
                {
                    "domain": domain,
                    "mutation": kind,
                    "disabled_checks": sorted(disabled),
                    "new_false_accepts": changed,
                    "detected": bool(changed),
                }
            )
    write_json(out / "release_mutations.json", mutations)
    controls = []
    for domain in ("artifact", "business"):
        subset = [c for c in cases if c["split"] == "test" and c["domain"] == domain]
        first = [verify(domain, c["candidate"], c["oracle"]) for c in subset]
        repeated = [verify(domain, c["candidate"], c["oracle"]) for c in subset]
        controls.append(
            {
                "domain": domain,
                "first_sha256": digest(first),
                "repeat_sha256": digest(repeated),
                "false_alarm": first != repeated,
            }
        )
    write_json(out / "clean_controls.json", controls)
    summary["controlled_release_regressions"] = {
        "detected": rate(sum(m["detected"] for m in mutations), len(mutations)),
        "clean_control_false_alarms": rate(
            sum(c["false_alarm"] for c in controls), len(controls)
        ),
        "scope": "Predeclared required-check configuration regressions executed on the full regression corpus, separate from the held-out artifact verdict test.",
    }
    summary["scope"] = (
        "200 held-out constructed artifact/state items; reference calculations use sklearn, candidate verifier uses independent arithmetic. No human/open-ended semantic validation."
    )
    write_json(out / "summary.json", summary)
    return summary
