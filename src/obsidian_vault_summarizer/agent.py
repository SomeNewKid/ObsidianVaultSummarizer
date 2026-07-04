"""Obsidian vault summarizer agent."""

from typing import cast

from otto_agent.guardrail import GuardrailSet
from otto_agent.harness.runner import AgentHarness, RunResult
from otto_agent.model import ModelClientRegistry
from otto_agent.openai_helper import create_openai_model_client_registry
from otto_agent.skilled_agent import SkilledAgent
from otto_agent.state import EntityRef, GoalState, GoalStatus
from otto_agent.tool import Tool, ToolRegistry

from .skill import OBSIDIAN_VAULT_SUMMARIZER_SKILL
from .tools import LIST_VAULT_FILES_TOOL, READ_VAULT_FILE_TOOL, SecretFileGuardrail

MAX_MODEL_CALLS = 10
MODEL_NAME = "gpt-4.1-mini"


def create_obsidian_vault_summary_goal_state() -> GoalState:
    """Create the initial goal state for one Obsidian vault summary."""
    return GoalState(
        goal_id="obsidian-vault-summary",
        status=GoalStatus.RUNNING,
        root_entity=EntityRef(
            entity_type="obsidian_vault",
            entity_id="local_vault",
        ),
    )


def create_obsidian_vault_summarizer_agent(
    model_client_registry: ModelClientRegistry,
) -> SkilledAgent:
    """Create the Obsidian vault summarizer agent."""
    return SkilledAgent(
        name="obsidian_vault_summarizer_agent",
        skill=OBSIDIAN_VAULT_SUMMARIZER_SKILL,
        model_client_registry=model_client_registry,
        response_schema_name="obsidian_vault_summarizer_agent_decision",
    )


def create_obsidian_vault_tool_registry() -> ToolRegistry:
    """Create the tools available to the Obsidian vault summarizer agent."""
    return ToolRegistry(
        tools=cast(
            tuple[Tool, ...],
            (
                LIST_VAULT_FILES_TOOL,
                READ_VAULT_FILE_TOOL,
            ),
        ),
    )


def run_obsidian_vault_summarizer(max_agent_turns: int = 8) -> RunResult:
    """Run the Obsidian vault summarizer agent."""
    model_client_registry = create_openai_model_client_registry(
        max_model_calls=MAX_MODEL_CALLS, model_name=MODEL_NAME
    )
    tool_registry = create_obsidian_vault_tool_registry()
    goal_state = create_obsidian_vault_summary_goal_state()
    agent = create_obsidian_vault_summarizer_agent(model_client_registry)
    guardrail_set = GuardrailSet(before_tool_call=(SecretFileGuardrail(),))

    return AgentHarness().run_agent_goal(
        agent=agent,
        goal_state=goal_state,
        tool_registry=tool_registry,
        max_agent_turns=max_agent_turns,
        guardrails=guardrail_set,
    )
