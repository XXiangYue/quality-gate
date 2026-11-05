from quality_gate.web_review import accepted_review, review_evidence


def test_claim_alone_never_nominates_a_frame():
    steps = [
        {
            "action": "click",
            "reasoning": "Order successfully placed",
            "url": "cart",
            "axtree": "Cart",
        },
        {"url": "cart", "axtree": "Cart", "reasoning": "Confirmation received"},
    ]
    assert review_evidence(steps) == []
    steps[1]["axtree"] = "Cart\nOrder confirmation"
    assert review_evidence(steps) == [1]
    steps[1]["last_action_error"] = "timed out"
    assert review_evidence(steps) == []


def test_only_cited_accessible_images_can_reverse_a_rejection():
    allowed = {0, 4}
    answer = {"verdict": "success", "all_requirements_met": True, "citations": [4]}
    assert accepted_review(answer, allowed)
    for citations in ([], [3], [True], ["4"]):
        assert not accepted_review(dict(answer, citations=citations), allowed)
    assert not accepted_review(dict(answer, all_requirements_met=False), allowed)
