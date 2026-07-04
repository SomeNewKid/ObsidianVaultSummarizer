from typing import cast

import pytest

from otto_agent.agent import ActionDecision, FinalDecision, StateUpdate
from otto_agent.agents.model_decision import (
    agent_decision_from_model_data,
    create_model_decision_schema,
    model_decision_from_data,
)
from otto_agent.agents.skill import AgentSkill, FinalDetailField
from otto_agent.state import ToolResult
from otto_agent.tool import ToolArgument, ToolRegistry, ToolRequest, ToolRuntime


class _FakeTool:
    name = "inspect_record"
    description = "Inspect a record by identifier."
    arguments = (
        ToolArgument(
            name="record_id",
            argument_type="string",
            description="Identifier of the record.",
        ),
    )

    def execute(
        self,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        raise NotImplementedError


def test_model_decision_schema_includes_available_tool() -> None:
    schema = create_model_decision_schema(_tool_registry(), _skill())
    action_schema = _schema_properties(schema)["action_decision"]

    assert "inspect_record" in str(action_schema)
    assert "record_id" in str(action_schema)


def test_model_decision_schema_includes_state_updates() -> None:
    schema = create_model_decision_schema(_tool_registry(), _skill())
    state_updates_schema = _schema_properties(schema)["state_updates"]

    assert "add_claim" in str(state_updates_schema)
    assert "add_fact" in str(state_updates_schema)
    assert "add_output" in str(state_updates_schema)
    assert "'additionalProperties': True" not in str(state_updates_schema)


def test_model_decision_schema_includes_final_detail_fields() -> None:
    schema = create_model_decision_schema(_tool_registry(), _skill())
    final_schema = _schema_properties(schema)["final_decision"]

    assert "result_code" in str(final_schema)
    assert "success" in str(final_schema)
    assert "failed" in str(final_schema)


def test_model_data_converts_to_action_decision() -> None:
    decision = agent_decision_from_model_data(
        {
            "reason": "Need to inspect the record.",
            "state_updates": [
                {
                    "operation": "add_claim",
                    "arguments": {
                        "claim_type": "reported_condition",
                        "data": {"source": "request"},
                    },
                }
            ],
            "action_decision": {
                "tool_name": "inspect_record",
                "arguments": {"record_id": "R001"},
            },
            "final_decision": None,
        }
    )

    assert decision == ActionDecision(
        reason="Need to inspect the record.",
        state_updates=[
            StateUpdate(
                operation="add_claim",
                arguments={
                    "claim_type": "reported_condition",
                    "data": {"source": "request"},
                },
            )
        ],
        tool_name="inspect_record",
        arguments={"record_id": "R001"},
    )


def test_model_data_converts_to_final_decision() -> None:
    decision = agent_decision_from_model_data(
        {
            "reason": "The goal is complete.",
            "state_updates": [],
            "action_decision": None,
            "final_decision": {
                "completion_type": "done",
                "details": {"result_code": "success"},
            },
        }
    )

    assert decision == FinalDecision(
        reason="The goal is complete.",
        state_updates=[],
        completion_type="done",
        details={"result_code": "success"},
    )


def test_model_data_rejects_both_decision_branches() -> None:
    with pytest.raises(
        ValueError,
        match="Model decision cannot include both decision branches.",
    ):
        model_decision_from_data(
            {
                "reason": "Malformed decision.",
                "state_updates": [],
                "action_decision": {
                    "tool_name": "inspect_record",
                    "arguments": {"record_id": "R001"},
                },
                "final_decision": {
                    "completion_type": "done",
                    "details": {"result_code": "success"},
                },
            }
        )


def test_model_data_rejects_missing_decision_branch() -> None:
    with pytest.raises(
        ValueError,
        match="Model decision must include one decision branch.",
    ):
        model_decision_from_data(
            {
                "reason": "Malformed decision.",
                "state_updates": [],
                "action_decision": None,
                "final_decision": None,
            }
        )


def test_model_data_rejects_missing_reason() -> None:
    with pytest.raises(ValueError, match="Model decision reason is required."):
        model_decision_from_data(
            {
                "reason": "",
                "state_updates": [],
                "action_decision": None,
                "final_decision": {
                    "completion_type": "done",
                    "details": {"result_code": "success"},
                },
            }
        )


def _skill() -> AgentSkill:
    return AgentSkill(
        name="fake_skill",
        goal="Complete a generic goal.",
        final_detail_fields={
            "result_code": FinalDetailField(
                description="The structured result code.",
                allowed_values={
                    "success": "The goal succeeded.",
                    "failed": "The goal failed.",
                },
            )
        },
    )


def _tool_registry() -> ToolRegistry:
    return ToolRegistry(tools=(_FakeTool(),))


def _schema_properties(schema: dict[str, object]) -> dict[str, object]:
    return cast(dict[str, object], schema["properties"])
