from otto_agent.agent import ActionDecision, FinalDecision, StateUpdate
from otto_agent.harness.rules import (
    CompletionTypeRule,
    RegisteredToolRule,
    StateUpdateShapeRule,
    ToolNameRule,
)
from otto_agent.state import EntityRef, GoalState, GoalStatus, ToolResult
from otto_agent.tool import ToolArgument, ToolRegistry, ToolRequest, ToolRuntime


class _FakeTool:
    name = "fake_tool"
    description = "Fake tool used by harness rule tests."
    arguments = (
        ToolArgument(
            name="value",
            argument_type="string",
            description="A fake tool value.",
        ),
    )

    def execute(
        self,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            arguments=tool_request,
            data={},
        )


def test_completion_type_rule_rejects_missing_completion_type() -> None:
    decision = FinalDecision(
        completion_type="",
        details={},
        reason="The goal is complete.",
    )

    errors = CompletionTypeRule().validate(decision, _goal_state())

    assert len(errors) == 1
    assert errors[0].code == "missing_completion_type"


def test_tool_name_rule_rejects_missing_tool_name() -> None:
    decision = ActionDecision(
        tool_name="",
        arguments={},
        reason="Need to use a tool.",
    )

    errors = ToolNameRule().validate(decision, _goal_state())

    assert len(errors) == 1
    assert errors[0].code == "missing_tool_name"


def test_registered_tool_rule_rejects_unknown_tool_name() -> None:
    decision = ActionDecision(
        tool_name="missing_tool",
        arguments={},
        reason="Need to use a tool.",
    )

    errors = RegisteredToolRule(ToolRegistry(tools=(_FakeTool(),))).validate(
        decision,
        _goal_state(),
    )

    assert len(errors) == 1
    assert errors[0].code == "unknown_tool"


def test_state_update_shape_rule_accepts_valid_add_output() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={},
        reason="The goal is complete.",
        state_updates=[
            StateUpdate(
                operation="add_output",
                arguments={
                    "output_type": "draft_note",
                    "data": {"text": "noted"},
                },
            )
        ],
    )

    errors = StateUpdateShapeRule().validate(decision, _goal_state())

    assert errors == []


def test_state_update_shape_rule_rejects_unknown_operation() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={},
        reason="The goal is complete.",
        state_updates=[
            StateUpdate(
                operation="replace_claims",
                arguments={},
            )
        ],
    )

    errors = StateUpdateShapeRule().validate(decision, _goal_state())

    assert len(errors) == 1
    assert errors[0].code == "unknown_state_update_operation"


def test_state_update_shape_rule_rejects_missing_data() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={},
        reason="The goal is complete.",
        state_updates=[
            StateUpdate(
                operation="add_claim",
                arguments={"claim_type": "reported_condition"},
            )
        ],
    )

    errors = StateUpdateShapeRule().validate(decision, _goal_state())

    assert len(errors) == 1
    assert errors[0].code == "missing_data"


def _goal_state() -> GoalState:
    root_entity = EntityRef(entity_type="task", entity_id="T001")
    return GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=root_entity,
    )
