from argparse import ArgumentParser
from pathlib import Path, PurePosixPath
import json

from tk_script_agent_lab.knowledge.chunking import DEFAULT_CHUNKER_VERSION
from tk_script_agent_lab.knowledge.ingestion_contracts import (
    IngestionRequest,
    KnowledgeDocument,
)
from tk_script_agent_lab.knowledge.ingestor import (
    DEFAULT_INGESTOR_VERSION,
    DeterministicKnowledgeIngestor,
)

FIXTURE_DIR = Path("data/golden_cases/rag_ingestion_v1")
PREVIEW_CHARS = 96


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = _load_fixture(FIXTURE_DIR)
    ingestion_defaults = payload["ingestion"]
    document = KnowledgeDocument.model_validate(
        {
            **payload["document"],
            "content": _load_content_file(FIXTURE_DIR, payload["content_file"]),
        }
    )
    request = IngestionRequest(
        documents=[document],
        max_chars=args.max_chars or ingestion_defaults["max_chars"],
        overlap_chars=args.overlap_chars
        if args.overlap_chars is not None
        else ingestion_defaults["overlap_chars"],
        chunker_version=ingestion_defaults.get("chunker_version", DEFAULT_CHUNKER_VERSION),
        ingestor_version=ingestion_defaults.get("ingestor_version", DEFAULT_INGESTOR_VERSION),
    )
    result = DeterministicKnowledgeIngestor().ingest(request)
    print(json.dumps(_summarize(result), ensure_ascii=False, indent=2))
    return 0 if not result.errors else 1


def _parser() -> ArgumentParser:
    parser = ArgumentParser(
        description="Run the Phase 4A deterministic local ingestion demo."
    )
    parser.add_argument("--max-chars", type=int, help="Maximum characters per chunk.")
    parser.add_argument(
        "--overlap-chars",
        type=int,
        help="Overlap for fixed-window chunks when a paragraph exceeds max chars.",
    )
    return parser


def _load_fixture(fixture_dir: Path) -> dict:
    return json.loads((fixture_dir / "ingestion_input.json").read_text(encoding="utf-8"))


def _load_content_file(fixture_dir: Path, content_file: str) -> str:
    path = PurePosixPath(content_file)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Fixture content_file must be a local fixture filename")
    return (fixture_dir / path).read_text(encoding="utf-8")


def _summarize(result) -> dict:
    return {
        "request_id": result.trace.request_id,
        "document_ids": result.trace.input_document_ids,
        "accepted_document_ids": result.trace.accepted_document_ids,
        "rejected_document_ids": result.trace.rejected_document_ids,
        "chunk_count": result.trace.chunk_count,
        "chunks": [
            {
                "chunk_id": chunk.chunk_id,
                "sequence": chunk.sequence,
                "char_start": chunk.char_start,
                "char_end": chunk.char_end,
                "char_count": chunk.char_count,
                "content_preview": _preview(chunk.content),
                "provenance": chunk.provenance_type,
                "evidence_status": chunk.evidence_status,
            }
            for chunk in result.chunks
        ],
        "errors": [error.model_dump(mode="json") for error in result.errors],
    }


def _preview(content: str) -> str:
    if len(content) <= PREVIEW_CHARS:
        return content
    return f"{content[:PREVIEW_CHARS].rstrip()}..."


if __name__ == "__main__":
    raise SystemExit(main())
