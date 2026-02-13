"""Pydantic schemas for the EG-VIA API contract."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator


class VariantType(str, Enum):
    """Supported variant types for MVP."""

    SNV = "SNV"
    INDEL = "indel"


class AssayContext(str, Enum):
    """Supported assay contexts.

    `somatic` is accepted as a compatibility alias for existing tests.
    """

    TUMOR_ONLY = "tumor-only"
    TUMOR_NORMAL = "tumor-normal"
    PANEL = "panel"
    WES = "WES"
    SOMATIC = "somatic"


class InterpretRequest(BaseModel):
    """Input payload for POST /v1/interpret.

    Canonical v1 fields are present. Defaults keep stub mode backward-compatible
    with the current contract tests that send a minimal payload.
    """

    gene: str = ""
    hgvs: str = ""
    variant_type: VariantType
    disease_context: str = ""
    assay_context: AssayContext
    user_question: str | None = None


class Citation(BaseModel):
    """Citation metadata tied to evidence."""

    citation_id: str
    source: str
    title: str | None = None
    year: int | None = None
    url: str | None = None
    raw_id: str | None = None
    metadata: dict[str, object] | None = None


class Claim(BaseModel):
    """Claim extracted from evidence and bound to one citation."""

    claim_id: str
    text: str
    citation_id: str
    supports_or_contradicts: str
    evidence_strength: str
    year: int | None = None

    @field_validator("supports_or_contradicts")
    @classmethod
    def validate_supports_or_contradicts(cls, value: str) -> str:
        allowed = {"support", "contradict", "neutral"}
        if value not in allowed:
            raise ValueError(f"supports_or_contradicts must be one of: {sorted(allowed)}")
        return value

    @field_validator("evidence_strength")
    @classmethod
    def validate_evidence_strength(cls, value: str) -> str:
        allowed = {"Strong", "Moderate", "Weak"}
        if value not in allowed:
            raise ValueError(f"evidence_strength must be one of: {sorted(allowed)}")
        return value


class EvidenceTableEntry(BaseModel):
    """One citation + one claim entry."""

    citation: Citation
    claim: Claim


class Draft(BaseModel):
    """Interpretation draft text blocks."""

    summary: str
    what_is_known: str
    conflicting_evidence: str
    limitations: str
    uncertainty: str
    disclaimer: str


class ConfidencePanel(BaseModel):
    """Confidence + abstention metadata."""

    confidence: float = Field(ge=0.0, le=1.0)
    reasons: list[str]
    abstain: bool
    abstain_reasons: list[str]


class Trace(BaseModel):
    """Execution trace metadata for transparency."""

    request_id: str
    retrieval_queries: list[str]
    source_count: int
    claim_count: int
    conflict_count: int
    verification_checks: list[str]
    verification_failures: list[str]
    timings_ms: dict[str, int]


class InterpretResponse(BaseModel):
    """Output payload for POST /v1/interpret."""

    request_id: str
    draft: Draft
    evidence_table: list[EvidenceTableEntry]
    confidence_panel: ConfidencePanel
    trace: Trace


class HealthzResponse(BaseModel):
    """Health check response."""

    status: str

