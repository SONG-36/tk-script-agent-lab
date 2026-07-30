import pytest
from pydantic import ValidationError as PydanticValidationError

from tk_script_agent_lab.domain import ScriptDraft, ScriptScene


def make_scene(scene_id: str, sequence: int) -> ScriptScene:
    return ScriptScene(
        scene_id=scene_id,
        sequence=sequence,
        visual="Show car interior.",
        action="Frame the cleanup context.",
        voiceover=None,
        on_screen_text=None,
        duration_seconds=1.0,
    )


def test_script_scene_duration_must_be_positive() -> None:
    scene = make_scene("scene_1", 1)

    assert scene.duration_seconds == 1.0


def test_script_scene_zero_duration_fails() -> None:
    with pytest.raises(PydanticValidationError):
        ScriptScene(
            scene_id="scene_1",
            sequence=1,
            visual="Show car interior.",
            action="Frame the cleanup context.",
            voiceover=None,
            on_screen_text=None,
            duration_seconds=0,
        )


def test_script_draft_accepts_continuous_scene_sequence() -> None:
    script = ScriptDraft(
        script_id="script_1",
        product_id="prod_1",
        creative_idea_id="idea_1",
        title="Script",
        scenes=[make_scene("scene_1", 1), make_scene("scene_2", 2)],
        caption=None,
        cta=None,
        source_usages=[],
    )

    assert [scene.sequence for scene in script.scenes] == [1, 2]


def test_script_scene_sequence_duplicate_fails() -> None:
    with pytest.raises(PydanticValidationError):
        ScriptDraft(
            script_id="script_1",
            product_id="prod_1",
            creative_idea_id="idea_1",
            title="Script",
            scenes=[make_scene("scene_1", 1), make_scene("scene_2", 1)],
            caption=None,
            cta=None,
            source_usages=[],
        )


def test_script_scene_sequence_gap_fails() -> None:
    with pytest.raises(PydanticValidationError):
        ScriptDraft(
            script_id="script_1",
            product_id="prod_1",
            creative_idea_id="idea_1",
            title="Script",
            scenes=[make_scene("scene_1", 1), make_scene("scene_2", 3)],
            caption=None,
            cta=None,
            source_usages=[],
        )
