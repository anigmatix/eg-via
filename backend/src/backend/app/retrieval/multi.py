"""Composite retriever implementation."""

from __future__ import annotations

from collections.abc import Iterable

from backend.app.retrieval.base import BaseRetriever, RetrievalError, RetrievalResult
from backend.app.schemas import Citation, InterpretRequest


def _merge_unique(values: Iterable[str]) -> list[str]:
    merged: list[str] = []
    for value in values:
        if value and value not in merged:
            merged.append(value)
    return merged


def _citation_dedupe_key(
    citation: Citation,
) -> tuple[str, str | None, str | None, str | None, int | None]:
    return (citation.source, citation.raw_id, citation.url, citation.title, citation.year)


class MultiRetriever:
    """Execute multiple retrievers and merge their outputs."""

    name = "multi"

    def __init__(self, retrievers: list[BaseRetriever] | None = None) -> None:
        self._retrievers = retrievers or []

    def retrieve(self, request: InterpretRequest) -> RetrievalResult:
        all_queries: list[str] = []
        all_failures: list[str] = []
        unique_citations: dict[
            tuple[str, str | None, str | None, str | None, int | None], Citation
        ] = {}

        for retriever in self._retrievers:
            try:
                result = retriever.retrieve(request)
            except RetrievalError as exc:
                all_failures.append(str(exc))
                continue
            except Exception as exc:  # pragma: no cover - defensive fallback
                retriever_name = getattr(retriever, "name", retriever.__class__.__name__)
                all_failures.append(
                    f"retrieval.{retriever_name}: unexpected {exc.__class__.__name__}: {exc}"
                )
                continue

            all_queries.extend(result.queries)
            all_failures.extend(result.failures)
            for citation in result.citations:
                key = _citation_dedupe_key(citation)
                if key in unique_citations:
                    continue
                unique_citations[key] = citation

        deduped_citations = [
            citation.model_copy(update={"citation_id": f"C{index}"})
            for index, citation in enumerate(unique_citations.values(), start=1)
        ]

        return RetrievalResult(
            citations=deduped_citations,
            queries=_merge_unique(all_queries),
            failures=_merge_unique(all_failures),
        )
