from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Ensure `backend/src` is importable when tests are run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.app.main import app  # noqa: E402


REQUIRED_DRAFT_FIELDS = (
    "summary",
    "what_is_known",
    "conflicting_evidence",
    "limitations",
    "uncertainty",
    "disclaimer",
)

REQUIRED_CONFIDENCE_FIELDS = (
    "confidence",
    "reasons",
    "abstain",
    "abstain_reasons",
)

REQUIRED_TRACE_FIELDS = (
    "request_id",
    "retrieval_queries",
    "source_count",
    "claim_count",
    "conflict_count",
    "verification_checks",
    "verification_failures",
    "timings_ms",
)

TREATMENT_BLACKLIST = ("treat", "therapy", "dose", "prescribe", "recommend")

VALID_INTERPRET_REQUEST = {
    "variant_type": "SNV",
    "assay_context": "somatic",
    "claims": [],
}


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _collect_text(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(_collect_text(item))
        return out
    if isinstance(value, dict):
        out: list[str] = []
        for item in value.values():
            out.extend(_collect_text(item))
        return out
    return []


def test_healthz_contract(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_interpret_contract_shape_and_stub_abstention(client: TestClient) -> None:
    response = client.post("/v1/interpret", json=VALID_INTERPRET_REQUEST)
    assert response.status_code == 200

    payload = response.json()

    request_id = payload.get("request_id")
    assert isinstance(request_id, str)
    assert request_id.strip()

    draft = payload.get("draft")
    assert isinstance(draft, dict)
    for field in REQUIRED_DRAFT_FIELDS:
        assert field in draft

    evidence_table = payload.get("evidence_table")
    assert isinstance(evidence_table, list)

    confidence_panel = payload.get("confidence_panel")
    assert isinstance(confidence_panel, dict)
    for field in REQUIRED_CONFIDENCE_FIELDS:
        assert field in confidence_panel
    assert isinstance(confidence_panel["confidence"], (int, float))
    assert 0.0 <= float(confidence_panel["confidence"]) <= 1.0
    assert isinstance(confidence_panel["reasons"], list)
    assert isinstance(confidence_panel["abstain"], bool)
    assert isinstance(confidence_panel["abstain_reasons"], list)

    # Stub mode invariant when no claims are supplied.
    assert confidence_panel["abstain"] is True
    assert len(confidence_panel["abstain_reasons"]) > 0

    trace = payload.get("trace")
    assert isinstance(trace, dict)
    for field in REQUIRED_TRACE_FIELDS:
        assert field in trace
    assert trace["request_id"] == request_id
    assert isinstance(trace["retrieval_queries"], list)
    assert len(trace["retrieval_queries"]) > 0
    assert "timings_ms" in trace
    assert "total" in trace["timings_ms"]
    assert trace["timings_ms"]["total"] > 0

    # Safety invariant: draft text must avoid treatment recommendation language.
    draft_text = " ".join(_collect_text(draft)).lower()
    for banned in TREATMENT_BLACKLIST:
        assert re.search(rf"\b{re.escape(banned)}\w*\b", draft_text) is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("variant_type", "CNV"),
        ("assay_context", "foo"),
    ],
)
def test_interpret_rejects_invalid_enum_values(
    client: TestClient, field: str, value: str
) -> None:
    payload = dict(VALID_INTERPRET_REQUEST)
    payload[field] = value

    response = client.post("/v1/interpret", json=payload)
    assert response.status_code == 422
