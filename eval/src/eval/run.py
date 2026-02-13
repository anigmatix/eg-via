"""CLI runner for EG-VIA deterministic eval harness."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from eval.checks import run_all_checks
from eval.dataset import EvalCase, load_cases


@dataclass(frozen=True)
class CaseResult:
    """Execution result for one case."""

    case_id: str
    passed: bool
    errors: list[str]


class BackendUnavailableError(RuntimeError):
    """Raised when backend cannot be reached."""


def _post_interpret(
    client: httpx.Client,
    base_url: str,
    payload: dict[str, Any],
    timeout: float,
    retries: int,
) -> httpx.Response:
    endpoint = f"{base_url.rstrip('/')}/v1/interpret"
    attempts = retries + 1
    last_exc: httpx.RequestError | None = None

    for _attempt in range(attempts):
        try:
            return client.post(endpoint, json=payload, timeout=timeout)
        except httpx.RequestError as exc:
            last_exc = exc

    assert last_exc is not None  # for type narrowing
    raise BackendUnavailableError(str(last_exc)) from last_exc


def evaluate_case(
    client: httpx.Client,
    case: EvalCase,
    base_url: str,
    timeout: float,
    retries: int,
) -> CaseResult:
    """Call backend and run deterministic checks for one case."""

    try:
        response = _post_interpret(
            client=client,
            base_url=base_url,
            payload=case.request,
            timeout=timeout,
            retries=retries,
        )
    except BackendUnavailableError:
        raise

    errors: list[str] = []
    if response.status_code != 200:
        errors.append(f"HTTP {response.status_code}: {response.text[:200]}")
        return CaseResult(case_id=case.case_id, passed=False, errors=errors)

    try:
        payload = response.json()
    except ValueError as exc:
        errors.append(f"response is not valid JSON: {exc}")
        return CaseResult(case_id=case.case_id, passed=False, errors=errors)

    if not isinstance(payload, dict):
        errors.append("response JSON must be an object")
        return CaseResult(case_id=case.case_id, passed=False, errors=errors)

    errors.extend(run_all_checks(payload, expected_abstain=case.expected_abstain))
    return CaseResult(case_id=case.case_id, passed=not errors, errors=errors)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic EG-VIA API eval checks against a local backend."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for backend API (default: %(default)s)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        required=True,
        help="Path to JSONL evaluation dataset.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Request timeout in seconds (default: %(default)s).",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=0,
        help="Number of retries after request errors (default: %(default)s).",
    )
    return parser.parse_args()


def main() -> int:
    """CLI entrypoint."""

    args = _parse_args()
    try:
        cases = load_cases(args.data)
    except ValueError as exc:
        print(f"[ERROR] Invalid dataset: {exc}")
        return 2

    print(f"Running {len(cases)} eval case(s) against {args.base_url}")

    results: list[CaseResult] = []
    with httpx.Client() as client:
        for case in cases:
            try:
                result = evaluate_case(
                    client=client,
                    case=case,
                    base_url=args.base_url,
                    timeout=args.timeout,
                    retries=args.retries,
                )
            except BackendUnavailableError as exc:
                print(
                    "[ERROR] Backend unavailable. "
                    f"Could not reach {args.base_url}/v1/interpret: {exc}"
                )
                return 2

            if result.passed:
                print(f"[PASS] {result.case_id}")
            else:
                print(f"[FAIL] {result.case_id}")
                for error in result.errors:
                    print(f"  - {error}")
            results.append(result)

    failures = [result for result in results if not result.passed]
    passed = len(results) - len(failures)
    print(f"Summary: total={len(results)} passed={passed} failed={len(failures)}")

    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
