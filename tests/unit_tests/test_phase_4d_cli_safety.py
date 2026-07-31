import os

from scripts import run_phase_4d_creative_rag_demo as demo


def test_phase_4d_help_does_not_read_environment(monkeypatch, capsys) -> None:
    getenv_calls = []

    def record_getenv(name, default=None):
        getenv_calls.append(name)
        return default

    monkeypatch.setattr(os.environ, "get", record_getenv)
    try:
        demo.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    assert "--knowledge-mode" in capsys.readouterr().out
    assert "OPENAI_API_KEY" not in getenv_calls
    assert "OPENAI_MODEL" not in getenv_calls
    assert "OPENAI_EMBEDDING_MODEL" not in getenv_calls


def test_phase_4d_vector_or_openai_requires_confirm_before_environment(monkeypatch, capsys) -> None:
    getenv_calls = []

    def record_getenv(name, default=None):
        getenv_calls.append(name)
        return default

    monkeypatch.setattr(os.environ, "get", record_getenv)

    assert demo.main(["--knowledge-mode", "vector", "--knowledge-pack", "tiktok_car_cleaning_v1"]) == 2
    assert demo.main(["--creative-provider", "openai"]) == 2
    assert "OPENAI_API_KEY" not in getenv_calls
    assert "OPENAI_MODEL" not in getenv_calls
    assert "OPENAI_EMBEDDING_MODEL" not in getenv_calls
    assert "--confirm-live" in capsys.readouterr().err


def test_phase_4d_off_fake_runs_without_live(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    assert demo.main(["--knowledge-mode", "off", "--creative-provider", "fake"]) == 0
    output = capsys.readouterr().out

    assert "IDEA_SELECTION_REQUIRED" in output
    assert "OPENAI_API_KEY" not in output


def test_phase_4d_static_fake_runs_without_live(monkeypatch, capsys) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_EMBEDDING_MODEL", raising=False)

    assert demo.main(
        [
            "--knowledge-mode",
            "static",
            "--creative-provider",
            "fake",
            "--knowledge-pack",
            "tiktok_car_cleaning_v1",
        ]
    ) == 0
    output = capsys.readouterr().out

    assert '"knowledge_mode": "static"' in output
    assert "IDEA_SELECTION_REQUIRED" in output
    assert "OPENAI_API_KEY" not in output
