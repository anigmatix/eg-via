"""Stub orchestrator for the EG-VIA backend contract spine."""

from __future__ import annotations

from backend.app.policies import build_abstention_panel, contains_treatment_language
from backend.app.schemas import Draft, InterpretRequest, InterpretResponse, Trace
from backend.app.trace import elapsed_between_ms, new_request_id, start_timer


def _normalized(value: str, fallback: str) -> str:
    """Normalize user input for deterministic query construction."""

    normalized = value.strip()
    return normalized if normalized else fallback


def _build_retrieval_queries(request: InterpretRequest) -> list[str]:
    """Build deterministic, request-derived retrieval query candidates."""

    gene = _normalized(request.gene, "UNKNOWN_GENE")
    hgvs = _normalized(request.hgvs, "UNKNOWN_HGVS")
    disease_context = _normalized(request.disease_context, "unspecified_disease")
    assay_hint = request.assay_context.value

    queries = [
        f"{gene} {hgvs}",
        f"{gene} {disease_context} somatic",
        f"{gene} {hgvs} {assay_hint}",
    ]

    deduped: list[str] = []
    for query in queries:
        if query not in deduped:
            deduped.append(query)
    return deduped[:4]


def _build_stub_draft() -> Draft:
    """Create a safe, uncertainty-forward draft without treatment content."""

    draft = Draft(
        summary="Evidence is currently insufficient to produce a citation-grounded interpretation.",
        what_is_known="No validated evidence claims were produced in this run.",
        conflicting_evidence="No direct claim conflicts were identified because no claims were extracted.",
        limitations="This is a stub pipeline response with empty retrieval and extraction outputs.",
        uncertainty="Uncertainty is high due to absence of supporting claims and citations.",
        disclaimer="For assistive evidence synthesis only; not for diagnostic or therapeutic decision use.",
    )

    return draft


def _verify_draft_language(draft: Draft) -> None:
    """Block treatment-like language to preserve safety constraints."""

    for value in draft.model_dump().values():
        if contains_treatment_language(value):
            raise ValueError("Draft contains blocked treatment-like language.")


def run_interpretation(request: InterpretRequest) -> InterpretResponse:
    """Run the deterministic stub pipeline and return a contract-valid response."""

    total_start = start_timer()
    request_id = new_request_id()

    # Retrieval stage (stub): produce deterministic would-run query strings.
    retrieval_start = start_timer()
    retrieval_queries = _build_retrieval_queries(request)
    retrieval_end = start_timer()

    # Extraction stage (stub): no sources and no claims.
    extraction_start = start_timer()
    evidence_table = []
    source_count = 0
    claim_count = 0
    conflict_count = 0
    extraction_end = start_timer()

    # Synthesis stage (stub): deterministic uncertainty-forward draft.
    synthesis_start = start_timer()
    draft = _build_stub_draft()
    synthesis_end = start_timer()

    # Verification stage (stub): language safety gate + abstention gate.
    verification_start = start_timer()
    _verify_draft_language(draft)
    confidence_panel = build_abstention_panel(
        claim_count=claim_count,
        conflict_count=conflict_count,
        source_count=source_count,
    )
    verification_end = start_timer()

    trace = Trace(
        request_id=request_id,
        retrieval_queries=retrieval_queries,
        source_count=source_count,
        claim_count=claim_count,
        conflict_count=conflict_count,
        verification_checks=[
            "claim_citation_binding",
            "treatment_language_block",
            "abstention_gate",
        ],
        verification_failures=[],
        timings_ms={
            "retrieval": elapsed_between_ms(retrieval_start, retrieval_end),
            "extraction": elapsed_between_ms(extraction_start, extraction_end),
            "synthesis": elapsed_between_ms(synthesis_start, synthesis_end),
            "verification": elapsed_between_ms(verification_start, verification_end),
            "total": elapsed_between_ms(total_start, verification_end),
        },
    )

    return InterpretResponse(
        request_id=request_id,
        draft=draft,
        evidence_table=evidence_table,
        confidence_panel=confidence_panel,
        trace=trace,
    )
