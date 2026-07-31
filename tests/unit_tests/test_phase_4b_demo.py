from scripts.run_phase_4b_retrieval_demo import main


def test_phase_4b_demo_help_does_not_run_pipeline(capsys) -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0
    output = capsys.readouterr().out
    assert "--run-eval" in output


def test_phase_4b_demo_default_and_eval_are_offline(capsys) -> None:
    assert main([]) == 0
    default_output = capsys.readouterr().out
    assert "OPENAI_API_KEY" not in default_output
    assert "environment" not in default_output.casefold()
    assert "content_preview" in default_output

    assert main(["--run-eval"]) == 0
    eval_output = capsys.readouterr().out
    assert '"failed": 0' in eval_output


def test_phase_4b_demo_invalid_date_returns_stable_error(capsys) -> None:
    assert main(["--effective-on", "not-a-date"]) == 1
    output = capsys.readouterr().out
    assert "RETRIEVAL_FILTER_INVALID" in output
