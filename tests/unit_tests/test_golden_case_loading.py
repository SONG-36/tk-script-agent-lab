from tk_script_agent_lab.domain import DomainDataset, validate_domain_dataset

from conftest import load_golden_case_dataset


def test_golden_case_loads_and_validates() -> None:
    dataset = load_golden_case_dataset()

    assert validate_domain_dataset(dataset) == []


def test_golden_case_models_dump_and_reload() -> None:
    dataset = load_golden_case_dataset()
    dumped = dataset.model_dump(mode="json")
    reloaded = DomainDataset.model_validate(dumped)

    assert validate_domain_dataset(reloaded) == []


def test_validator_does_not_modify_dataset() -> None:
    dataset = load_golden_case_dataset()
    before = dataset.model_dump(mode="json")

    validate_domain_dataset(dataset)

    assert dataset.model_dump(mode="json") == before
