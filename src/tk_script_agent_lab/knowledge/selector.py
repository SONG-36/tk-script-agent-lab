from tk_script_agent_lab.knowledge.models import (
    CreativeKnowledgeItem,
    CreativeKnowledgePack,
    KnowledgeExclusion,
    KnowledgeSelectionInputs,
    KnowledgeSelectionRecord,
    stable_selection_id,
)


class KnowledgeSelectionError(ValueError):
    code = "KNOWLEDGE_SELECTION_FAILED"


class StaticCreativeKnowledgeSelector:
    def __init__(self, *, selector_version: str = "static_selector_v1") -> None:
        if not selector_version.strip():
            raise KnowledgeSelectionError("selector_version must not be blank")
        self.selector_version = selector_version

    def empty_record(
        self,
        *,
        target_market: str,
        product_category: str,
        limit: int,
    ) -> KnowledgeSelectionRecord:
        selection_inputs = KnowledgeSelectionInputs(
            target_market=target_market,
            product_category=product_category,
            limit=limit,
        )
        return KnowledgeSelectionRecord(
            selection_id=stable_selection_id(
                mode="off",
                pack_id=None,
                pack_version=None,
                selector_version=self.selector_version,
                selection_inputs=selection_inputs,
                selected_ids=[],
            ),
            stage="creative",
            mode="off",
            pack_id=None,
            pack_version=None,
            selector_version=self.selector_version,
            candidate_ids=[],
            selected_ids=[],
            excluded_items=[],
            selection_inputs=selection_inputs,
        )

    def select(
        self,
        *,
        pack: CreativeKnowledgePack,
        target_market: str,
        product_category: str,
        limit: int,
    ) -> tuple[list[CreativeKnowledgeItem], KnowledgeSelectionRecord]:
        selection_inputs = KnowledgeSelectionInputs(
            target_market=target_market,
            product_category=product_category,
            limit=limit,
        )
        candidate_ids = [item.knowledge_id for item in pack.items]
        eligible: list[CreativeKnowledgeItem] = []
        excluded: list[KnowledgeExclusion] = []
        for item in pack.items:
            reason = _first_exclusion_reason(
                item,
                target_market=target_market,
                product_category=product_category,
            )
            if reason is None:
                eligible.append(item)
            else:
                excluded.append(
                    KnowledgeExclusion(
                        knowledge_id=item.knowledge_id,
                        reason=reason,
                    )
                )
        sorted_items = sorted(eligible, key=lambda item: (-item.priority, item.knowledge_id))
        selected = sorted_items[:limit]
        for item in sorted_items[limit:]:
            excluded.append(
                KnowledgeExclusion(
                    knowledge_id=item.knowledge_id,
                    reason="over_limit",
                )
            )
        selected_ids = [item.knowledge_id for item in selected]
        record = KnowledgeSelectionRecord(
            selection_id=stable_selection_id(
                mode="static",
                pack_id=pack.pack_id,
                pack_version=pack.version,
                selector_version=self.selector_version,
                selection_inputs=selection_inputs,
                selected_ids=selected_ids,
            ),
            stage="creative",
            mode="static",
            pack_id=pack.pack_id,
            pack_version=pack.version,
            selector_version=self.selector_version,
            candidate_ids=candidate_ids,
            selected_ids=selected_ids,
            excluded_items=excluded,
            selection_inputs=selection_inputs,
        )
        return selected, record


def _first_exclusion_reason(
    item: CreativeKnowledgeItem,
    *,
    target_market: str,
    product_category: str,
) -> str | None:
    if item.status == "disabled":
        return "disabled"
    if item.status == "draft":
        return "draft"
    if "creative" not in item.applicability.task_stages:
        return "stage_mismatch"
    if not _matches(item.applicability.target_markets, target_market):
        return "market_mismatch"
    if not _matches(item.applicability.product_categories, product_category):
        return "category_mismatch"
    return None


def _matches(patterns: list[str], value: str) -> bool:
    normalized = value.strip().casefold()
    return any(pattern == "*" or pattern.strip().casefold() == normalized for pattern in patterns)
