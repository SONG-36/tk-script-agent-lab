from collections import Counter
from datetime import date
from hashlib import sha256
import json
import re
from unicodedata import normalize as unicode_normalize

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.contracts import (
    RetrievedKnowledge,
    RetrievalExclusion,
    RetrievalRequest,
    RetrievalResult,
    RetrievalTrace,
)
from tk_script_agent_lab.knowledge.index_contracts import KnowledgeIndex
from tk_script_agent_lab.knowledge.ingestion_contracts import KnowledgeChunk

RESERVED_METADATA_FIELDS = {
    "chunk_id",
    "document_id",
    "sequence",
    "document_version",
    "char_start",
    "char_end",
    "language",
}


class ExactMetadataKnowledgeRetriever:
    def __init__(
        self,
        index: KnowledgeIndex,
        *,
        retriever_version: str = "exact_metadata_v1",
    ) -> None:
        self._index = index
        self._retriever_version = retriever_version

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        chunks = list(self._index.snapshot())
        build_id = _index_build_id(self._index)
        candidate_ids = [chunk.chunk_id for chunk in chunks]
        filters_applied = _filters_applied(request)
        if not chunks:
            return _result(
                request=request,
                build_id=build_id,
                retriever_version=self._retriever_version,
                candidate_ids=[],
                selected=[],
                excluded=[],
                filters_applied=filters_applied,
                errors=[
                    ValidationError(
                        code="RETRIEVAL_INDEX_EMPTY",
                        message="Knowledge index has not been built.",
                        object_type="KnowledgeIndex",
                        object_id=None,
                        field=None,
                        related_id=None,
                    )
                ],
            )

        effective_on = request.filters.get("effective_on")
        effective_date: date | None = None
        if effective_on:
            try:
                effective_date = date.fromisoformat(effective_on)
            except ValueError:
                return _result(
                    request=request,
                    build_id=build_id,
                    retriever_version=self._retriever_version,
                    candidate_ids=candidate_ids,
                    selected=[],
                    excluded=[],
                    filters_applied=filters_applied,
                    errors=[
                        ValidationError(
                            code="RETRIEVAL_FILTER_INVALID",
                            message="effective_on must use YYYY-MM-DD.",
                            object_type="RetrievalRequest",
                            object_id=None,
                            field="filters.effective_on",
                            related_id=None,
                        )
                    ],
                )

        query = _normalized_text(request.query)
        terms = _query_terms(request.query)
        matches: list[tuple[KnowledgeChunk, float]] = []
        excluded: list[RetrievalExclusion] = []
        for chunk in chunks:
            reason = _metadata_exclusion(chunk, request, effective_date)
            if reason is None:
                score = _score(chunk, query, terms)
                if score is None:
                    reason = "query_no_match"
                else:
                    matches.append((chunk, score))
            if reason is not None:
                excluded.append(RetrievalExclusion(knowledge_id=chunk.chunk_id, reason=reason))

        ranked = sorted(
            matches,
            key=lambda item: (-item[1], item[0].document_id, item[0].sequence, item[0].chunk_id),
        )
        selected_pairs = ranked[: request.limit]
        over_limit = ranked[request.limit :]
        excluded.extend(
            RetrievalExclusion(knowledge_id=chunk.chunk_id, reason="over_limit")
            for chunk, _score_value in over_limit
        )
        selected = [_to_retrieved(chunk, score_value) for chunk, score_value in selected_pairs]
        return _result(
            request=request,
            build_id=build_id,
            retriever_version=self._retriever_version,
            candidate_ids=candidate_ids,
            selected=selected,
            excluded=excluded,
            filters_applied=filters_applied,
            errors=[],
        )


def _metadata_exclusion(
    chunk: KnowledgeChunk,
    request: RetrievalRequest,
    effective_date: date | None,
) -> str | None:
    if request.stage not in chunk.task_stages:
        return "stage_mismatch"
    if not _list_matches(chunk.target_markets, request.target_market):
        return "market_mismatch"
    if not _list_matches(chunk.product_categories, request.product_category):
        return "category_mismatch"
    if effective_date is not None:
        if chunk.effective_from is not None and chunk.effective_from > effective_date:
            return "not_effective"
        if chunk.effective_to is not None and chunk.effective_to < effective_date:
            return "not_effective"
    for key, expected in request.filters.items():
        if key == "effective_on":
            continue
        actual = chunk.metadata.get(key)
        if actual is None or _norm(actual) != _norm(expected):
            return f"metadata_mismatch:{key}"
    return None


def _score(chunk: KnowledgeChunk, normalized_query: str, terms: list[str]) -> float | None:
    title = _normalized_text(chunk.title)
    content = _normalized_text(chunk.content)
    combined = f"{title} {content}"
    phrase_match = normalized_query in title or normalized_query in content
    terms_match = all(term in combined for term in terms)
    if not phrase_match and not terms_match:
        return None
    score = 0
    if normalized_query in title:
        score += 100
    if normalized_query in content:
        score += 50
    for term in terms:
        if term in title:
            score += 10
        if term in content:
            score += 3
    return float(score)


def _to_retrieved(chunk: KnowledgeChunk, score: float) -> RetrievedKnowledge:
    reserved = {
        "chunk_id": chunk.chunk_id,
        "document_id": chunk.document_id,
        "sequence": str(chunk.sequence),
        "document_version": chunk.document_version,
        "char_start": str(chunk.char_start),
        "char_end": str(chunk.char_end),
        "language": chunk.language,
    }
    metadata = {key: value for key, value in chunk.metadata.items() if key not in RESERVED_METADATA_FIELDS}
    metadata.update(reserved)
    return RetrievedKnowledge(
        knowledge_id=chunk.chunk_id,
        title=chunk.title,
        content=chunk.content,
        kind=metadata.get("kind", "knowledge_chunk"),
        provenance_type=chunk.provenance_type,
        evidence_status=chunk.evidence_status,
        source_reference=chunk.source.source_reference,
        metadata=metadata,
        score=score,
    )


def _result(
    *,
    request: RetrievalRequest,
    build_id: str,
    retriever_version: str,
    candidate_ids: list[str],
    selected: list[RetrievedKnowledge],
    excluded: list[RetrievalExclusion],
    filters_applied: dict[str, str],
    errors: list[ValidationError],
) -> RetrievalResult:
    trace = RetrievalTrace(
        retriever_type="static",
        retriever_version=retriever_version,
        request_id=_stable_exact_request_id(request, build_id, retriever_version),
        candidate_ids=candidate_ids,
        selected_ids=[item.knowledge_id for item in selected],
        excluded=excluded,
        filters_applied=filters_applied,
    )
    return RetrievalResult(items=selected, trace=trace, errors=errors)


def _filters_applied(request: RetrievalRequest) -> dict[str, str]:
    values = {
        "query": request.query,
        "target_market": request.target_market,
        "product_category": request.product_category,
        "stage": request.stage,
        "effective_on": request.filters.get("effective_on", ""),
        "query_match_mode": "exact_all_terms_or_phrase",
        "ranking_version": "exact_rank_v1",
    }
    for key, value in request.filters.items():
        if key != "effective_on":
            values[f"metadata:{key}"] = value
    return values


def _stable_exact_request_id(
    request: RetrievalRequest,
    build_id: str,
    retriever_version: str,
) -> str:
    payload = {
        "request": request.model_dump(mode="json"),
        "index_build_id": build_id,
        "retriever_version": retriever_version,
    }
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return f"rr_{sha256(normalized.encode('utf-8')).hexdigest()[:12]}"


def _index_build_id(index: KnowledgeIndex) -> str:
    trace = getattr(index, "build_trace", None)
    trace_value = trace() if callable(trace) else trace
    build_id = getattr(trace_value, "build_id", None)
    return build_id or "ib_unbuilt"


def _norm(value: str) -> str:
    return unicode_normalize("NFKC", value).strip().casefold()


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicode_normalize("NFKC", value).casefold()).strip()


def _query_terms(query: str) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for term in re.findall(r"[\w]+", _normalized_text(query), flags=re.UNICODE):
        if term and term not in seen:
            seen.add(term)
            terms.append(term)
    return terms


def _list_matches(values: list[str], expected: str) -> bool:
    normalized = {_norm(value) for value in values}
    return "*" in normalized or _norm(expected) in normalized


def exclusion_reason_counts(result: RetrievalResult) -> dict[str, int]:
    return dict(Counter(item.reason for item in result.trace.excluded))
