from otto_agent.agent import (
    ActionDecision,
    AgentDecision,
    AgentRequest,
    FinalDecision,
    StateUpdate,
)
from otto_agent.harness.runner import AgentHarness, RunStatus
from otto_agent.reducer import StateReducer
from otto_agent.state import Claim, EntityRef, GoalState, GoalStatus, ToolResult
from otto_agent.tool import ToolArgument, ToolRegistry, ToolRequest, ToolRuntime
from otto_agent.validation import ValidationError, ValidationRule


class _ToolUsingAgent:
    name = "tool_using_agent"

    def decide(self, request: AgentRequest) -> AgentDecision:
        if request.goal_state.tool_results:
            return FinalDecision(
                completion_type="done",
                details={"tool_result_count": len(request.goal_state.tool_results)},
                reason="The tool result is available.",
            )

        return ActionDecision(
            tool_name="fake_tool",
            arguments={"value": "example"},
            reason="Need to call the fake tool.",
        )

    def get_validation_rules(self) -> list[ValidationRule]:
        return []

    def get_state_reducers(self) -> list[StateReducer]:
        return []


class _AlwaysActingAgent:
    name = "always_acting_agent"

    def decide(self, request: AgentRequest) -> AgentDecision:
        return ActionDecision(
            tool_name="fake_tool",
            arguments={"turn": len(request.goal_state.tool_results) + 1},
            reason="Keep calling the fake tool.",
        )

    def get_validation_rules(self) -> list[ValidationRule]:
        return []

    def get_state_reducers(self) -> list[StateReducer]:
        return []


class _InvalidAgent:
    name = "invalid_agent"

    def decide(self, request: AgentRequest) -> AgentDecision:
        return ActionDecision(
            tool_name="fake_tool",
            arguments={"value": "example"},
            reason="This decision should fail validation.",
        )

    def get_validation_rules(self) -> list[ValidationRule]:
        return [_RejectEverythingRule()]

    def get_state_reducers(self) -> list[StateReducer]:
        return []


class _ClaimingToolUsingAgent:
    name = "claiming_tool_using_agent"

    def decide(self, request: AgentRequest) -> AgentDecision:
        if request.goal_state.tool_results:
            return FinalDecision(
                completion_type="done",
                details={
                    "claim_count": len(request.goal_state.claims),
                    "fact_count": len(request.goal_state.facts),
                    "output_count": len(request.goal_state.outputs),
                },
                reason="The claim and tool result are available.",
            )

        return ActionDecision(
            tool_name="claim_aware_tool",
            arguments={"value": "example"},
            reason="Record state before calling the tool.",
            state_updates=[
                StateUpdate(
                    operation="add_claim",
                    arguments={
                        "claim_type": "reported_condition",
                        "data": {"source": "request"},
                    },
                ),
                StateUpdate(
                    operation="add_fact",
                    arguments={
                        "fact_type": "known_condition",
                        "data": {"verified": True},
                    },
                ),
                StateUpdate(
                    operation="add_output",
                    arguments={
                        "output_type": "draft_note",
                        "data": {"text": "noted"},
                    },
                ),
            ],
        )

    def get_validation_rules(self) -> list[ValidationRule]:
        return []

    def get_state_reducers(self) -> list[StateReducer]:
        return []


class _ReducerUsingAgent:
    name = "reducer_using_agent"

    def decide(self, request: AgentRequest) -> AgentDecision:
        if request.goal_state.facts:
            return FinalDecision(
                completion_type="done",
                details={"fact_count": len(request.goal_state.facts)},
                reason="The reducer fact is available.",
            )

        return ActionDecision(
            tool_name="fake_tool",
            arguments={"value": "example"},
            reason="Need a tool result for the reducer.",
        )

    def get_validation_rules(self) -> list[ValidationRule]:
        return []

    def get_state_reducers(self) -> list[StateReducer]:
        return [_ToolResultFactReducer()]


class _ToolResultFactReducer:
    def apply(
        self,
        goal_state: GoalState,
        tool_result: ToolResult,
    ) -> None:
        goal_state.add_fact(
            "tool_result_seen",
            {"tool_name": tool_result.tool_name},
        )


class _RejectEverythingRule:
    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        return [
            ValidationError(
                code="rejected_for_test",
                message="The test rule rejects all decisions.",
            )
        ]


class _FakeTool:
    name = "fake_tool"
    description = "Fake tool used by harness runner tests."
    arguments = (
        ToolArgument(
            name="value",
            argument_type="string",
            description="A fake tool value.",
        ),
    )

    def __init__(self) -> None:
        self.execution_count = 0

    def execute(
        self,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        self.execution_count += 1
        return ToolResult(
            tool_name=self.name,
            arguments=tool_request,
            data={
                "value": "tool response",
                "runtime_value_count": len(tool_runtime.values),
            },
        )


class _ClaimAwareTool:
    name = "claim_aware_tool"
    description = "Fake tool that observes goal state during execution."
    arguments = (
        ToolArgument(
            name="value",
            argument_type="string",
            description="A fake tool value.",
        ),
    )

    def __init__(self, goal_state: GoalState) -> None:
        self._goal_state = goal_state

    def execute(
        self,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        return ToolResult(
            tool_name=self.name,
            arguments=tool_request,
            data={
                "claim_count_at_execution": len(self._goal_state.claims),
                "fact_count_at_execution": len(self._goal_state.facts),
                "output_count_at_execution": len(self._goal_state.outputs),
            },
        )


def test_agent_loop_continues_after_action_decision() -> None:
    goal_state = _goal_state()
    tool = _FakeTool()

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=(tool,)),
        max_agent_turns=2,
    )

    assert result.status == RunStatus.COMPLETED
    assert result.completion_type == "done"
    assert result.details == {"tool_result_count": 1}
    assert tool.execution_count == 1
    assert goal_state.status == GoalStatus.COMPLETED
    assert goal_state.tool_results == [
        ToolResult(
            tool_name="fake_tool",
            arguments={"value": "example"},
            data={"value": "tool response", "runtime_value_count": 0},
        )
    ]


def test_validation_failure_stops_before_tool_execution() -> None:
    goal_state = _goal_state()
    tool = _FakeTool()

    result = AgentHarness().run_agent_goal(
        agent=_InvalidAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=(tool,)),
        max_agent_turns=2,
    )

    assert result.status == RunStatus.FAILED
    assert goal_state.status == GoalStatus.FAILED
    assert goal_state.tool_results == []
    assert tool.execution_count == 0
    assert any(
        "Validation failed: rejected_for_test" in event.message
        for event in result.trace_events
    )


def test_agent_loop_fails_when_max_turns_is_reached() -> None:
    goal_state = _goal_state()
    tool = _FakeTool()

    result = AgentHarness().run_agent_goal(
        agent=_AlwaysActingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=(tool,)),
        max_agent_turns=2,
    )

    assert result.status == RunStatus.FAILED
    assert result.completion_type is None
    assert result.details == {
        "agent": "always_acting_agent",
        "reason_code": "goal_not_completed",
    }
    assert goal_state.status == GoalStatus.FAILED
    assert tool.execution_count == 2
    assert len(goal_state.tool_results) == 2
    assert result.trace_events[-1].message == "Stopped after reaching 2 turn."


def test_agent_loop_applies_state_updates_before_action_decision() -> None:
    goal_state = _goal_state()

    result = AgentHarness().run_agent_goal(
        agent=_ClaimingToolUsingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=(_ClaimAwareTool(goal_state),)),
        max_agent_turns=2,
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details == {
        "claim_count": 1,
        "fact_count": 1,
        "output_count": 1,
    }
    assert goal_state.claims == [
        Claim(claim_type="reported_condition", data={"source": "request"})
    ]
    assert goal_state.tool_results == [
        ToolResult(
            tool_name="claim_aware_tool",
            arguments={"value": "example"},
            data={
                "claim_count_at_execution": 1,
                "fact_count_at_execution": 1,
                "output_count_at_execution": 1,
            },
        )
    ]


def test_agent_loop_applies_reducers_after_action_decision() -> None:
    goal_state = _goal_state()

    result = AgentHarness().run_agent_goal(
        agent=_ReducerUsingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=(_FakeTool(),)),
        max_agent_turns=2,
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details == {"fact_count": 1}
    assert len(goal_state.tool_results) == 1
    assert goal_state.facts[0].fact_type == "tool_result_seen"
    assert goal_state.facts[0].data == {"tool_name": "fake_tool"}


def _goal_state() -> GoalState:
    root_entity = EntityRef(entity_type="task", entity_id="T001")
    return GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=root_entity,
    )
