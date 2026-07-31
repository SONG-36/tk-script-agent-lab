import re

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.ingestion_contracts import (
    ChunkingRequest,
    ChunkingResult,
    KnowledgeChunk,
    KnowledgeDocument,
    stable_chunk_id,
)

DEFAULT_CHUNKER_VERSION = "deterministic_paragraph_v1"


def normalize_knowledge_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized = "\n".join(line.rstrip(" \t") for line in normalized.split("\n"))
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


class DeterministicParagraphChunker:
    def chunk(self, request: ChunkingRequest) -> ChunkingResult:
        normalized = normalize_knowledge_text(request.document.content)
        if not normalized:
            return ChunkingResult(
                chunks=[],
                errors=[
                    ValidationError(
                        code="INGESTION_EMPTY_CONTENT",
                        message="KnowledgeDocument content is empty after normalization.",
                        object_type="KnowledgeDocument",
                        object_id=request.document.document_id,
                        field="content",
                        related_id=None,
                    )
                ],
            )

        chunks: list[KnowledgeChunk] = []
        sequence = 1
        current_start: int | None = None
        current_end: int | None = None

        def flush_current() -> None:
            nonlocal current_start, current_end, sequence
            if current_start is None or current_end is None:
                return
            chunks.append(
                _build_chunk(
                    request=request,
                    sequence=sequence,
                    content=normalized[current_start:current_end],
                    char_start=current_start,
                    char_end=current_end,
                )
            )
            sequence += 1
            current_start = None
            current_end = None

        for paragraph_start, paragraph_end in _paragraph_spans(normalized):
            paragraph_length = paragraph_end - paragraph_start
            if paragraph_length > request.max_chars:
                flush_current()
                for window_start, window_end in _fixed_windows(
                    paragraph_start,
                    paragraph_end,
                    max_chars=request.max_chars,
                    overlap_chars=request.overlap_chars,
                ):
                    chunks.append(
                        _build_chunk(
                            request=request,
                            sequence=sequence,
                            content=normalized[window_start:window_end],
                            char_start=window_start,
                            char_end=window_end,
                        )
                    )
                    sequence += 1
                continue

            if current_start is None:
                current_start = paragraph_start
                current_end = paragraph_end
                continue

            candidate_length = paragraph_end - current_start
            if candidate_length <= request.max_chars:
                current_end = paragraph_end
            else:
                flush_current()
                current_start = paragraph_start
                current_end = paragraph_end

        flush_current()
        return ChunkingResult(chunks=chunks, errors=[])


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    cursor = 0
    for paragraph in text.split("\n\n"):
        start = text.find(paragraph, cursor)
        end = start + len(paragraph)
        spans.append((start, end))
        cursor = end + 2
    return spans


def _fixed_windows(
    start: int,
    end: int,
    *,
    max_chars: int,
    overlap_chars: int,
) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    step = max_chars - overlap_chars
    cursor = start
    while cursor < end:
        window_end = min(cursor + max_chars, end)
        spans.append((cursor, window_end))
        if window_end == end:
            break
        cursor += step
    return spans


def _build_chunk(
    *,
    request: ChunkingRequest,
    sequence: int,
    content: str,
    char_start: int,
    char_end: int,
) -> KnowledgeChunk:
    document = request.document
    return KnowledgeChunk(
        chunk_id=stable_chunk_id(
            document_id=document.document_id,
            document_version=document.version,
            chunker_version=request.chunker_version,
            sequence=sequence,
            content=content,
        ),
        document_id=document.document_id,
        sequence=sequence,
        content=content,
        char_start=char_start,
        char_end=char_end,
        char_count=len(content),
        title=document.title,
        source=document.source,
        document_version=document.version,
        language=document.language,
        provenance_type=document.provenance_type,
        evidence_status=document.evidence_status,
        target_markets=document.target_markets,
        product_categories=document.product_categories,
        task_stages=document.task_stages,
        effective_from=document.effective_from,
        effective_to=document.effective_to,
        metadata=document.metadata,
        token_count=None,
    )
