import json

from tk_script_agent_lab.domain import ValidationError
from tk_script_agent_lab.knowledge.contracts import (
    RetrievedKnowledge,
    RetrievalExclusion,
    RetrievalRequest,
    RetrievalResult,
    RetrievalTrace,
    stable_retrieval_request_id,
)
from tk_script_agent_lab.knowledge.loader import KnowledgePackError, load_creative_knowledge_pack
from tk_script_agent_lab.knowledge.models import CreativeKnowledgeItem
from tk_script_agent_lab.knowledge.selector import (
    KnowledgeSelectionError,
    StaticCreativeKnowledgeSelector,
)


class StaticKnowledgeRetriever:
    def __init__(
        self,
        *,
        pack_id: str,
        retriever_version: str = "static_selector_v1",
    ) -> None:
        if not pack_id.strip():
            raise KnowledgeSelectionError("pack_id must not be blank")
        self.pack_id = pack_id
        self.retriever_version = retriever_version

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        try:
            if request.stage != "creative":
                raise KnowledgeSelectionError("static knowledge retriever only supports creative stage")
            pack = load_creative_knowledge_pack(self.pack_id)
            selected_items, record = StaticCreativeKnowledgeSelector(
                selector_version=self.retriever_version,
            ).select(
                pack=pack,
                target_market=request.target_market,
                product_category=request.product_category,
                limit=request.limit,
            )
            return RetrievalResult(
                items=[_retrieved_knowledge(item) for item in selected_items],
                trace=RetrievalTrace(
                    retriever_type="static",
                    retriever_version=self.retriever_version,
                    request_id=record.selection_id,
                    candidate_ids=record.candidate_ids,
                    selected_ids=record.selected_ids,
                    excluded=[
                        RetrievalExclusion(
                            knowledge_id=item.knowledge_id,
                            reason=item.reason,
                        )
                        for item in record.excluded_items
                    ],
                    filters_applied={
                        **request.filters,
                        "pack_id": pack.pack_id,
                        "pack_version": pack.version,
                        "target_market": request.target_market,
                        "product_category": request.product_category,
                    },
                ),
                errors=[],
            )
        except (KnowledgePackError, KnowledgeSelectionError) as exc:
            return RetrievalResult(
                items=[],
                trace=_empty_trace(
                    request,
                    retriever_version=self.retriever_version,
                    pack_id=self.pack_id,
                ),
                errors=[
                    ValidationError(
                        code=exc.code,
                        message=str(exc),
                        object_type="StaticKnowledgeRetriever",
                        object_id=self.pack_id,
                        field="pack_id",
                        related_id=None,
                    )
                ],
            )


def _retrieved_knowledge(item: CreativeKnowledgeItem) -> RetrievedKnowledge:
    metadata = {
        "rationale": item.rationale or "",
        "positive_examples": json.dumps(item.positive_examples, ensure_ascii=False),
        "anti_examples": json.dumps(item.anti_examples, ensure_ascii=False),
        "priority": str(item.priority),
        "status": item.status,
    }
    return RetrievedKnowledge(
        knowledge_id=item.knowledge_id,
        title=item.title,
        content=item.instruction,
        kind=item.kind,
        provenance_type=item.provenance_type,
        evidence_status=item.evidence_status,
        source_reference=item.source_reference,
        metadata={key: value for key, value in metadata.items() if value},
        score=None,
    )


def _empty_trace(
    request: RetrievalRequest,
    *,
    retriever_version: str,
    pack_id: str | None = None,
) -> RetrievalTrace:
    filters = {
        **request.filters,
        "target_market": request.target_market,
        "product_category": request.product_category,
    }
    if pack_id:
        filters["pack_id"] = pack_id
    return RetrievalTrace(
        retriever_type="static",
        retriever_version=retriever_version,
        request_id=stable_retrieval_request_id(request),
        candidate_ids=[],
        selected_ids=[],
        excluded=[],
        filters_applied=filters,
    )
