# Outcome evidence review

Quality Gate now tests whether a rejected web task can be recovered by checking the user's actual outcome requirements against time-indexed browser evidence. Four development iterations replaced the first round's confirmation-word screen with an evidence pack, per-condition checks, source-bound requirements and a challenge of proposed acceptances.

The improvement is modest. The development-selected policy recovers one of 31 missed successes on the previously inspected WebArena regression set and two of 21 on a new WorkArena transfer set, with no additional false acceptances observed. It increases total logical tokens by 46.5% and 44.4%, respectively. A simpler same-evidence reread recovers more successes and is better on the small transfer sample. The experiment does not establish superiority of the more elaborate policy.

## Data and boundaries

- AgentRewardBench metadata remains pinned to `05899fcfe52c925978944a23920373b7a9c63740`; observations remain pinned to HF `b6d17e646009d6cb63d5dd7be78807b680693f61`.
- Development: 88 WebArena trajectories, 22 tasks. First human annotations give 27 successes, 60 failures and one `Unsure`; the latter is retained in coverage/cost, excluded from binary accuracy.
- Regression: all 310 previously inspected WebArena test trajectories, 78 tasks, 119 successes and 191 failures. Their results cannot establish fresh held-out generalization.
- Transfer: 20 previously uninspected WorkArena official test tasks, 80 trajectories from four actors. Before viewing traces or outcomes we selected eight L1 and twelve L2 tasks by SHA256 order, as recorded in `protocols/workarena-v3-tasks.json`. The frozen method was applied once. Human labels were joined only for scoring. There are 31 successes, 49 failures and no annotation disagreements in this sample.
- All 80 new trajectories and 1,874 screenshots were acquired. Original source SHA256 and lossless reconstructed RGB hashes were checked. No benchmark Agent was rerun; these are real model judge calls on publicly recorded Agent executions, not new live-browser task attempts.
- The same DeepSeek Flash service alias, temperature 0, disabled thinking and 1,300 output-token cap are used. WebArena uses the retained November 5 WebJudge initial judgments; transfer initial judgments were run on November 6. This is a service-alias comparison, not an immutable model-weight guarantee, and is not a comparison to WebJudge's leaderboard model.

## What changed

1. **Observational evidence.** All new variants receive the same chronological accessibility text, URLs, action-after-observation positions, communicated answers and at most four images (three highest-scored frames plus the final frame). Agent reasoning and the original rejection explanation are omitted. Duplicate page text is referenced backwards. Query-related windows are used for large archives, with explicit omission markers.
2. **Outcome contract.** Requirements are extracted from the user task before execution is shown. Each condition in the final method points to a literal user span. An explicit draft request cannot be promoted to sending; one bounded repair is allowed for a malformed scope contract.
3. **Coverage certificate.** Every condition has a met/missing/contradicted state and page, answer or image references. Code checks condition coverage, frame availability and literal textual quote provenance. An agent's answer alone cannot certify a mutation.
4. **Candidate challenge.** Only a proposed acceptance is independently challenged in another call, using the same evidence and contract. It checks inconsistent states/reasons, incomplete values and citations. The challenge may correct a citation or reject a candidate. It uses the same model, so errors remain correlated.

The deterministic validators check provenance and certificate structure, not semantic truth. Image descriptions and the sufficiency of evidence still depend on the model. The 100,000 setting is a soft AX-text character target, not a hard token or full-input limit. Repeated pages count toward its pruning trigger; 18 development traces were pruned despite fitting after deduplication. The largest development serialized pack was 120,451 characters. This limitation was frozen and shared across new variants.

## Development iterations

| Policy | Correct successes | Accepted failures | Rescued / new false accepts | Total logical tokens |
|---|---:|---:|---:|---:|
| baseline | 16/27 | 6/60 | 0 / 0 | 2,517,353 |
| review_all | 17/27 | 6/60 | 1 / 0 | 2,625,883 |
| evidence | 20/27 | 8/60 | 4 / 2 | 3,589,379 |
| coverage | 17/27 | 6/60 | 1 / 0 | 3,630,861 |
| scoped | 16/27 | 7/60 | 0 / 1 | 3,645,797 |
| unaudited | 17/27 | 7/60 | 1 / 1 | 3,654,622 |
| audited | 18/27 | 6/60 | 2 / 0 | 3,701,990 |

`evidence` is the unanchored same-evidence reread. It recovered four but released two new failures. `coverage` stopped those false releases but only recovered one. `scoped` added user-span requirements, exposing a negation-check bug and a model certificate that marked a one-star rating as satisfying four stars. The fourth bounded repair fixed the negative-language check and added candidate challenge; it recovered two with no new false releases. This extra repair round extends the original two-to-three-round development intention and is recorded before regression/transfer scoring.

`unaudited` is the **exact same candidate** before its final challenge, with that call removed from cost. It is a proper component ablation. `scoped` also differs in the negation bug and cannot serve as this ablation. On development, the candidate challenge repaired one valid rejection and blocked one invalid acceptance, at 47,368 additional tokens. The selected `audited` policy was frozen on these development results; we did not switch policies after seeing later outcomes.

## Previously inspected WebArena regression

| Policy | Correct successes | Accepted failures | Rescued / new false accepts | Total logical tokens |
|---|---:|---:|---:|---:|
| baseline | 88/119 | 11/191 | 0 / 0 | 7,851,272 |
| selective | 88/119 | 12/191 | 0 / 1 | 8,113,433 |
| review_all | 90/119 | 12/191 | 2 / 1 | 8,207,735 |
| evidence | 96/119 | 16/191 | 8 / 5 | 11,181,282 |
| unaudited | 91/119 | 11/191 | 3 / 0 | 11,391,783 |
| audited | 89/119 | 11/191 | 1 / 0 | 11,504,204 |

The final policy improves recall from 73.95% to 74.79%, with false acceptances unchanged at 11/191. Its task-cluster bootstrap interval for recall change is [0.00, 2.80] percentage points. Removing the last challenge recovers three with the same observed false acceptance count, so the challenge over-rejects here. The simpler evidence arm recovers eight but releases five new failures (four when disputed labels are excluded). This is a sensitivity/caution result, not a selected replacement.

## Unseen WorkArena transfer

| Policy | Correct successes | Accepted failures | Rescued / new false accepts | Total logical tokens |
|---|---:|---:|---:|---:|
| baseline | 10/31 | 0/49 | 0 / 0 | 3,582,377 |
| review_all | 11/31 | 0/49 | 1 / 0 | 3,722,622 |
| evidence | 13/31 | 0/49 | 3 / 0 | 5,125,742 |
| unaudited | 12/31 | 0/49 | 2 / 0 | 5,138,583 |
| audited | 12/31 | 0/49 | 2 / 0 | 5,171,991 |

Recall changes from 32.26% to 38.71%; no failures among the 49 negative trajectories are accepted by either policy. The two recoveries are different actors on **one base task**, not two independent task families: after impersonating a specified user, the subsequent header and account button actually show that user. WebJudge's original rejection said the final transition had not been observed. The new evidence pack exposes the final identity state. The task-cluster interval for recall change is [0.00, 20.69] percentage points. Twenty tasks and zero observed added false acceptances do not demonstrate a zero population error rate.

The same-evidence reread recovers three successes at lower cost; the final challenge adds no transfer gains. These results support the usefulness of improved evidence access in a narrow case, but do not isolate a positive contribution from complex contracts or auditing on unseen tasks. No broad reliability, significance or optimality claim is justified.

## Cost and reproducibility

Per-arm logical tokens include its initial WebJudge calls and completed review/contract/challenge path. Shared cached payloads are counted as if that arm were replayed alone. This is not physical billing and cannot alone account for a response followed by a local parsing failure. `accounting.json` separately records all newly metered physical requests, known peak-equivalent estimates and unknown billing. The three initial local SQLite initialization errors are retained; all affected traces later completed. There are no unresolved inference failures. The old WebArena baseline's physical cost is not charged again in the new ledger.

Published JSONL rows reproduce every table with `python scripts/check_coverage_results.py`. Structured certificates expose conditions, evidence references, candidates and final challenges. All 471 completed structured certificates were revalidated after the release-only malformed-input hardening; every decision remained identical. Original frozen inference source, development log, freeze record and source manifests remain in `results/coverage_v3/`. Twelve offline tests cover provenance, missing/duplicate conditions, malformed outputs, action/answer separation, scope negation and old contracts. These tests do not establish model correctness.

## Running

Use the [original WebJudge guide](WEBJUDGE.md) to prepare WebArena and its baseline. Supply your endpoint key through the environment; never add it to a file tracked by Git.

```bash
uv sync --locked
uv run python scripts/check_coverage_results.py
uv run --with 'Pillow==13.0.0' python scripts/coverage_judge.py runtime/webarena/observations runtime/webarena/verdicts runtime/coverage --variant audited --split dev
# Freeze your chosen configuration before test/transfer evaluation.
uv run --with 'Pillow==13.0.0' python scripts/coverage_judge.py runtime/webarena/observations runtime/webarena/verdicts runtime/coverage --variant audited --split test
uv run --with 'Pillow==13.0.0' python scripts/coverage_judge.py runtime/webarena/observations runtime/webarena/verdicts runtime/coverage --variant evidence --split test
uv run python scripts/score_coverage.py runtime/webarena/observations/catalog.json runtime/webarena/verdicts runtime/coverage runtime/coverage-scored --variants evidence unaudited audited
```

To reproduce the fixed transfer sample (original JSON downloads total about 2.2 GB before pruning):

```bash
uv run python scripts/prepare_coverage_data.py protocols/workarena-v3-tasks.json runtime/workarena/observations
uv run --with 'Pillow==13.0.0' python scripts/webarena_judge.py runtime/workarena/observations runtime/workarena/baseline runtime/webarena/webjudge.py --split test
uv run --with 'Pillow==13.0.0' python scripts/coverage_judge.py runtime/workarena/observations runtime/workarena/baseline runtime/workarena/reviews --variant audited --split test
uv run --with 'Pillow==13.0.0' python scripts/coverage_judge.py runtime/workarena/observations runtime/workarena/baseline runtime/workarena/reviews --variant evidence --split test
uv run python scripts/score_coverage.py runtime/workarena/observations/catalog.json runtime/workarena/baseline runtime/workarena/reviews runtime/workarena/scored --variants evidence unaudited audited
```

The current implementation is an experimental offline reviewer. Initial acceptances are never revisited, so their false positives remain. API errors produce coverage gaps and preserved failure records; a resumed run uses content-addressed successful calls. Do not claim that all successful or failed tasks are reliably adjudicated.

## Sources

- [AgentRewardBench and pinned annotations/splits](https://github.com/McGill-NLP/agent-reward-bench/tree/05899fcfe52c925978944a23920373b7a9c63740/agent_reward_bench/data)
- [Pinned public observation archive](https://huggingface.co/datasets/McGill-NLP/agent-reward-bench/tree/b6d17e646009d6cb63d5dd7be78807b680693f61)
- [Pinned original WebJudge implementation](https://github.com/OSU-NLP-Group/Online-Mind2Web/blob/1a8db93168d5d7870402b7f453160e1c557153c8/src/methods/webjudge_general_eval.py)
