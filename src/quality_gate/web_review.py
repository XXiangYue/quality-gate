"""Selective second reads of WebJudge rejections using subsequent browser evidence."""

from __future__ import annotations

import re

CONFIRMATION = re.compile(
    r"\b(?:successfully|confirmation|order (?:number|#)|added to|has been (?:saved|created|updated)|changes saved)\b",
    re.IGNORECASE,
)
MUTATION = re.compile(
    r"\b(?:submit|save|confirm|buy|order|post|send|create|update|delete|cart)\b",
    re.IGNORECASE,
)


def review_evidence(steps: list[dict]) -> list[int]:
    """Only environmental changes following an action can nominate a rejection."""
    nominated = []
    for i in range(1, len(steps)):
        before, after = steps[i - 1], steps[i]
        if after.get("last_action_error") or not before.get("action"):
            continue
        new_lines = set(after.get("axtree", "").splitlines()) - set(
            before.get("axtree", "").splitlines()
        )
        changed_text = "\n".join(
            re.sub(r"\[\d+\]", "", line) for line in sorted(new_lines)
        )
        changed_url = before.get("url") != after.get("url")
        if CONFIRMATION.search(changed_text) or (
            changed_url and MUTATION.search(before.get("axtree", "")[-5000:])
        ):
            nominated.append(i)
    return nominated[-3:]


def accepted_review(reply: dict, allowed_indices: set[int]) -> bool:
    citations = reply.get("citations")
    return (
        reply.get("verdict") == "success"
        and reply.get("all_requirements_met") is True
        and isinstance(citations, list)
        and bool(citations)
        and all(type(i) is int and i in allowed_indices for i in citations)
    )
