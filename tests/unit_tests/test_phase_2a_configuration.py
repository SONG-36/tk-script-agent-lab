import pytest
from pydantic import ValidationError

from tk_script_agent_lab.configuration import GraphConfiguration


def test_configuration_defaults_to_fake_provider() -> None:
    config = GraphConfiguration()

    assert config.creative_provider == "fake"
    assert config.creative_model is None
    assert config.script_provider == "fake"
    assert config.script_model is None
    assert config.script_prompt_version == "script_draft_v1"


def test_fake_mode_does_not_require_model_name() -> None:
    config = GraphConfiguration(
        creative_provider="fake",
        creative_model=None,
        script_provider="fake",
        script_model=None,
    )

    assert config.creative_provider == "fake"
    assert config.script_provider == "fake"


def test_openai_mode_can_parse_without_api_key_in_configuration() -> None:
    config = GraphConfiguration(
        creative_provider="openai",
        creative_model="creative-model",
        script_provider="openai",
        script_model="script-model",
    )

    assert config.creative_model == "creative-model"
    assert config.script_model == "script-model"
    assert "api" not in GraphConfiguration.model_fields


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GraphConfiguration(creative_provider="unknown")
    with pytest.raises(ValidationError):
        GraphConfiguration(script_provider="unknown")


def test_blank_model_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GraphConfiguration(creative_provider="openai", creative_model=" ")
    with pytest.raises(ValidationError):
        GraphConfiguration(script_provider="openai", script_model=" ")


def test_creative_and_script_providers_are_independent() -> None:
    creative_only = GraphConfiguration(
        creative_provider="openai",
        creative_model="creative-model",
        script_provider="fake",
    )
    script_only = GraphConfiguration(
        creative_provider="fake",
        script_provider="openai",
        script_model="script-model",
    )

    assert creative_only.script_provider == "fake"
    assert creative_only.script_model is None
    assert script_only.creative_provider == "fake"
    assert script_only.creative_model is None
