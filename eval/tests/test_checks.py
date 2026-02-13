from __future__ import annotations

from eval.checks import (
    check_abstention,
    check_contract_presence,
    check_treatment_language_safety,
    check_trace_invariants,
    run_all_checks,
)


def _valid_response() -> dict[str, object]:
    return {
        "request_id": "req-123",
        "draft": {
            "summary": "Evidence is currently insufficient for a grounded interpretation.",
            "what_is_known": "No validated evidence claims were produced.",
            "conflicting_evidence": "No direct claim conflicts were identified.",
            "limitations": "This is a stub pipeline response.",
            "uncertainty": "Uncertainty is high due to absent claims and citations.",
            "disclaimer": "Assistive evidence synthesis only; not for diagnostic use.",
        },
        "evidence_table": [],
        "confidence_panel": {
            "confidence": 0.1,
            "reasons": ["Insufficient evidence."],
            "abstain": True,
            "abstain_reasons": ["No evidence available."],
        },
        "trace": {
            "request_id": "req-123",
            "retrieval_queries": ["EGFR c.2573T>G", "EGFR NSCLC somatic"],
            "source_count": 0,
            "claim_count": 0,
            "conflict_count": 0,
            "verification_checks": [],
            "verification_failures": [],
            "timings_ms": {"total": 15},
        },
    }


def test_all_checks_pass_for_valid_response() -> None:
    response = _valid_response()
    assert run_all_checks(response, expected_abstain=True) == []


def test_contract_presence_fails_on_missing_key() -> None:
    response = _valid_response()
    del response["draft"]
    errors = check_contract_presence(response)
    assert any("missing top-level key 'draft'" in err for err in errors)


def test_trace_invariants_fail_on_zero_total() -> None:
    response = _valid_response()
    response["trace"]["timings_ms"]["total"] = 0
    errors = check_trace_invariants(response)
    assert "trace.timings_ms.total must be > 0" in errors


def test_abstention_check_fails_when_expected_true_but_false() -> None:
    response = _valid_response()
    response["confidence_panel"]["abstain"] = False
    errors = check_abstention(response, expected_abstain=True)
    assert "expected abstain=true but response abstain=false" in errors


def test_safety_check_finds_treatment_language() -> None:
    response = _valid_response()
    response["draft"]["summary"] = "We recommend treatment."
    errors = check_treatment_language_safety(response)
    assert any("banned term stem" in err for err in errors)
