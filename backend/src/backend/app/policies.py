"""Deterministic safety and abstention policies for MVP stub mode."""

from __future__ import annotations

import re

from backend.app.schemas import ConfidencePanel

_TREATMENT_PATTERN = re.compile(r"\b(treat\w*|therapy\w*|dose\w*|prescribe\w*|recommend\w*)\b", re.IGNORECASE)


def contains_treatment_language(text: str) -> bool:
    """Return True if text includes treatment-like language."""

    return _TREATMENT_PATTERN.search(text) is not None


def build_abstention_panel(
    claim_count: int,
    conflict_count: int,
    source_count: int,
) -> ConfidencePanel:
    """Build deterministic confidence output for the current evidence state."""

    if claim_count == 0:
        reasons = [
            "No claims extracted after schema validation.",
            "Interpretation is abstained because evidence is missing.",
        ]
        abstain_reasons = [
            "No claims extracted after schema validation.",
            "Insufficient evidence for citation-grounded interpretation.",
        ]
        if source_count == 0:
            reasons.insert(0, "No sources retrieved (retrieval stub).")
            abstain_reasons.insert(0, "No sources retrieved (retrieval stub).")

        return ConfidencePanel(
            confidence=0.1,
            reasons=reasons,
            abstain=True,
            abstain_reasons=abstain_reasons,
        )

    reasons = ["At least one claim was available."]
    if conflict_count > 0:
        reasons.append("Conflicting evidence detected.")

    return ConfidencePanel(
        confidence=0.4 if conflict_count > 0 else 0.6,
        reasons=reasons,
        abstain=conflict_count > 0,
        abstain_reasons=["Conflicting evidence is too high."] if conflict_count > 0 else [],
    )
