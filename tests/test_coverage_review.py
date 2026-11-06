import copy

from quality_gate.coverage_review import (
    answer_from_action,
    observation_pack,
    scoped_contract_errors,
    selected_frames,
    validate_coverage,
)


def fixture():
    contract = {
        "deliverable": "mutate",
        "conditions": [
            {"id": "C1", "requirement": "Create order", "match": "semantic"}
        ],
    }
    pages = observation_pack(
        [
            {
                "axtree": "Order #123 confirmed",
                "action": "send_msg_to_user('Order confirmed')",
            },
            {"axtree": "Order #123 confirmed"},
        ],
        "Create order",
    )
    response = {
        "verdict": "success",
        "checks": [
            {
                "id": "C1",
                "status": "met",
                "evidence": [
                    {"source": "page", "step": 1, "quote": "Order #123 confirmed"}
                ],
            }
        ],
    }
    return contract, pages, response


def test_citation_provenance_does_not_accept_claim_or_invented_quote():
    contract, pages, reply = fixture()
    assert validate_coverage(reply, contract, pages, {0}) == (True, [])
    for source, step, quote in [
        ("answer", 0, "Order confirmed"),
        ("page", 0, "Order #999 confirmed"),
        ("image", 1, "Order confirmed"),
        ("page", True, "Order #123 confirmed"),
    ]:
        broken = copy.deepcopy(reply)
        broken["checks"][0]["evidence"][0] = {
            "source": source,
            "step": step,
            "quote": quote,
        }
        assert not validate_coverage(broken, contract, pages, {0})[0]


def test_missing_or_repeated_conditions_cannot_pass():
    contract, pages, reply = fixture()
    for checks in [
        [],
        reply["checks"] * 2,
        [dict(reply["checks"][0], status="missing")],
    ]:
        assert not validate_coverage(dict(reply, checks=checks), contract, pages, {0})[
            0
        ]


def test_malformed_certificates_fail_closed():
    contract, pages, reply = fixture()
    assert not validate_coverage(
        dict(reply, checks=reply["checks"] + [None]), contract, pages, {0}
    )[0]
    assert not validate_coverage(None, contract, pages, {0})[0]
    assert not validate_coverage(reply, None, pages, {0})[0]
    assert not validate_coverage(reply, dict(contract, conditions=None), pages, {0})[0]


def test_action_claims_remain_separate_and_aliases_point_backward():
    assert answer_from_action("send_msg_to_user('done')") == "done"
    assert answer_from_action("click('done')") == ""
    assert answer_from_action("__import__('os').system('exit 1')") == ""
    _, pages, _ = fixture()
    assert pages[1]["same_page_as"] == 0
    assert "answer_to_user" not in pages[1]
    assert (
        "confirmed"
        not in observation_pack(
            [{"axtree": "Cart", "reasoning": "confirmed"}], "order"
        )[0]["page"]
    )


def test_partial_observations_disclose_elision_and_frames_include_final():
    pages = observation_pack(
        [{"axtree": "\n".join(f"unrelated line {i}" for i in range(2000))}],
        "needle",
        limit=1000,
    )
    assert pages[0]["partial_observation"]
    assert "[omitted lines]" in pages[0]["page"]
    assert selected_frames([5, 1, 4, 2, 0], 5) == [0, 2, 3, 4]


def test_scope_validation_does_not_turn_not_sent_into_send_required():
    goal = "Draft an email to request a refund"
    contract = {
        "deliverable": "draft",
        "conditions": [
            {
                "id": "C1",
                "requirement": "Email draft prepared, not sent",
                "user_span": "Draft an email",
                "match": "semantic",
            }
        ],
    }
    assert (
        scoped_contract_errors(contract, goal, ignore_negated_transmission=True) == []
    )
    contract["conditions"][0]["requirement"] = "Email is sent"
    assert scoped_contract_errors(contract, goal, ignore_negated_transmission=True) == [
        "draft_condition_requires_transmission"
    ]
    contract["conditions"][0]["user_span"] = "Submit a refund request"
    assert "condition_not_grounded_in_user_request" in scoped_contract_errors(
        contract, goal, ignore_negated_transmission=True
    )
