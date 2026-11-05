# Measured results and interpretation

On 100 constructed invalid and 100 valid test artifacts/states, false accepts fell from 100 to 0 versus format-only checking; all valid cases passed. All 20 predefined missing-check configurations were detected.

The corpus is constructed, not a collection of production incidents or a universal semantic judge. The separate real-Agent feedback contrast did not establish improvement. Static fixture timings are not end-to-end execution latency.

## Evidence and reproduction

The original commit is `f6818662fdf4d845732545c34b63776a3960b694`. The measurement date is 2026-11-01.
`results/SOURCE_MANIFEST.json` lists original file hashes. `results/` contains
per-trial numeric/state exports, not all original databases or model transcripts.
Private workstation paths were normalized. Benchmark source text, downloaded
models, credentials and API request identifiers are excluded. Constructed Quality
Gate corpus data is published because it was authored for this experiment.

Run `uv run python scripts/verify_results.py` to recompute primary numbers.
The script verifies observed numerators, denominators and token totals against
the published summaries. It does not independently validate model judgments.
Fresh-run instructions are in [RUNNING.md](RUNNING.md).

## Additional findings to preserve




The test split contains 100 invalid and 100 valid cases, separate from 100 development cases. Controlled missing-check variants are deliberately generated release defects, not independently discovered incidents. A separate real-Agent 12-task feedback control in Expedition yielded 12/12 without feedback versus 11/12 with feedback; it does not establish feedback improvement. That integration experiment is described here but is not required to run this standalone verifier.
