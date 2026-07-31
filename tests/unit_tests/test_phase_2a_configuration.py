import pytest
from pydantic import ValidationError

from tk_script_agent_lab.configuration import GraphConfiguration


def test_configuration_defaults_to_fake_provider() -> None:
    config = GraphConfiguration()

    assert config.creative_provider == "fake"
    assert config.creative_model is None


def test_fake_mode_does_not_require_model_name() -> None:
    config = GraphConfiguration(creative_provider="fake", creative_model=None)

    assert config.creative_provider == "fake"


def test_openai_mode_can_parse_without_api_key_in_configuration() -> None:
    config = GraphConfiguration(creative_provider="openai", creative_model="test-model")

    assert config.creative_model == "test-model"
    assert "api" not in GraphConfiguration.model_fields


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GraphConfiguration(creative_provider="unknown")


def test_blank_model_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        GraphConfiguration(creative_provider="openai", creative_model=" ")
