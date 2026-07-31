from collections import Counter

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.index_contracts import (
    IndexBuildRequest,
    IndexBuildResult,
    IndexBuildTrace,
    stable_index_build_id,
)
from tk_script_agent_lab.knowledge.ingestion_contracts import KnowledgeChunk


class InMemoryKnowledgeIndex:
    def __init__(self) -> None:
        self._chunks: tuple[KnowledgeChunk, ...] = ()
        self._by_id: dict[str, KnowledgeChunk] = {}
        self._build_trace: IndexBuildTrace | None = None

    @property
    def build_trace(self) -> IndexBuildTrace | None:
        return self._build_trace.model_copy(deep=True) if self._build_trace else None

    def build(self, request: IndexBuildRequest) -> IndexBuildResult:
        input_chunk_ids = [chunk.chunk_id for chunk in request.chunks]
        duplicate_chunk_ids = sorted(
            chunk_id for chunk_id, count in Counter(input_chunk_ids).items() if count > 1
        )
        build_id = stable_index_build_id(index_version=request.index_version, chunks=request.chunks)
        if duplicate_chunk_ids:
            trace = IndexBuildTrace(
                build_id=build_id,
                index_type="in_memory",
                index_version=request.index_version,
                input_chunk_ids=input_chunk_ids,
                indexed_chunk_ids=[],
                rejected_chunk_ids=duplicate_chunk_ids,
                duplicate_chunk_ids=duplicate_chunk_ids,
                chunk_count=0,
            )
            return IndexBuildResult(
                trace=trace,
                errors=[
                    ValidationError(
                        code="INDEX_DUPLICATE_CHUNK_ID",
                        message="IndexBuildRequest contains duplicate chunk_id values.",
                        object_type="KnowledgeChunk",
                        object_id=chunk_id,
                        field="chunk_id",
                        related_id=chunk_id,
                    )
                    for chunk_id in duplicate_chunk_ids
                ],
            )

        ordered = tuple(
            chunk.model_copy(deep=True)
            for chunk in sorted(
                request.chunks,
                key=lambda item: (item.document_id, item.sequence, item.chunk_id),
            )
        )
        trace = IndexBuildTrace(
            build_id=build_id,
            index_type="in_memory",
            index_version=request.index_version,
            input_chunk_ids=input_chunk_ids,
            indexed_chunk_ids=[chunk.chunk_id for chunk in ordered],
            rejected_chunk_ids=[],
            duplicate_chunk_ids=[],
            chunk_count=len(ordered),
        )
        self._chunks = ordered
        self._by_id = {chunk.chunk_id: chunk for chunk in ordered}
        self._build_trace = trace
        return IndexBuildResult(trace=trace, errors=[])

    def get(self, chunk_id: str) -> KnowledgeChunk | None:
        chunk = self._by_id.get(chunk_id)
        return chunk.model_copy(deep=True) if chunk else None

    def snapshot(self) -> tuple[KnowledgeChunk, ...]:
        return tuple(chunk.model_copy(deep=True) for chunk in self._chunks)
