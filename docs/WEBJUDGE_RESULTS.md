# WebJudge results on AgentRewardBench WebArena

On 310 of 310 held-out browser trajectories, selective review reversed 1 initial rejections. Human primary annotations identified 0 recovered successes and 1 newly accepted failures. The policy missed the predefined guard on the count of false accepts. The release check keeps the original judgment and leaves the second-read evidence available for inspection. Success recall changed from 73.9% to 73.9%, with a false-accept rate of 5.8% and 6.3% respectively.

| Policy | Human successes accepted | Human failures accepted | Recovered successes | Newly accepted failures | Rereads | All logical model tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Original WebJudge | 88/119 | 11/191 | 0 | 0 | 0 | 7,851,272 |
| Selective reread | 88/119 | 12/191 | 0 | 1 | 123 | 8,113,433 |
| Reread every rejection | 90/119 | 12/191 | 2 | 1 | 211 | 8,207,735 |

Reviewing every rejection found 2 successful trajectories omitted by the baseline and released 1 additional failures. Selective review used 123 versus 211 second reads. Those requests represent 39.7% of completed test trajectories. The difference in total logical tokens across these two policies was 94,302.

The paired 95% task-bootstrap intervals for selective-minus-baseline differences were [0.0, 0.0] percentage points in recall and [0.0, 1.685] points in false-accept rate (78 task groups). The primary comparison used the first annotation in the pinned metadata. Of the completed held-out rows, 9 had discordant annotations. Restricting to unanimous labels yielded 0 recovered successes and 1 newly accepted failures.

Development coverage was 88/88. The selection rule was fixed after one development smoke run. Remaining development and held-out trajectories were replayed without tuning on their labels. On dev, selective review recovered 1 true successes with 0 newly accepted failures. In webarena.629 (Llama), a later empty submission form had distracted the first judge from an already published discussion post. The second reader cited frame 15. A different failure mode appears in the held-out directions query webarena.757 (Claude). The final frame contained the route and ETA, but the selective trigger did not nominate this read-only interaction. Rereading every rejection recovered it.

The held-out metaseq SSH-clone query (webarena.295, Llama) illustrates an erroneous reversal. The judge accepted the project menu showing an abbreviated SSH address. The initial judge had explicitly checked whether the user received the complete command. The primary human label is unsuccessful. A valid frame citation establishes where the reviewer looked, while semantic sufficiency still depends on what that observation proves.

Replay used the same DeepSeek Flash service alias for all three policies. Accepted baseline records bypass review in all policies. Logical token totals include the original judge calls and the extra calls specific to each policy. Physical requests are shared and cached. The [physical usage record](../results/webarena/accounting.json) gives the available meter totals and billing limits. The early run was restored using 340 available response records, so unobservable early retries cannot be assigned an exact physical charge. The per-arm token totals are conditional on completed verdicts. The public export retains every catalog identity and its status, including any incomplete attempt.

Recompute the report counts from the [public per-trajectory records](../results/webarena/trajectories.jsonl).

```bash
python3 scripts/score_webarena.py results/webarena/trajectories.jsonl /tmp/recomputed.json
diff -u results/webarena/summary.json /tmp/recomputed.json
```

The [running guide](WEBJUDGE.md) contains download, source integrity, image preparation and paired inference instructions.
