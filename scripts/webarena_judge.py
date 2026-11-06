"""Execute the pinned upstream WebJudge and two paired review policies."""

import argparse
import asyncio
import base64
import gzip
import hashlib
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import threading
import types
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib import request

from PIL import Image
from webarena_data import HF, fetch

from quality_gate.common import Budget, write_json
from quality_gate.web_review import accepted_review, review_evidence

PIN = "9035e921766de7afa424a61377917138eb3e728f6686aaa64f7a31107dd66ec8"
MODEL = "deepseek-flash"
LIMIT = threading.BoundedSemaphore(28)
CACHE_LOCKS = [threading.Lock() for _ in range(257)]


def peak_cost(usage):
    return usage["prompt_tokens"] * 0.30e-6 + usage["completion_tokens"] * 1.20e-6


def encoded(image):
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, format="JPEG")
    return base64.b64encode(buffer.getvalue()).decode()


def official(path):
    if hashlib.sha256(path.read_bytes()).hexdigest() != PIN:
        raise ValueError("Unexpected upstream WebJudge source")
    utils = types.ModuleType("utils")
    utils.encode_image = encoded
    sys.modules["utils"] = utils
    spec = importlib.util.spec_from_file_location("upstream_webjudge", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Model:
    def __init__(self, cache):
        self.cache = cache
        self.usage = []
        self.mutex = threading.Lock()

    def generate(self, messages):
        body = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0,
            "max_tokens": 1300,
            "thinking": {"type": "disabled"},
        }
        payload = json.dumps(body, ensure_ascii=False).encode()
        name = hashlib.sha256(payload).hexdigest()
        path = self.cache / (name + ".json")
        with CACHE_LOCKS[int(name[:8], 16) % len(CACHE_LOCKS)]:
            if not path.exists():
                endpoint = (
                    os.environ["OUTCOMES_API_BASE"].rstrip("/") + "/chat/completions"
                )
                req = request.Request(
                    endpoint,
                    data=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer " + os.environ["OUTCOMES_API_KEY"],
                    },
                )
                budget = Budget(self.cache.parent / "billing.sqlite", 30)
                maximum = min(1_000_000, len(payload) + 8192) * 0.30e-6 + 1300 * 1.20e-6
                with LIMIT:
                    ticket = budget.reserve(
                        maximum, label="webjudge", request_sha256=name
                    )
                    try:
                        with request.urlopen(req, timeout=100) as stream:
                            result = json.load(stream)
                        usage = result["usage"]
                        budget.settle(ticket, usage, peak_cost(usage))
                    except Exception:
                        budget.settle(ticket, {}, maximum, unknown_billing=True)
                        raise
                text = result["choices"][0]["message"]["content"]
                if not text or not isinstance(usage["prompt_tokens"], int):
                    raise ValueError("Incomplete response")
                with tempfile.NamedTemporaryFile(
                    mode="w", dir=self.cache, delete=False
                ) as f:
                    json.dump({"text": text, "usage": usage}, f)
                Path(f.name).replace(path)
        data = json.loads(path.read_text())
        with self.mutex:
            self.usage.append(
                {k: data["usage"][k] for k in ("prompt_tokens", "completion_tokens")}
                | {"call": name}
            )
        return [data["text"]]


def evaluate(row, data, out, module):
    key = row["task"] + "__" + row["agent"]
    destination = out / (key + ".json")
    if destination.exists():
        return
    trajectory = json.loads(gzip.decompress((data / (key + ".json.gz")).read_bytes()))
    steps, goal = trajectory["steps"], trajectory["goal"]
    model = Model(out / "calls")
    with tempfile.TemporaryDirectory(dir=out) as temp:

        def image_file(s):
            remote = s["screenshot_path"].removeprefix("trajectories/")
            dataset = row["task"].split(".", 1)[0]
            if dataset not in {"webarena", "workarena"} or not remote.startswith(
                f"screenshots/{dataset}/"
            ):
                raise ValueError("Invalid public screenshot path")
            img = Path(temp) / (str(s["num"]) + ".png")
            store = data / "frames"
            store.mkdir(exist_ok=True)
            saved = store / (hashlib.sha256(remote.encode()).hexdigest() + ".png")
            if not saved.is_file():
                raw = fetch(HF + remote)
                with Image.open(io.BytesIO(raw)) as check:
                    check.verify()
                with tempfile.NamedTemporaryFile(dir=store, delete=False) as part:
                    part.write(raw)
                Path(part.name).replace(saved)
            os.link(saved, img)
            return img

        with ThreadPoolExecutor(4) as pool:
            frames = list(pool.map(image_file, steps))
        messages, _, _, record, key_points = asyncio.run(
            module.WebJudge_general_eval(
                goal,
                None,
                [s.get("reasoning") or "" for s in steps if s.get("action")],
                [s["action"] for s in steps if s.get("action")],
                frames,
                model,
                3,
            )
        )
        baseline = model.generate(messages)[0]
        matches = re.findall(
            r'(?im)^\s*\**Status\**:\s*["\x27* ]*(success|failure)\b', baseline
        )
        if not matches:
            raise ValueError("Unparseable upstream verdict")
        base = matches[-1].lower() == "success"
        first_calls = list(model.usage)
        trigger = review_evidence(steps) if not base else []
        updated = base
        cites = []
        if not base:
            ids = sorted(set(trigger + [len(frames) - 1]))
            prompt = (
                "Review a rejected web task from observed pages. Only reverse when every requested condition is visible or supported by the action history. An attempted action alone is insufficient. "
                'Output JSON {"verdict":"success" or "failure","all_requirements_met":boolean,"citations":[frame numbers],"reason":string}.\n'
                + json.dumps(
                    {
                        "task": goal,
                        "requirements": key_points,
                        "actions": [s.get("action") for s in steps],
                        "initial_judgment": baseline,
                    },
                    ensure_ascii=False,
                )
            )
            content = [{"type": "text", "text": prompt}]
            for i in ids:
                with Image.open(frames[i]) as img:
                    content.extend(
                        [
                            {"type": "text", "text": f"Observed frame {i}"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": "data:image/jpeg;base64," + encoded(img)
                                },
                            },
                        ]
                    )
            raw = model.generate([{"role": "user", "content": content}])[0]
            judgment = json.loads(re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", raw))
            updated = accepted_review(judgment, set(ids))
            cites = judgment.get("citations", [])
        report = {
            "task": row["task"],
            "agent": row["agent"],
            "split": row["split"],
            "baseline": base,
            "selective": updated if trigger else base,
            "review_all": updated,
            "trigger": trigger,
            "citations": cites,
            "frame_scores": [s["Score"] for s in record],
            "base_calls": first_calls,
            "review_calls": model.usage[len(first_calls) :],
            "source_sha256": trajectory["source_sha256"],
            "model": MODEL,
        }
        tmp = destination.with_suffix(".part")
        tmp.write_text(json.dumps(report))
        tmp.replace(destination)


def main():
    p = argparse.ArgumentParser()
    for arg in ("data", "out", "upstream"):
        p.add_argument(arg, type=Path)
    p.add_argument("--split", choices=("dev", "test"), required=True)
    p.add_argument("--limit", type=int)
    p.add_argument("--workers", type=int, default=6)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "calls").mkdir(exist_ok=True)
    Budget(args.out / "billing.sqlite", 30)
    rows = [
        r
        for r in json.loads((args.data / "catalog.json").read_text())
        if r["split"] == args.split
    ]
    method = official(args.upstream)

    def one(r):
        try:
            evaluate(r, args.data, args.out, method)
            return True
        except Exception as e:  # noqa: BLE001 - record per-trajectory failures
            reason = {
                "task": r["task"],
                "agent": r["agent"],
                "error": type(e).__name__,
                "code": getattr(e, "code", None),
            }
            write_json(
                args.out / "errors" / (r["task"] + "__" + r["agent"] + ".json"), reason
            )
            print(reason, flush=True)
            return False

    with ThreadPoolExecutor(args.workers) as pool:
        selected = rows[: args.limit]
        complete = sum(pool.map(one, selected))
    print(f"Completed {complete}/{len(selected)} paired judgments", flush=True)
    if complete != len(selected):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
