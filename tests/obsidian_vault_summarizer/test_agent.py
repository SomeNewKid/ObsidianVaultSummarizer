"""Tests for Obsidian vault summarizer agent wiring."""

from obsidian_vault_summarizer.agent import (
    create_obsidian_vault_summarizer_agent,
    create_obsidian_vault_summary_goal_state,
    create_obsidian_vault_tool_registry,
)
from obsidian_vault_summarizer.skill import OBSIDIAN_VAULT_SUMMARIZER_SKILL
from otto_agent.model import ModelClientRegistry
from otto_agent.state import GoalStatus


def test_create_obsidian_vault_summary_goal_state() -> None:
    """Verify the initial goal state targets the local vault."""
    goal_state = create_obsidian_vault_summary_goal_state()

    assert goal_state.goal_id == "obsidian-vault-summary"
    assert goal_state.status == GoalStatus.RUNNING
    assert goal_state.root_entity.entity_type == "obsidian_vault"
    assert goal_state.root_entity.entity_id == "local_vault"


def test_create_obsidian_vault_tool_registry() -> None:
    """Verify the agent receives the available vault tools."""
    tool_registry = create_obsidian_vault_tool_registry()

    assert tool_registry.get("list_vault_files") is not None
    assert tool_registry.get("read_vault_file") is not None


def test_create_obsidian_vault_summarizer_agent_uses_skill() -> None:
    """Verify the agent is configured with the Obsidian summarizer skill."""
    fake_model_client_registry = ModelClientRegistry(clients=())
    agent = create_obsidian_vault_summarizer_agent(fake_model_client_registry)

    assert agent.name == "obsidian_vault_summarizer_agent"
    assert agent.skill == OBSIDIAN_VAULT_SUMMARIZER_SKILL
    assert agent.response_schema_name == "obsidian_vault_summarizer_agent_decision"
