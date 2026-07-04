"""Tests for Obsidian vault tools."""

import pytest

from obsidian_vault_summarizer.tools import list_vault_files, read_vault_file


def test_list_vault_files_returns_vault_file_names() -> None:
    """Verify the vault listing tool returns the available file names."""
    assert list_vault_files() == ["Agent.md", "Index.md", "Secret.md", "Tool.md"]


def test_read_vault_file_returns_named_file_content() -> None:
    """Verify the vault reader returns content for a named vault file."""
    content = read_vault_file("Agent.md")

    assert "Agent" in content


def test_read_vault_file_rejects_directory_traversal() -> None:
    """Verify the vault reader does not allow paths outside the vault."""
    with pytest.raises(ValueError, match="directly in the vault"):
        read_vault_file("../README.md")
