"""Dataset loading utilities for eval harness."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUEST_REQUIRED_FIELDS = (
    "gene",
    "hgvs",
    "variant_type",
    "disease_context",
    "assay_context",
)
REQUEST_OPTIONAL_FIELDS = ("user_question",)


@dataclass(frozen=True)
class EvalCase:
    """One evaluation case from JSONL."""

    case_id: str
    request: dict[str, Any]
    expected_abstain: bool


def _read_json_line(raw_line: str, line_no: int, data_path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(raw_line)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{data_path}:{line_no} is not valid JSON: {exc.msg}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{data_path}:{line_no} must be a JSON object")
    return payload


def _build_request(payload: dict[str, Any], line_no: int, data_path: Path) -> dict[str, Any]:
    request: dict[str, Any] = {}
    for field in REQUEST_REQUIRED_FIELDS:
        value = payload.get(field)
        if not isinstance(value, str):
            raise ValueError(f"{data_path}:{line_no} missing string field '{field}'")
        request[field] = value

    for field in REQUEST_OPTIONAL_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(
                f"{data_path}:{line_no} optional field '{field}' must be string or null"
            )
        request[field] = value

    return request


def _build_case(payload: dict[str, Any], line_no: int, data_path: Path) -> EvalCase:
    expected = payload.get("expected")
    if not isinstance(expected, dict):
        raise ValueError(f"{data_path}:{line_no} must include object field 'expected'")

    expected_abstain = expected.get("expected_abstain")
    if not isinstance(expected_abstain, bool):
        raise ValueError(
            f"{data_path}:{line_no} expected.expected_abstain must be boolean"
        )

    case_id = payload.get("case_id")
    if case_id is None:
        case_id = f"line-{line_no}"
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError(f"{data_path}:{line_no} case_id must be a non-empty string")

    request = _build_request(payload=payload, line_no=line_no, data_path=data_path)

    return EvalCase(
        case_id=case_id.strip(),
        request=request,
        expected_abstain=expected_abstain,
    )


def load_cases(data_path: Path) -> list[EvalCase]:
    """Load JSONL cases from disk."""

    if not data_path.exists():
        raise ValueError(f"Dataset file not found: {data_path}")

    cases: list[EvalCase] = []
    with data_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            payload = _read_json_line(stripped, line_no=line_no, data_path=data_path)
            cases.append(_build_case(payload, line_no=line_no, data_path=data_path))

    if not cases:
        raise ValueError(f"Dataset is empty: {data_path}")

    return cases
