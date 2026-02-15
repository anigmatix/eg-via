"""Shared retrieval tool interfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from backend.app.schemas import Citation, InterpretRequest


class RetrievalError(RuntimeError):
    """Recoverable retrieval failure."""


@dataclass(slots=True)
class RetrievalResult:
    """Canonical output from a retrieval tool."""

    citations: list[Citation] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)


class BaseRetriever(Protocol):
    """Interface implemented by retrieval tools."""

    name: str

    def retrieve(self, request: InterpretRequest) -> RetrievalResult:
        """Fetch citations for `request`."""
