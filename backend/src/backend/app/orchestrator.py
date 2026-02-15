"""Stub orchestrator for the EG-VIA backend contract spine."""

from __future__ import annotations

from backend.app.policies import build_abstention_panel, contains_treatment_language
from backend.app.retrieval import BaseRetriever, RetrievalError, build_retriever_from_env
from backend.app.schemas import (
    Claim,
    Citation,
    Draft,
    EvidenceTableEntry,
    InterpretRequest,
    InterpretResponse,
    Trace,
)
from backend.app.trace import elapsed_between_ms, new_request_id, start_timer


def _build_stub_draft(*, source_count: int, claim_count: int) -> Draft:
    """Create a safe, uncertainty-forward draft without treatment content."""

    if source_count > 0 and claim_count == 0:
        what_is_known = (
            f"{source_count} evidence source(s) were retrieved, but no validated claims are "
            "available yet."
        )
        limitations = (
            "Evidence sources were retrieved, but claim extraction is not yet "
            "implemented; no validated claims were produced."
        )
    else:
        what_is_known = "No validated evidence claims were produced in this run."
        limitations = (
            "No sources were retrieved in this run, and claim extraction remains "
            "stubbed."
        )

    draft = Draft(
        summary="Evidence is currently insufficient to produce a citation-grounded interpretation.",
        what_is_known=what_is_known,
        conflicting_evidence="No direct claim conflicts were identified because no claims were extracted.",
        limitations=limitations,
        uncertainty="Uncertainty is high due to absence of supporting claims and citations.",
        disclaimer="For assistive evidence synthesis only; not for diagnostic or therapeutic decision use.",
    )

    return draft


def _verify_draft_language(draft: Draft) -> None:
    """Block treatment-like language to preserve safety constraints."""

    for value in draft.model_dump().values():
        if contains_treatment_language(value):
            raise ValueError("Draft contains blocked treatment-like language.")


def _build_placeholder_evidence_table(
    retrieved_citations: list[Citation],
) -> list[EvidenceTableEntry]:
    """Represent retrieved sources without asserting biomedical claims."""

    entries: list[EvidenceTableEntry] = []
    for citation in retrieved_citations:
        claim = Claim(
            claim_id=f"placeholder-{citation.citation_id}",
            text=(
                f"Source retrieved from {citation.source}; claim extraction not yet "
                "implemented for this citation."
            ),
            citation_id=citation.citation_id,
            supports_or_contradicts="neutral",
            evidence_strength="Weak",
            year=citation.year,
        )
        entries.append(EvidenceTableEntry(citation=citation, claim=claim))
    return entries


def run_interpretation(
    request: InterpretRequest,
    *,
    retriever: BaseRetriever | None = None,
) -> InterpretResponse:
    """Run the deterministic stub pipeline and return a contract-valid response."""

    total_start = start_timer()
    request_id = new_request_id()

    active_retriever = retriever or build_retriever_from_env()

    # Retrieval stage: delegated entirely to the retrieval tool interface.
    retrieval_start = start_timer()
    retrieved_citations = []
    retrieval_queries: list[str] = []
    retrieval_failures: list[str] = []
    try:
        retrieval_result = active_retriever.retrieve(request)
        retrieved_citations = retrieval_result.citations
        retrieval_queries = retrieval_result.queries
        retrieval_failures = retrieval_result.failures
    except RetrievalError as exc:
        retrieval_failures.append(str(exc))
    except Exception as exc:  # pragma: no cover - defensive fallback
        retrieval_failures.append(
            f"retrieval.interface: unexpected {exc.__class__.__name__}: {exc}"
        )
    retrieval_end = start_timer()

    # Extraction stage (stub): no validated claims yet, even when sources are retrieved.
    extraction_start = start_timer()
    evidence_table = _build_placeholder_evidence_table(retrieved_citations)
    source_count = len(retrieved_citations)
    claim_count = 0
    conflict_count = 0
    extraction_end = start_timer()

    # Synthesis stage (stub): deterministic uncertainty-forward draft.
    synthesis_start = start_timer()
    draft = _build_stub_draft(source_count=source_count, claim_count=claim_count)
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
        verification_failures=retrieval_failures,
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
