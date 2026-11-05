import importlib.util
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts/score_webarena.py"
spec = importlib.util.spec_from_file_location("score_webarena", path)
scores = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scores)


def test_nontriggered_review_does_not_cost_selective_arm_and_missing_is_visible():
    rows = [
        {
            "task": "one",
            "agent": "x",
            "labels": ["Successful"],
            "baseline": False,
            "selective": True,
            "review_all": True,
            "trigger": [1],
        },
        {
            "task": "one",
            "agent": "y",
            "labels": ["Unsuccessful", "Successful"],
            "baseline": False,
            "selective": False,
            "review_all": True,
            "trigger": [],
        },
    ]
    for row in rows:
        row.update(
            split="test",
            status="complete",
            base_tokens=50,
            review_tokens=10,
            base_call_count=3,
            review_call_count=1,
            screening_parse_errors=0,
        )
    rows.append(
        {
            "task": "two",
            "agent": "x",
            "split": "test",
            "status": "no_completed_verdict",
            "labels": ["Successful"],
        }
    )
    report = scores.summarize(rows)["test"]
    assert report["expected"] == 3 and report["arms"]["selective"]["completed"] == 2
    assert report["arms"]["selective"]["rescued"] == 1
    assert report["arms"]["review_all"]["new_false_accept"] == 1
    assert report["arms"]["selective"]["new_false_accept"] == 0
    assert report["arms"]["selective"]["logical_tokens"] == 110
    assert report["arms"]["review_all"]["logical_tokens"] == 120
    assert report["unanimous_only"]["baseline"]["negatives"] == 0
