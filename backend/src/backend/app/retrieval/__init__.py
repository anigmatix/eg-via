"""Retrieval layer exports."""

from backend.app.retrieval.base import BaseRetriever, RetrievalError, RetrievalResult
from backend.app.retrieval.clinvar import (
    ClinVarRetriever,
    build_clinvar_queries,
    parse_clinvar_summary,
    retrieve_clinvar_citations,
)
from backend.app.retrieval.factory import build_retriever_from_env
from backend.app.retrieval.multi import MultiRetriever

__all__ = [
    "BaseRetriever",
    "ClinVarRetriever",
    "MultiRetriever",
    "RetrievalError",
    "RetrievalResult",
    "build_clinvar_queries",
    "build_retriever_from_env",
    "parse_clinvar_summary",
    "retrieve_clinvar_citations",
]
