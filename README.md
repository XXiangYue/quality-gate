# Quality Gate

Quality Gate evaluates whether an agent completed its task. It adds outcome requirements, time-indexed evidence and a challenge of proposed acceptances to an original WebJudge baseline. The original artifact verifier remains available for local business state and regression fixtures.

## Current method experiment

Four development iterations are documented in [outcome evidence review](docs/COVERAGE_REVIEW.md). On 80 unseen WorkArena trajectories, the development-selected reviewer changes correct success recognition from 10/31 to 12/31, with no false acceptance among 49 failures; logical tokens increase 44.4%. Both recoveries are actors on one task. On 310 previously inspected WebArena regression traces, it recovers one success without adding false acceptances. The simpler same-evidence reread performs better on transfer, so superiority of the more complex method is not established. Full component ablations, source manifests, certificates and failed iterations are retained.

```bash
uv run python scripts/check_coverage_results.py
```

## Public browser trajectories

The [WebJudge reproduction guide](docs/WEBJUDGE.md) describes the three paired arms, evidence requirements, datasets, setup and offline scoring. The [held-out results](docs/WEBJUDGE_RESULTS.md) give the number of rescued successes, newly released failures, reviewer calls and disagreements.

## Earlier controlled artifact results

On 100 constructed invalid and 100 valid test artifacts/states, false accepts fell from 100 to 0 versus format-only checking; all valid cases passed. All 20 predefined missing-check configurations were detected.

**Scope and negative findings:** The corpus is constructed, not a collection of production incidents or a universal semantic judge. The separate real-Agent feedback contrast did not establish improvement. Static fixture timings are not end-to-end execution latency.

Measurements were made on **2026-11-01** in the original integrated workspace.
The standalone packaging was prepared on **2026-11-05**. Packaging checks are
reported separately in `VALIDATION.json`; they are not new model benchmark runs.

## Quick start

Use **Python 3.12**, `uv`, and macOS or Linux. Run commands from this checkout.


```bash
git clone https://github.com/XXiangYue/quality-gate.git
cd quality-gate
uv sync --locked
uv run pytest -q
uv run python scripts/verify_results.py
```

The following controlled artifact checks run locally without API credentials. Public browser replay requires a vision-capable model endpoint.


```bash
uv run quality-gate evaluate --out runtime/new-quality-run
uv run quality-gate verify --domain artifact --candidate examples/candidate.json --oracle examples/oracle.json
```

See [running and reproduction](docs/RUNNING.md), [results and limits](docs/RESULTS.md),
[architecture](docs/ARCHITECTURE.md), and [source attribution](THIRD_PARTY.md).
For a Chinese overview, see [中文说明](README.zh-CN.md).

## What is in the repository

- `src/quality_gate/`: independently installable project code and project-specific CLI.
- `tests/`: offline domain and retained regression checks.
- `results/`: measured per-trial exports, protocols, summaries and source hashes.
- `scripts/verify_results.py`: recomputes the primary published counts without inference.
- `protocols/P3.json`: original design protocol; original runs lock later amendments.
- `PROVENANCE.json`: source commit, original/published file hashes and packaging changes.

This is personal portfolio engineering. Historical employer results and private
workplace material are not included. Original code has no newly assigned blanket
license in this packaging operation; vendored components retain their licenses.
