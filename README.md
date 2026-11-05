# Quality Gate

Independent acceptance checks for Agent artifacts and business final state, with controlled release-regression witnesses.

## Measured outcome

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

All evaluation and verification paths in this repository run locally without API credentials.


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
