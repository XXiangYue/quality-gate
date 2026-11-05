# Running Quality Gate

## Environment

Use Python 3.12 and the checked-in `uv.lock`. `uv sync --locked` installs an
editable checkout in its own virtual environment. Run from the repository root;
the source intentionally locates project assets relative to that checkout.
Linux/macOS are supported; Windows users can use WSL2. CPU runs do not require CUDA.

## Three different verification levels

1. `uv run pytest -q`: offline contracts and regression witnesses; provider fixtures
   are explicitly simulated and are not model-effectiveness evidence.
2. `uv run python scripts/verify_results.py`: recomputation from published rows
   of historical measurements; no inference or new performance claim.
3. The project commands below: fresh execution under your own environment. Use
   a new output directory. Changed models, prompts, dependencies or assets define
   a new run and need their own result label.

```bash
uv run quality-gate evaluate --out runtime/new-quality-run
uv run quality-gate verify --domain artifact --candidate examples/candidate.json --oracle examples/oracle.json
```

All evaluation and verification paths in this repository run locally without API credentials.


## Results and troubleshooting

`results/` is a read-only historical export. New runs go under `runtime/` or a new
chosen directory. The code refuses a conflicting frozen protocol. Do not reuse
an old terminal output directory for a changed configuration.





The corpus command regenerates constructed labeled examples and compares format-only V0 with independent V1. Inspect corpus.json, verdicts.json and release_mutations.json in the new output directory. Static evaluation timings are not deployment latency.


If inference credentials are absent, an explicit configuration error is expected.
No embedded fallback response is substituted for real inference.
