"""Fetch public observations separately from human labels and scoring metadata."""

import argparse
import concurrent.futures
import csv
import gzip
import hashlib
import io
import json
import subprocess
import urllib.parse
from pathlib import Path

HF = "https://huggingface.co/datasets/McGill-NLP/agent-reward-bench/resolve/b6d17e646009d6cb63d5dd7be78807b680693f61/"
METADATA = "https://raw.githubusercontent.com/McGill-NLP/agent-reward-bench/05899fcfe52c925978944a23920373b7a9c63740/agent_reward_bench/data/"


def fetch(url):
    # Curl handles content compression, redirects and HTTP/2 for large HF blobs.
    # Set HTTPS_PROXY explicitly on hosts that expose a system-only proxy.
    return subprocess.run(
        [
            "curl",
            "--fail",
            "--location",
            "--silent",
            "--show-error",
            "--compressed",
            "--connect-timeout",
            "12",
            "--max-time",
            "150",
            "--retry",
            "3",
            "--retry-all-errors",
            url,
        ],
        capture_output=True,
        check=True,
    ).stdout


def catalog_rows():
    split = {
        r["task_id"]: r["split"]
        for r in csv.DictReader(io.StringIO(fetch(METADATA + "splits.csv").decode()))
        if r["benchmark"] == "webarena"
    }
    catalog = {}
    for r in csv.DictReader(io.StringIO(fetch(METADATA + "annotations.csv").decode())):
        if r["benchmark"] == "webarena" and r["task_id"] in split:
            key = (r["task_id"], r["model_name"])
            row = catalog.setdefault(
                key,
                {
                    "task": key[0],
                    "agent": key[1],
                    "experiment": r["exp_name"],
                    "split": split[key[0]],
                    "labels": [],
                },
            )
            row["labels"].append([r["annotator_name"], r["trajectory_success"]])
    return list(catalog.values())


def run(folder, workers, *, shard=0, shards=1, frames=False):
    folder.mkdir(parents=True, exist_ok=True)
    catalog = catalog_rows()
    (folder / "catalog.json").write_text(json.dumps(catalog, indent=2))
    rows = catalog[shard::shards]
    frame_dir = folder / "frames"
    if frames:
        frame_dir.mkdir(exist_ok=True)

    def ensure_frames(path):
        if not frames:
            return
        for step in json.loads(gzip.decompress(path.read_bytes()))["steps"]:
            remote = step["screenshot_path"].removeprefix("trajectories/")
            if not remote.startswith("screenshots/webarena/"):
                raise ValueError("Unexpected screenshot path")
            dest = frame_dir / (hashlib.sha256(remote.encode()).hexdigest() + ".png")
            if not dest.exists():
                raw = fetch(HF + remote)
                if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
                    raise ValueError("Fetched resource is not PNG")
                dest.write_bytes(raw)

    def one(row):
        key = row["task"] + "__" + row["agent"]
        path = folder / (key + ".json.gz")
        try:
            if path.exists():
                ensure_frames(path)
                return True
            resource = f"cleaned/webarena/{row['agent']}/{row['experiment']}/{row['task']}.json"
            raw = fetch(HF + urllib.parse.quote(resource))
            src = json.loads(raw)
            steps = [
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
                for s in src["steps"]
            ]
            tmp = path.with_suffix(".part")
            tmp.write_bytes(
                gzip.compress(
                    json.dumps(
                        {
                            "goal": src["goal"],
                            "steps": steps,
                            "source_sha256": hashlib.sha256(raw).hexdigest(),
                        }
                    ).encode()
                )
            )
            tmp.replace(path)
            ensure_frames(path)
            return True
        except Exception as ex:  # noqa: BLE001 - keep the other scheduled trajectories running
            print(key, type(ex).__name__, flush=True)
            return False

    with concurrent.futures.ThreadPoolExecutor(workers) as pool:
        available = sum(pool.map(one, rows))
        print("Available trajectories:", available, "/", len(rows), flush=True)
        return available == len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--with-frames", action="store_true")
    args = parser.parse_args()
    if not 0 <= args.shard < args.shards:
        parser.error("Shard index is outside the partition.")
    ok = run(
        args.folder,
        args.workers,
        shard=args.shard,
        shards=args.shards,
        frames=args.with_frames,
    )
    raise SystemExit(0 if ok else 1)
