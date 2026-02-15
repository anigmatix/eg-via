"""ClinVar retrieval for citation metadata."""

from __future__ import annotations

import re
from typing import Any

import httpx
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from backend.app.retrieval.base import RetrievalError, RetrievalResult
from backend.app.schemas import Citation, InterpretRequest

_EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _normalized(value: str, fallback: str) -> str:
    normalized = value.strip()
    return normalized if normalized else fallback


def build_clinvar_queries(request: InterpretRequest) -> list[str]:
    """Build deterministic ClinVar-focused query terms from request inputs."""

    gene = _normalized(request.gene, "UNKNOWN_GENE")
    hgvs = _normalized(request.hgvs, "UNKNOWN_HGVS")

    candidates = [
        f"{gene}[gene] AND {hgvs}",
        f"{gene} {hgvs} clinvar",
    ]

    deduped: list[str] = []
    for query in candidates:
        if query not in deduped:
            deduped.append(query)
    return deduped


def _extract_year(value: str | None) -> int | None:
    if not value:
        return None
    match = re.search(r"\b(19|20)\d{2}\b", value)
    if not match:
        return None
    return int(match.group(0))


def _extract_summary_records(summary_payload: dict[str, Any]) -> list[dict[str, Any]]:
    result = summary_payload.get("result")
    if not isinstance(result, dict):
        return []

    uids = result.get("uids")
    if not isinstance(uids, list):
        return []

    records: list[dict[str, Any]] = []
    for uid in uids:
        if not isinstance(uid, str):
            continue
        record = result.get(uid)
        if isinstance(record, dict):
            records.append(record)
    return records


def parse_clinvar_summary(
    summary_payload: dict[str, Any],
    *,
    citation_start_index: int = 1,
) -> list[Citation]:
    """Normalize ClinVar summary payload into canonical Citation objects."""

    citations: list[Citation] = []
    for offset, record in enumerate(_extract_summary_records(summary_payload)):
        uid = str(record.get("uid", "")).strip() or None
        accession = str(record.get("accession", "")).strip() or None
        title = str(record.get("title", "")).strip() or None

        germline_classification = record.get("germline_classification")
        if not isinstance(germline_classification, dict):
            germline_classification = {}

        clinical_significance = record.get("clinical_significance")
        if not isinstance(clinical_significance, dict):
            clinical_significance = {}

        last_evaluated = (
            str(germline_classification.get("last_evaluated", "")).strip()
            or str(clinical_significance.get("last_evaluated", "")).strip()
            or None
        )

        raw_id = accession or uid
        record_url = (
            f"https://www.ncbi.nlm.nih.gov/clinvar/?term={raw_id}" if raw_id else None
        )

        metadata: dict[str, object] = {}
        classification = (
            str(germline_classification.get("description", "")).strip()
            or str(clinical_significance.get("description", "")).strip()
            or None
        )
        review_status = str(record.get("review_status", "")).strip() or None
        if classification:
            metadata["classification"] = classification
        if review_status:
            metadata["review_status"] = review_status
        if last_evaluated:
            metadata["last_evaluated"] = last_evaluated

        citations.append(
            Citation(
                citation_id=f"C{citation_start_index + offset}",
                source="ClinVar",
                title=title,
                year=_extract_year(last_evaluated),
                url=record_url,
                raw_id=raw_id,
                metadata=metadata or None,
            )
        )
    return citations


def _request_json(
    client: httpx.Client,
    *,
    url: str,
    params: dict[str, Any],
    max_attempts: int,
    retry_wait_seconds: float,
    timeout_s: float,
) -> dict[str, Any]:
    retrying = Retrying(
        stop=stop_after_attempt(max_attempts),
        wait=wait_fixed(retry_wait_seconds),
        retry=retry_if_exception_type((httpx.HTTPError, ValueError)),
        reraise=True,
    )

    for attempt in retrying:
        with attempt:
            response = client.get(url, params=params, timeout=timeout_s)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise ValueError("Expected JSON object response from ClinVar endpoint.")
            return payload

    raise RuntimeError("Retry loop terminated unexpectedly.")


def _extract_esearch_ids(search_payload: dict[str, Any]) -> list[str]:
    esearch_result = search_payload.get("esearchresult")
    if not isinstance(esearch_result, dict):
        return []

    idlist = esearch_result.get("idlist")
    if not isinstance(idlist, list):
        return []
    return [value for value in idlist if isinstance(value, str) and value.strip()]


class ClinVarRetriever:
    """Retrieval tool for ClinVar citations."""

    name = "clinvar"

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        max_records: int = 5,
        max_attempts: int = 3,
        retry_wait_seconds: float = 0.2,
        timeout_s: float = 10.0,
    ) -> None:
        self._client = client
        self._max_records = max_records
        self._max_attempts = max_attempts
        self._retry_wait_seconds = retry_wait_seconds
        self._timeout_s = timeout_s

    def retrieve(self, request: InterpretRequest) -> RetrievalResult:
        """Fetch and normalize ClinVar citations for a variant request."""

        queries = build_clinvar_queries(request)
        if not queries:
            return RetrievalResult(citations=[], queries=[])

        search_params = {
            "db": "clinvar",
            "retmode": "json",
            "retmax": self._max_records,
            "term": queries[0],
        }

        owns_client = self._client is None
        http_client = self._client or httpx.Client()

        try:
            search_payload = _request_json(
                http_client,
                url=f"{_EUTILS_BASE_URL}/esearch.fcgi",
                params=search_params,
                max_attempts=self._max_attempts,
                retry_wait_seconds=self._retry_wait_seconds,
                timeout_s=self._timeout_s,
            )
            ids = _extract_esearch_ids(search_payload)
            if not ids:
                return RetrievalResult(citations=[], queries=queries)

            summary_params = {
                "db": "clinvar",
                "retmode": "json",
                "id": ",".join(ids[: self._max_records]),
            }
            summary_payload = _request_json(
                http_client,
                url=f"{_EUTILS_BASE_URL}/esummary.fcgi",
                params=summary_params,
                max_attempts=self._max_attempts,
                retry_wait_seconds=self._retry_wait_seconds,
                timeout_s=self._timeout_s,
            )
            citations = parse_clinvar_summary(summary_payload)
            return RetrievalResult(citations=citations, queries=queries)
        except (httpx.HTTPError, ValueError) as exc:
            message = (
                f"retrieval.{self.name}: failed with {exc.__class__.__name__}: {exc}"
            )
            return RetrievalResult(citations=[], queries=queries, failures=[message])
        finally:
            if owns_client:
                http_client.close()


def retrieve_clinvar_citations(
    request: InterpretRequest,
    *,
    client: httpx.Client | None = None,
    max_records: int = 5,
    max_attempts: int = 3,
    retry_wait_seconds: float = 0.2,
    timeout_s: float = 10.0,
) -> tuple[list[Citation], list[str]]:
    """Compatibility wrapper around `ClinVarRetriever`."""

    retriever = ClinVarRetriever(
        client=client,
        max_records=max_records,
        max_attempts=max_attempts,
        retry_wait_seconds=retry_wait_seconds,
        timeout_s=timeout_s,
    )
    try:
        result = retriever.retrieve(request)
    except RetrievalError:
        return [], build_clinvar_queries(request)
    return result.citations, result.queries
