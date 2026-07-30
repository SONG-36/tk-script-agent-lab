from pydantic import BaseModel, ConfigDict

from tk_script_agent_lab.domain import CreativeIdea, ReferenceInsight, ScriptDraft


class FakeProviderFixtures(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_insights: list[ReferenceInsight]
    creative_ideas: list[CreativeIdea]
    script_drafts: list[ScriptDraft]
