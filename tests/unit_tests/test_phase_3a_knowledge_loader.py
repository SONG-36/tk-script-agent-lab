import pytest

from tk_script_agent_lab.knowledge.loader import (
    KnowledgePackError,
    KnowledgePackNotFound,
    load_creative_knowledge_pack,
)


def test_loads_registered_creative_knowledge_pack() -> None:
    pack = load_creative_knowledge_pack("tiktok_car_cleaning_v1")

    assert pack.pack_id == "tiktok_car_cleaning_v1"
    assert len(pack.items) == 6
    assert all(item.provenance_type == "internal_working_rule" for item in pack.items)


@pytest.mark.parametrize(
    "pack_id",
    [
        "../knowledge/creative/tiktok_car_cleaning_v1.yaml",
        "/tmp/tiktok_car_cleaning_v1.yaml",
        "https://example.com/tiktok_car_cleaning_v1.yaml",
        "knowledge/creative/tiktok_car_cleaning_v1.yaml",
        "missing_pack",
    ],
)
def test_loader_rejects_paths_urls_and_unknown_pack_ids(pack_id: str) -> None:
    with pytest.raises(KnowledgePackNotFound):
        load_creative_knowledge_pack(pack_id)


def test_loader_errors_have_stable_codes() -> None:
    assert KnowledgePackNotFound.code == "KNOWLEDGE_PACK_NOT_FOUND"
    assert KnowledgePackError.code == "KNOWLEDGE_PACK_INVALID"
