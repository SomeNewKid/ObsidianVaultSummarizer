"""Smoke tests for the project package."""

import pytest

from obsidian_vault_summarizer import cli
from otto_agent.harness.runner import RunResult, RunStatus


def test_cli_runs_obsidian_vault_summarizer(monkeypatch, capsys) -> None:
    """Verify the CLI runs and prints the summarizer result."""
    result = RunResult(
        run_id="obsidian-vault-summary",
        status=RunStatus.COMPLETED,
        completion_type="done",
        details={
            "summary": "A tiny test summary.",
            "reason_code": "summary_created",
        },
        trace_events=(),
    )
    monkeypatch.setattr(cli, "run_obsidian_vault_summarizer", lambda: result)

    assert cli.main([]) == 0

    output = capsys.readouterr().out
    assert "A tiny test summary." in output


def test_cli_rejects_arguments() -> None:
    """Verify the CLI documents that it does not accept arguments."""
    with pytest.raises(SystemExit, match="Usage: python -m obsidian_vault_summarizer"):
        cli.main(["unexpected"])
