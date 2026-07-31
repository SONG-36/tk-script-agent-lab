from tk_script_agent_lab.knowledge.chunking import (
    DeterministicParagraphChunker,
    normalize_knowledge_text,
)
from tk_script_agent_lab.knowledge.ingestion_contracts import (
    ChunkingRequest,
)

from tests.unit_tests.test_phase_4a_ingestion_contracts import document


def test_normalize_knowledge_text_is_deterministic_and_does_not_mutate_document() -> None:
    raw = "  # Title\r\nLine with spaces   \r\n\r\n\r\nNext line\t  \n"
    doc = document(content=raw)

    normalized = normalize_knowledge_text(doc.content)

    assert normalized == "# Title\nLine with spaces\n\nNext line"
    assert doc.content == raw


def test_paragraph_chunker_merges_paragraphs_until_max_chars() -> None:
    doc = document(content="Alpha paragraph.\n\nBeta paragraph.\n\nGamma paragraph.")
    result = DeterministicParagraphChunker().chunk(
        ChunkingRequest(
            document=doc,
            max_chars=40,
            overlap_chars=5,
            chunker_version="deterministic_paragraph_v1",
        )
    )

    assert result.errors == []
    assert [chunk.sequence for chunk in result.chunks] == [1, 2]
    assert result.chunks[0].content == "Alpha paragraph.\n\nBeta paragraph."
    assert result.chunks[0].char_start == 0
    assert result.chunks[0].char_end == len(result.chunks[0].content)


def test_long_paragraph_uses_fixed_windows_with_overlap() -> None:
    doc = document(content="abcdefghijklmnopqrstuvwxyz")
    result = DeterministicParagraphChunker().chunk(
        ChunkingRequest(
            document=doc,
            max_chars=10,
            overlap_chars=3,
            chunker_version="deterministic_paragraph_v1",
        )
    )

    assert result.errors == []
    assert [(chunk.char_start, chunk.char_end) for chunk in result.chunks] == [
        (0, 10),
        (7, 17),
        (14, 24),
        (21, 26),
    ]
    assert [chunk.content for chunk in result.chunks] == [
        "abcdefghij",
        "hijklmnopq",
        "opqrstuvwx",
        "vwxyz",
    ]


def test_chunk_ids_are_stable_and_token_count_stays_none() -> None:
    doc = document(content="Alpha paragraph.\n\nBeta paragraph.")
    request = ChunkingRequest(
        document=doc,
        max_chars=100,
        overlap_chars=10,
        chunker_version="deterministic_paragraph_v1",
    )

    first = DeterministicParagraphChunker().chunk(request)
    second = DeterministicParagraphChunker().chunk(request)

    assert [chunk.chunk_id for chunk in first.chunks] == [
        chunk.chunk_id for chunk in second.chunks
    ]
    assert all(chunk.token_count is None for chunk in first.chunks)
    assert all(chunk.char_count == len(chunk.content) for chunk in first.chunks)
