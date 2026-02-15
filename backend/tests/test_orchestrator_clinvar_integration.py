from __future__ import annotations

import sys
from pathlib import Path

# Ensure `backend/src` is importable when tests are run from repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import backend.app.orchestrator as orchestrator  # noqa: E402
from backend.app.retrieval.base import RetrievalResult  # noqa: E402
from backend.app.schemas import Citation, InterpretRequest  # noqa: E402


class FixtureRetriever:
    name = "fixture"

    def retrieve(self, _request: InterpretRequest) -> RetrievalResult:
        return RetrievalResult(
            citations=[
                Citation(
                    citation_id="C99",
                    source="ClinVar",
                    title="BRCA1 c.68_69delAG",
                    year=2021,
                    url="https://www.ncbi.nlm.nih.gov/clinvar/?term=VCV000000101",
                    raw_id="VCV000000101",
                ),
                Citation(
                    citation_id="C98",
                    source="PubMed",
                    title="BRCA1 variant report",
                    year=2018,
                    raw_id="12345678",
                ),
            ],
            queries=["BRCA1[gene] AND c.68_69delAG", "BRCA1 c.68_69delAG clinvar"],
        )


def _build_request() -> InterpretRequest:
    return InterpretRequest(
        gene="BRCA1",
        hgvs="c.68_69delAG",
        variant_type="SNV",
        disease_context="breast cancer",
        assay_context="tumor-only",
    )


def test_orchestrator_uses_retriever_interface_for_trace_and_source_count() -> None:
    request = _build_request()

    response = orchestrator.run_interpretation(request, retriever=FixtureRetriever())

    assert response.trace.source_count == 2
    assert response.trace.retrieval_queries == [
        "BRCA1[gene] AND c.68_69delAG",
        "BRCA1 c.68_69delAG clinvar",
    ]
    assert response.trace.timings_ms["retrieval"] > 0
    assert response.trace.claim_count == 0
    assert len(response.evidence_table) == response.trace.source_count
    assert response.evidence_table[0].citation.citation_id == "C99"
    assert response.evidence_table[0].claim.claim_id == "placeholder-C99"
    assert response.evidence_table[0].claim.citation_id == "C99"
    assert response.evidence_table[0].claim.supports_or_contradicts == "neutral"
    assert response.evidence_table[0].claim.evidence_strength == "Weak"
    assert "claim extraction not yet implemented" in response.evidence_table[0].claim.text
    assert response.evidence_table[1].citation.citation_id == "C98"
    assert response.evidence_table[1].claim.claim_id == "placeholder-C98"
    assert response.confidence_panel.abstain is True
