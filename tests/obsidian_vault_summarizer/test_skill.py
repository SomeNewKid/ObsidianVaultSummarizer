"""Tests for the Obsidian vault summarizer skill."""

from obsidian_vault_summarizer.skill import OBSIDIAN_VAULT_SUMMARIZER_SKILL


def test_obsidian_vault_summarizer_skill_defines_final_result_fields() -> None:
    """Verify the skill exposes the fields required by final decisions."""
    final_fields = OBSIDIAN_VAULT_SUMMARIZER_SKILL.final_detail_fields

    assert set(final_fields) == {
        "summary",
        "main_topics",
        "note_relationships",
        "files_read",
        "reason_code",
    }


def test_obsidian_vault_summarizer_skill_allows_expected_reason_codes() -> None:
    """Verify the skill supports the expected completion reasons."""
    reason_code = OBSIDIAN_VAULT_SUMMARIZER_SKILL.final_detail_fields["reason_code"]

    assert reason_code.allowed_values == {
        "summary_created": "A vault knowledge summary was created.",
        "missing_vault_files": "No vault files could be discovered.",
        "missing_note_content": (
            "The agent could not read enough note content to summarize the vault."
        ),
    }
