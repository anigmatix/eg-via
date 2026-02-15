"""Configuration helpers for retrieval feature flags."""

from __future__ import annotations

import os
from dataclasses import dataclass


def _parse_bool_env(value: str | None, *, default: bool) -> bool:
    """Parse a truthy/falsey environment string deterministically."""

    if value is None:
        return default

    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class RetrievalConfig:
    """Feature flags controlling retrieval integrations."""

    enable_clinvar: bool = False


def get_retrieval_config() -> RetrievalConfig:
    """Load retrieval feature flags from environment variables."""

    return RetrievalConfig(
        enable_clinvar=_parse_bool_env(
            os.getenv("EGVIA_ENABLE_CLINVAR"),
            default=False,
        )
    )
