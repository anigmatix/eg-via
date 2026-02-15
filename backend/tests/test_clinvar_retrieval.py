from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Ensure `backend/src` is importable when tests are run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from backend.app.retrieval.clinvar import (  # noqa: E402
    build_clinvar_queries,
    parse_clinvar_summary,
    retrieve_clinvar_citations,
)
from backend.app.schemas import InterpretRequest  # noqa: E402

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "clinvar"


def _load_fixture(name: str) -> dict[str, Any]:
    return json.loads((_FIXTURE_DIR / name).read_text())


class _StubResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict[str, Any]:
        return self._payload


class _StubClient:
    def __init__(self, payloads: list[dict[str, Any]]) -> None:
        self._payloads = payloads
        self.calls: list[dict[str, Any]] = []

    def get(self, url: str, params: dict[str, Any], timeout: float) -> _StubResponse:
        self.calls.append(
            {
                "url": url,
                "params": params,
                "timeout": timeout,
            }
        )
        payload = self._payloads.pop(0)
        return _StubResponse(payload)


def _build_request() -> InterpretRequest:
    return InterpretRequest(
        gene="BRCA1",
        hgvs="c.68_69delAG",
        variant_type="SNV",
        disease_context="breast cancer",
        assay_context="tumor-only",
    )


def test_build_clinvar_queries_contains_gene_and_hgvs() -> None:
    request = _build_request()
    queries = build_clinvar_queries(request)

    assert len(queries) >= 1
    primary_query = queries[0]
    assert "BRCA1" in primary_query
    assert "c.68_69delAG" in primary_query
    assert "[gene]" in primary_query
    assert "AND" in primary_query


def test_parse_clinvar_summary_normalizes_to_citations() -> None:
    summary_payload = _load_fixture("esummary_success.json")

    citations = parse_clinvar_summary(summary_payload)

    assert len(citations) == 2

    first = citations[0]
    assert first.citation_id == "C1"
    assert first.source == "ClinVar"
    assert first.raw_id == "VCV000000101"
    assert first.year == 2021
    assert first.metadata is not None
    assert first.metadata["classification"] == "Pathogenic"

    second = citations[1]
    assert second.citation_id == "C2"
    assert second.raw_id == "VCV000000202"
    assert second.year == 2018
    assert second.metadata is not None
    assert second.metadata["classification"] == "Likely pathogenic"


def test_retrieve_clinvar_citations_uses_fixture_payloads() -> None:
    request = _build_request()
    client = _StubClient(
        payloads=[
            _load_fixture("esearch_success.json"),
            _load_fixture("esummary_success.json"),
        ]
    )

    citations, queries = retrieve_clinvar_citations(
        request,
        client=client,  # type: ignore[arg-type]
        max_attempts=1,
        retry_wait_seconds=0.0,
    )

    assert len(citations) == 2
    assert len(queries) >= 1

    assert len(client.calls) == 2
    search_call = client.calls[0]
    assert "esearch.fcgi" in search_call["url"]
    assert search_call["params"]["db"] == "clinvar"
    assert "BRCA1" in search_call["params"]["term"]
    assert "c.68_69delAG" in search_call["params"]["term"]

    summary_call = client.calls[1]
    assert "esummary.fcgi" in summary_call["url"]
    assert summary_call["params"]["id"] == "101,202"
