import copy
import random

from quality_gate.quality import (
    reference_artifact,
    verify_artifact,
    reference_business,
    verify_business,
)


def test_independent_reference_and_legal_ordering():
    candidate, oracle = reference_artifact(random.Random(23), "independent-unit")
    assert verify_artifact(candidate, oracle)["passed"]
    candidate["predictions"].reverse()
    from quality_gate.common import digest

    candidate["report_prediction_sha256"] = digest(candidate["predictions"])
    assert verify_artifact(candidate, oracle)["passed"]
    candidate["metrics"]["n"] -= 1
    assert "denominator" in verify_artifact(candidate, oracle)["failures"]


def test_answered_text_does_not_replace_business_state():
    candidate, oracle = reference_business(random.Random(17), "independent-unit")
    candidate["success"] = True
    candidate["ticket"]["status"] = "open"
    assert not verify_business(candidate, oracle)["passed"]
    candidate["ticket"]["status"] = "closed"
    candidate["knowledge"]["indexed_version"] -= 1
    assert "index_current" in verify_business(candidate, oracle)["failures"]


def test_malformed_candidate_and_invalid_oracle_are_distinct():
    from quality_gate.quality import verify, OracleError
    import pytest

    c, o = reference_artifact(random.Random(17), "malformed")
    c["metrics"] = None
    assert not verify("artifact", c, o)["passed"]
    with pytest.raises(OracleError):
        verify("artifact", c, {})
