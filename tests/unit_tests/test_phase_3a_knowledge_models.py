import pytest
from pydantic import ValidationError

from tk_script_agent_lab.knowledge import (
    CreativeKnowledgeItem,
    CreativeKnowledgePack,
    KnowledgeApplicability,
)


def item(knowledge_id: str = "ck_test") -> CreativeKnowledgeItem:
    return CreativeKnowledgeItem(
        knowledge_id=knowledge_id,
        title="Visible mess hook",
        kind="hook_pattern",
        instruction="Start with a visible car mess.",
        rationale=None,
        positive_examples=["Crumbs in a cup holder."],
        anti_examples=["Unverified suction claim."],
        priority=50,
        status="active",
        applicability=KnowledgeApplicability(
            task_stages=["creative"],
            target_markets=["*"],
            product_categories=["*"],
        ),
        provenance_type="internal_working_rule",
        evidence_status="hypothesis",
        source_reference=None,
    )


def test_creative_knowledge_pack_accepts_valid_items() -> None:
    pack = CreativeKnowledgePack(
        pack_id="pack_test",
        version="1.0",
        title="Test Pack",
        description="Test creative guidance.",
        items=[item()],
    )

    assert pack.items[0].knowledge_id == "ck_test"


def test_creative_knowledge_pack_rejects_duplicate_ids() -> None:
    with pytest.raises(ValidationError):
        CreativeKnowledgePack(
            pack_id="pack_test",
            version="1.0",
            title="Test Pack",
            description="Test creative guidance.",
            items=[item("ck_dup"), item("ck_dup")],
        )


def test_official_policy_requires_source_reference() -> None:
    with pytest.raises(ValidationError):
        CreativeKnowledgeItem.model_validate(
            {
                **item().model_dump(mode="json"),
                "provenance_type": "official_policy",
                "source_reference": None,
            }
        )


def test_internal_working_rule_cannot_be_verified() -> None:
    with pytest.raises(ValidationError):
        CreativeKnowledgeItem.model_validate(
            {
                **item().model_dump(mode="json"),
                "evidence_status": "verified",
            }
        )
