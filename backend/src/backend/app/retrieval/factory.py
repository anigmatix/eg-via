"""Builder for retrieval toolchains from environment flags."""

from __future__ import annotations

import os

from backend.app.retrieval.base import BaseRetriever
from backend.app.retrieval.clinvar import ClinVarRetriever
from backend.app.retrieval.multi import MultiRetriever


def _parse_bool_env(value: str | None, *, default: bool) -> bool:
    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


def build_retriever_from_env() -> BaseRetriever:
    """Construct the retrieval toolchain based on feature flags."""

    retrievers: list[BaseRetriever] = []

    enable_clinvar = _parse_bool_env(
        os.getenv("EGVIA_ENABLE_CLINVAR"),
        default=False,
    )
    if enable_clinvar:
        retrievers.append(ClinVarRetriever())

    return MultiRetriever(retrievers)
