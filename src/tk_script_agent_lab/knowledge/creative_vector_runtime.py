from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
import json

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.chunking import DEFAULT_CHUNKER_VERSION
from tk_script_agent_lab.knowledge.contracts import RetrievalRequest, RetrievalResult
from tk_script_agent_lab.knowledge.creative_pack_documents import creative_pack_to_documents
from tk_script_agent_lab.knowledge.embedding_contracts import (
    EmbeddingItem,
    EmbeddingProvider,
    EmbeddingRequest,
    EmbeddingResult,
    EmbeddingTrace,
)
from tk_script_agent_lab.knowledge.ingestion_contracts import IngestionRequest, IngestionTrace
from tk_script_agent_lab.knowledge.ingestor import DEFAULT_INGESTOR_VERSION, DeterministicKnowledgeIngestor
from tk_script_agent_lab.knowledge.loader import KnowledgePackError, load_creative_knowledge_pack
from tk_script_agent_lab.knowledge.openai_embedding import (
    OPENAI_EMBEDDING_PROVIDER_VERSION,
    OpenAIEmbeddingProvider,
)
from tk_script_agent_lab.knowledge.qdrant_vector_store import QdrantLocalVectorStore
from tk_script_agent_lab.knowledge.vector_retriever import VectorKnowledgeRetriever
from tk_script_agent_lab.knowledge.vector_store_contracts import VectorBuildRequest, VectorBuildTrace, VectorIndexItem


@dataclass(frozen=True)
class CreativeVectorRuntimeBuild:
    runtime: "CreativeVectorRuntime | None"
    errors: list[ValidationError]
    runtime_built: bool
    runtime_reused: bool


@dataclass(frozen=True)
class CreativeVectorRetrievalRun:
    result: RetrievalResult
    query_embedding_trace: EmbeddingTrace | None
    query_embedding_calls: int


class CreativeVectorRuntime:
    def __init__(
        self,
        *,
        pack_id: str,
        pack_version: str,
        collection_name: str,
        retriever: VectorKnowledgeRetriever,
        embedding_provider: "_RecordingEmbeddingProvider",
        ingestion_trace: IngestionTrace,
        document_embedding_trace: EmbeddingTrace,
        vector_build_trace: VectorBuildTrace,
        document_embedding_calls: int,
    ) -> None:
        self.pack_id = pack_id
        self.pack_version = pack_version
        self.collection_name = collection_name
        self.retriever = retriever
        self._embedding_provider = embedding_provider
        self.ingestion_trace = ingestion_trace
        self.document_embedding_trace = document_embedding_trace
        self.vector_build_trace = vector_build_trace
        self.document_embedding_calls = document_embedding_calls

    def retrieve(self, request: RetrievalRequest) -> CreativeVectorRetrievalRun:
        calls_before = self._embedding_provider.call_count
        result = self.retriever.retrieve(request)
        return CreativeVectorRetrievalRun(
            result=result,
            query_embedding_trace=self._embedding_provider.last_trace,
            query_embedding_calls=self._embedding_provider.call_count - calls_before,
        )


_RUNTIMES: dict[str, CreativeVectorRuntime] = {}


def reset_creative_vector_runtime_cache() -> None:
    _RUNTIMES.clear()


def get_or_build_creative_vector_runtime(
    *,
    pack_id: str,
    embedding_model: str,
    retriever_version: str,
    embedding_provider: EmbeddingProvider | None = None,
    vector_store_factory: Callable[[], QdrantLocalVectorStore] | None = None,
) -> CreativeVectorRuntimeBuild:
    try:
        pack = load_creative_knowledge_pack(pack_id)
    except KnowledgePackError as exc:
        return CreativeVectorRuntimeBuild(None, [_error(exc.code, str(exc), "pack_id", pack_id)], False, False)
    runtime_key = _runtime_key(pack.pack_id, pack.version, embedding_model, retriever_version)
    cached = _RUNTIMES.get(runtime_key)
    if cached is not None:
        return CreativeVectorRuntimeBuild(cached, [], False, True)

    documents = creative_pack_to_documents(pack)
    ingestion = DeterministicKnowledgeIngestor().ingest(
        IngestionRequest(
            documents=documents,
            max_chars=1000,
            overlap_chars=80,
            chunker_version=DEFAULT_CHUNKER_VERSION,
            ingestor_version=DEFAULT_INGESTOR_VERSION,
        )
    )
    if ingestion.errors:
        return CreativeVectorRuntimeBuild(None, ingestion.errors, False, False)

    recorder = _RecordingEmbeddingProvider(embedding_provider or OpenAIEmbeddingProvider())
    calls_before = recorder.call_count
    embedding = recorder.embed(
        EmbeddingRequest(
            items=[EmbeddingItem(item_id=chunk.chunk_id, text=f"{chunk.title}\n{chunk.content}") for chunk in ingestion.chunks],
            model=embedding_model,
            provider_version=OPENAI_EMBEDDING_PROVIDER_VERSION,
        )
    )
    document_embedding_calls = recorder.call_count - calls_before
    if embedding.errors:
        return CreativeVectorRuntimeBuild(None, embedding.errors, False, False)
    if len(embedding.vectors) != len(ingestion.chunks):
        return CreativeVectorRuntimeBuild(
            None,
            [_error("EMBEDDING_OUTPUT_INVALID", "Document embedding output count does not match chunk count.", "vectors", None)],
            False,
            False,
        )

    collection_name = _collection_name(pack.pack_id, pack.version, embedding_model, retriever_version)
    store = (vector_store_factory or QdrantLocalVectorStore)()
    vector_build = store.build(
        VectorBuildRequest(
            items=[
                VectorIndexItem(chunk=chunk, vector=vector)
                for chunk, vector in zip(ingestion.chunks, embedding.vectors, strict=True)
            ],
            collection_name=collection_name,
            index_version="qdrant_local_v1",
        )
    )
    if vector_build.errors:
        return CreativeVectorRuntimeBuild(None, vector_build.errors, False, False)

    runtime = CreativeVectorRuntime(
        pack_id=pack.pack_id,
        pack_version=pack.version,
        collection_name=collection_name,
        retriever=VectorKnowledgeRetriever(
            embedding_provider=recorder,
            vector_store=store,
            embedding_model=embedding_model,
            collection_name=collection_name,
            retriever_version=retriever_version,
        ),
        embedding_provider=recorder,
        ingestion_trace=ingestion.trace,
        document_embedding_trace=embedding.trace,
        vector_build_trace=vector_build.trace,
        document_embedding_calls=document_embedding_calls,
    )
    _RUNTIMES[runtime_key] = runtime
    return CreativeVectorRuntimeBuild(runtime, [], True, False)


class _RecordingEmbeddingProvider:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self._provider = provider
        self.last_trace: EmbeddingTrace | None = None

    @property
    def call_count(self) -> int:
        return int(getattr(self._provider, "call_count", 0))

    def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        result = self._provider.embed(request)
        self.last_trace = result.trace
        return result


def _runtime_key(pack_id: str, pack_version: str, embedding_model: str, retriever_version: str) -> str:
    return _stable_hash(
        {
            "pack_id": pack_id,
            "pack_version": pack_version,
            "embedding_model": embedding_model,
            "retriever_version": retriever_version,
        }
    )


def _collection_name(pack_id: str, pack_version: str, embedding_model: str, retriever_version: str) -> str:
    return f"cv_{_runtime_key(pack_id, pack_version, embedding_model, retriever_version)}"


def _stable_hash(payload: dict[str, str]) -> str:
    normalized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(normalized.encode("utf-8")).hexdigest()[:12]


def _error(code: str, message: str, field: str | None, related_id: str | None) -> ValidationError:
    return ValidationError(
        code=code,
        message=message,
        object_type="CreativeVectorRuntime",
        object_id=None,
        field=field,
        related_id=related_id,
    )
