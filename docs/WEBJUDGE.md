# WebArena completion review

Quality Gate replays the upstream WebJudge general evaluator on saved browser observations and offers a second assessment of rejected trajectories. A successful reversal must cite a supplied frame and affirm every requested condition. The model interprets whether the cited screenshot supports the claim. The code checks the citation index and the verdict format.

## Reproduce

Use Python 3.12, curl, an image-capable DeepSeek endpoint, and the pinned source files. Keep downloaded observations and model outputs under the ignored runtime directory. Human labels are used by the scoring stage. The judge reads the task description, agent actions and reasoning, accessibility text, URLs and browser frames.

```bash
uv sync --locked
mkdir -p runtime/webarena
curl -fL 'https://raw.githubusercontent.com/OSU-NLP-Group/Online-Mind2Web/1a8db93168d5d7870402b7f453160e1c557153c8/src/methods/webjudge_general_eval.py' -o runtime/webarena/webjudge.py
uv run python scripts/webarena_data.py runtime/webarena/observations --workers 8
export OUTCOMES_API_BASE=https://api.deepseek.com/v1
# Supply OUTCOMES_API_KEY in the local environment.
uv run --with 'Pillow==13.0.0' python scripts/webarena_judge.py runtime/webarena/observations runtime/webarena/verdicts runtime/webarena/webjudge.py --split dev
uv run --with 'Pillow==13.0.0' python scripts/webarena_judge.py runtime/webarena/observations runtime/webarena/verdicts runtime/webarena/webjudge.py --split test
uv run python scripts/score_webarena.py runtime/webarena/rows.jsonl runtime/webarena/summary.json --catalog runtime/webarena/observations/catalog.json --runs runtime/webarena/verdicts
```

The optional manual Actions workflow prepares twelve encrypted, one-day observation shards when a local machine has intermittent access to the public archive. It only downloads pinned public data. It receives the recipient's public X.509 certificate in base64. Decrypt each artifact locally with `openssl cms -decrypt -inform DER -in shard.cms -recip recipient.pem -inkey recipient.key -out shard.tar.gz`, then unpack each shard into a separate directory. Copy its trajectory JSON files and catalog to the common observations directory. Use `uv run --with Pillow python scripts/frame_bundle.py unpack runtime/webarena/observations/frames path/to/pixels.zip` for each image archive. Each reconstructed RGB frame is checked against its original pixel hash. The model calls run on the machine holding the API credential.

## Comparison

The upstream module is checked against its SHA-256 before import. Its original prompts identify requirements, score screenshots and assess the action history with the selected frames. We use threshold 3, temperature 0, thinking disabled, and a cap of 1,300 output tokens per call. We share identical cached payloads across comparisons and resumptions.

All three arms use the same initial judgment. An initial acceptance ends the trajectory. For a rejection, the selective arm can nominate up to three frames where subsequent observations contain confirmation language or the URL changed following a page with mutation controls. Generic controls can trigger an unnecessary reread. Both review arms receive the final frame and every nominated frame. The all-rejections arm also gets the final frame when the trigger is empty. This isolates the choice of which trajectories to reread. The second reader may keep the rejection.

Per-arm counts of calls and tokens represent replaying that arm alone. On a shared physical run, identical requests may have been served from the local cache. Billing failures and completed records have separate accounting. A conservative cost estimate prices input as a cache miss at peak rates. The estimate differs from a provider invoice. Raw model responses and screenshots are kept outside version control.

## Scoring

The primary human label is the first annotation in the pinned metadata file. Each trajectory contributes once. We report scores for unanimous annotations as a sensitivity check. Primary human unsure labels and incomplete model verdicts are separated from binary denominators. Report coverage of all 88 development and 310 held-out trajectories. Recall divides accepted human successes by human successes. False acceptance divides accepted human failures by human failures. We count individually the prior false rejections recovered and the new false accepts. Task-cluster bootstrap intervals resample complete task groups with replacement and are conditional on observed coverage. A zero-width interval when no observed trajectory flips gives no population-level safety guarantee.

Upstream sources include [AgentRewardBench and metadata](https://github.com/McGill-NLP/agent-reward-bench/tree/05899fcfe52c925978944a23920373b7a9c63740/agent_reward_bench/data), the [public trajectories](https://huggingface.co/datasets/McGill-NLP/agent-reward-bench/tree/b6d17e646009d6cb63d5dd7be78807b680693f61), the [WebJudge source](https://github.com/OSU-NLP-Group/Online-Mind2Web/blob/1a8db93168d5d7870402b7f453160e1c557153c8/src/methods/webjudge_general_eval.py), and the [provider pricing table](https://api-docs.deepseek.com/quick_start/pricing/).
