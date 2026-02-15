from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def default_disable_clinvar(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep network-backed retrieval off unless a test enables it explicitly."""

    monkeypatch.setenv("EGVIA_ENABLE_CLINVAR", "false")
