"""Recompute every published aggregate without an endpoint or benchmark download."""

import json
from pathlib import Path

from score_coverage import summarize


def main():
    root = Path(__file__).resolve().parents[1] / "results" / "coverage_v3"
    for corpus in ("webarena", "workarena"):
        folder = root / corpus
        rows = [
            json.loads(line)
            for line in (folder / "trajectories.jsonl").read_text().splitlines()
        ]
        variants = json.loads((folder / "variants.json").read_text())
        assert summarize(rows, variants) == json.loads(
            (folder / "summary.json").read_text()
        ), corpus
        assert len({(r["task"], r["agent"]) for r in rows}) == len(rows)
        for r in rows:
            for arm in ["baseline", "review_all", "selective", *variants]:
                if arm not in r:
                    continue
                assert (
                    type(r[arm]) is bool and r[arm + "_tokens"] >= r["baseline_tokens"]
                )
                assert not r["baseline"] or r[arm]
        print(corpus, len(rows), "rows: all aggregates match")


if __name__ == "__main__":
    main()
