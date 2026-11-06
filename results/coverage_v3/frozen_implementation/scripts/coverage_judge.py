"""Run outcome-coverage review against cached pinned WebJudge results."""

import argparse
import gzip
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image
from webarena_judge import Model, encoded

from quality_gate.common import Budget, write_json
from quality_gate.coverage_review import (
    AUDIT_PROMPT,
    CONTRACT_PROMPT,
    COVERAGE_PROMPT,
    EVIDENCE_RULES,
    SCOPED_CONTRACT_PROMPT,
    SCOPED_REVIEW_RULES,
    observation_pack,
    parse_json,
    scoped_contract_errors,
    selected_frames,
    validate_contract,
    validate_coverage,
)


def evaluate(row, args):
    key = row["task"] + "__" + row["agent"]
    dest = args.out / args.variant / (key + ".json")
    if dest.exists():
        return
    base = json.loads((args.baseline / (key + ".json")).read_text())
    trace = json.loads(gzip.decompress((args.data / (key + ".json.gz")).read_bytes()))
    model = Model(args.out / "calls")
    report = {
        "task": row["task"],
        "agent": row["agent"],
        "split": row["split"],
        "baseline": base["baseline"],
        "accepted": base["baseline"],
        "variant": args.variant,
        "source_sha256": trace["source_sha256"],
        "new_calls": [],
    }
    if not base["baseline"]:
        pages = observation_pack(trace["steps"], trace["goal"])
        ids = selected_frames(base["frame_scores"], len(trace["steps"]))
        contract = None
        if args.variant != "evidence":
            contract_prompt = (
                SCOPED_CONTRACT_PROMPT
                if args.variant in {"scoped", "audited"}
                else CONTRACT_PROMPT
            )
            contract = parse_json(
                model.generate(
                    [{"role": "user", "content": contract_prompt + trace["goal"]}]
                )[0]
            )
            if args.variant in {"scoped", "audited"}:
                errors = scoped_contract_errors(
                    contract,
                    trace["goal"],
                    ignore_negated_transmission=args.variant == "audited",
                )
                if errors:
                    report["contract_repair"] = {"original": contract, "errors": errors}
                    contract = parse_json(
                        model.generate(
                            [
                                {
                                    "role": "user",
                                    "content": contract_prompt + trace["goal"],
                                },
                                {"role": "assistant", "content": json.dumps(contract)},
                                {
                                    "role": "user",
                                    "content": "Repair these contract scope violations and return the same JSON schema: "
                                    + json.dumps(errors),
                                },
                            ]
                        )[0]
                    )
                    if scoped_contract_errors(
                        contract,
                        trace["goal"],
                        ignore_negated_transmission=args.variant == "audited",
                    ):
                        report.update(
                            accepted=False,
                            contract=contract,
                            validation_errors=["unrepairable_contract"],
                            new_calls=model.usage,
                        )
                        write_json(dest, report)
                        return
            if not validate_contract(contract):
                raise ValueError("Invalid contract")
        prompt = EVIDENCE_RULES
        if args.variant in {"scoped", "audited"}:
            prompt += SCOPED_REVIEW_RULES
        if contract:
            prompt += COVERAGE_PROMPT
        else:
            prompt += 'Return JSON {"verdict":"success|failure","reason":"reason tied to actual evidence"}.\n'
        payload = {"task": trace["goal"], "observations": pages}
        if contract:
            payload["contract"] = contract
        content = [
            {"type": "text", "text": prompt + json.dumps(payload, ensure_ascii=False)}
        ]
        for i in ids:
            remote = trace["steps"][i]["screenshot_path"].removeprefix("trajectories/")
            path = (
                args.data
                / "frames"
                / (hashlib.sha256(remote.encode()).hexdigest() + ".png")
            )
            with Image.open(path) as img:
                content += [
                    {"type": "text", "text": f"Observed image at step {i}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "data:image/jpeg;base64," + encoded(img)},
                    },
                ]
        raw = model.generate([{"role": "user", "content": content}])[0]
        reply = parse_json(raw)
        if contract:
            accepted, errors = validate_coverage(reply, contract, pages, set(ids))
        else:
            accepted, errors = reply.get("verdict") == "success", []
        if args.variant == "audited" and reply.get("verdict") == "success":
            report["candidate"] = {
                "reply": reply,
                "accepted_without_audit": accepted,
                "validation_errors": errors,
            }
            audit_content = [
                {
                    "type": "text",
                    "text": EVIDENCE_RULES
                    + SCOPED_REVIEW_RULES
                    + AUDIT_PROMPT
                    + COVERAGE_PROMPT
                    + json.dumps(payload, ensure_ascii=False)
                    + "\nPROPOSED CERTIFICATE:\n"
                    + json.dumps(reply, ensure_ascii=False),
                }
            ] + content[1:]
            reply = parse_json(
                model.generate([{"role": "user", "content": audit_content}])[0]
            )
            accepted, errors = validate_coverage(reply, contract, pages, set(ids))
        report.update(
            accepted=accepted,
            contract=contract,
            reply=reply,
            validation_errors=errors,
            frames=ids,
            evidence_pack_sha256=hashlib.sha256(json.dumps(pages).encode()).hexdigest(),
            new_calls=model.usage,
        )
    write_json(dest, report)


def main():
    p = argparse.ArgumentParser()
    for name in ("data", "baseline", "out"):
        p.add_argument(name, type=Path)
    p.add_argument(
        "--variant",
        choices=["evidence", "coverage", "scoped", "audited"],
        required=True,
    )
    p.add_argument("--split", choices=["dev", "test"], required=True)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    (args.out / "calls").mkdir(parents=True, exist_ok=True)
    Budget(args.out / "billing.sqlite", 30)
    rows = [
        r
        for r in json.loads((args.data / "catalog.json").read_text())
        if r["split"] == args.split
    ]

    def one(r):
        try:
            evaluate(r, args)
            return True
        except Exception as e:  # noqa: BLE001 - retain per-trajectory failures
            issue = {"task": r["task"], "agent": r["agent"], "error": type(e).__name__}
            write_json(
                args.out
                / "errors"
                / args.variant
                / (r["task"] + "__" + r["agent"] + ".json"),
                issue,
            )
            print(issue, flush=True)
            return False

    with ThreadPoolExecutor(args.workers) as pool:
        count = sum(pool.map(one, rows))
    print(args.variant, args.split, count, "/", len(rows), flush=True)
    raise SystemExit(0 if count == len(rows) else 1)


if __name__ == "__main__":
    main()
