"""Fetch a predeclared task list without selecting on human outcomes."""

import argparse
import csv
import gzip
import hashlib
import io
import json
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from webarena_data import HF, METADATA, fetch


def main():
    p = argparse.ArgumentParser()
    p.add_argument("tasks", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("--workers", type=int, default=4)
    args = p.parse_args()
    selected = set(json.loads(args.tasks.read_text())["tasks"])
    records = csv.DictReader(io.StringIO(fetch(METADATA + "annotations.csv").decode()))
    catalog = {}
    for r in records:
        if r["task_id"] not in selected:
            continue
        key = (r["task_id"], r["model_name"])
        row = catalog.setdefault(
            key,
            {
                "task": key[0],
                "agent": key[1],
                "experiment": r["exp_name"],
                "split": "test",
                "labels": [],
            },
        )
        row["labels"].append([r["annotator_name"], r["trajectory_success"]])
    if {k[0] for k in catalog} != selected:
        raise ValueError("Declared task missing from pinned annotations")
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "frames").mkdir(exist_ok=True)
    (args.out / "catalog.json").write_text(json.dumps(list(catalog.values()), indent=2))

    def one(row):
        domain = row["task"].split(".", 1)[0]
        if domain not in {"workarena", "webarena"}:
            raise ValueError("Unsupported domain")
        key = row["task"] + "__" + row["agent"]
        dest = args.out / (key + ".json.gz")
        if not dest.exists():
            url = HF + urllib.parse.quote(
                f"cleaned/{domain}/{row['agent']}/{row['experiment']}/{row['task']}.json"
            )
            raw = fetch(url)
            original = json.loads(raw)
            trace = {
                "goal": original["goal"],
                "steps": [
                    {
                        k: s.get(k)
                        for k in (
                            "num",
                            "action",
                            "reasoning",
                            "url",
                            "last_action_error",
                            "screenshot_path",
                        )
                    }
                    | {"axtree": s.get("axtree_pruned") or s.get("axtree") or ""}
                    for s in original["steps"]
                ],
                "source_sha256": hashlib.sha256(raw).hexdigest(),
            }
            part = dest.with_suffix(".part")
            part.write_bytes(gzip.compress(json.dumps(trace).encode()))
            part.replace(dest)
        trace = json.loads(gzip.decompress(dest.read_bytes()))
        for step in trace["steps"]:
            remote = step["screenshot_path"].removeprefix("trajectories/")
            if not remote.startswith(f"screenshots/{domain}/"):
                raise ValueError("Invalid frame path")
            image = (
                args.out
                / "frames"
                / (hashlib.sha256(remote.encode()).hexdigest() + ".png")
            )
            if not image.exists():
                raw = fetch(HF + urllib.parse.quote(remote))
                if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("Invalid PNG")
                part = image.with_suffix(".part")
                part.write_bytes(raw)
                part.replace(image)
        return True

    with ThreadPoolExecutor(args.workers) as pool:
        count = sum(pool.map(one, catalog.values()))
    print("Prepared", count, "trajectories")


if __name__ == "__main__":
    main()
