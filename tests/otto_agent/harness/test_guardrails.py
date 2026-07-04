"""Tests for Otto Agent guardrail behavior."""

from otto_agent.agent import ActionDecision, AgentDecision, AgentRequest, FinalDecision
from otto_agent.guardrail import (
    AfterToolCallGuardrailContext,
    BeforeRunGuardrailContext,
    BeforeToolCallGuardrailContext,
    FinalDecisionGuardrailContext,
    GuardrailResult,
    GuardrailSet,
)
from otto_agent.harness.runner import AgentHarness, RunStatus
from otto_agent.reducer import StateReducer
from otto_agent.state import EntityRef, GoalState, GoalStatus, ToolResult
from otto_agent.tool import ToolArgument, ToolRegistry, ToolRequest, ToolRuntime
from otto_agent.validation import ValidationRule


class _CompletingAgent:
    name = "completing_agent"

    def __init__(self) -> None:
        self.decide_call_count = 0

    def decide(self, request: AgentRequest) -> AgentDecision:
        """Return a final decision for the harness to accept."""
        self.decide_call_count += 1
        return FinalDecision(
            reason="The fake goal is complete.",
            completion_type="done",
            details={"message": "complete"},
        )

    def get_validation_rules(self) -> list[ValidationRule]:
        """Return no agent-specific validation rules."""
        return []

    def get_state_reducers(self) -> list[StateReducer]:
        """Return no state reducers."""
        return []


class _ToolUsingAgent:
    name = "tool_using_agent"

    def decide(self, request: AgentRequest) -> AgentDecision:
        """Use a tool, then complete after a tool result is available."""
        if request.goal_state.tool_results:
            tool_result = request.goal_state.tool_results[-1]
            return FinalDecision(
                reason="The tool result is available.",
                completion_type="done",
                details={
                    "tool_name": tool_result.tool_name,
                    "arguments": tool_result.arguments,
                    "data": tool_result.data,
                },
            )

        return ActionDecision(
            reason="Need to call the fake tool.",
            tool_name="fake_tool",
            arguments={"value": "original"},
        )

    def get_validation_rules(self) -> list[ValidationRule]:
        """Return no agent-specific validation rules."""
        return []

    def get_state_reducers(self) -> list[StateReducer]:
        """Return no state reducers."""
        return []


class _FakeTool:
    name = "fake_tool"
    description = "Fake tool used by guardrail tests."
    arguments = (
        ToolArgument(
            name="value",
            argument_type="string",
            description="A fake value.",
        ),
    )

    def __init__(self) -> None:
        self.requests: list[ToolRequest] = []

    def execute(
        self,
        tool_request: ToolRequest,
        tool_runtime: ToolRuntime,
    ) -> ToolResult:
        """Return a result containing the provided request value."""
        self.requests.append(tool_request)
        return ToolResult(
            tool_name=self.name,
            arguments=tool_request,
            data={"value": tool_request["value"]},
        )


class _ReplacementTool(_FakeTool):
    name = "replacement_tool"


class _BeforeRunGuardrail:
    name = "before_run_guardrail"

    def __init__(self, allowed: bool) -> None:
        self._allowed = allowed
        self.context: BeforeRunGuardrailContext | None = None

    def check(self, context: object) -> GuardrailResult:
        """Record the context and return the configured result."""
        if not isinstance(context, BeforeRunGuardrailContext):
            raise TypeError("Expected BeforeRunGuardrailContext.")

        self.context = context
        return GuardrailResult(
            allowed=self._allowed,
            mutated=False,
            reason="allowed" if self._allowed else "blocked",
        )


class _BeforeToolCallGuardrail:
    name = "before_tool_call_guardrail"

    def __init__(
        self,
        allowed: bool = True,
        replacement_tool_name: str | None = None,
        replacement_arguments: dict[str, object] | None = None,
    ) -> None:
        self._allowed = allowed
        self._replacement_tool_name = replacement_tool_name
        self._replacement_arguments = replacement_arguments
        self.context: BeforeToolCallGuardrailContext | None = None

    def check(self, context: object) -> GuardrailResult:
        """Record the context and optionally mutate the tool call."""
        if not isinstance(context, BeforeToolCallGuardrailContext):
            raise TypeError("Expected BeforeToolCallGuardrailContext.")

        self.context = context
        mutated = False

        if self._replacement_tool_name is not None:
            context.tool_name = self._replacement_tool_name
            mutated = True

        if self._replacement_arguments is not None:
            context.arguments = self._replacement_arguments
            mutated = True

        return GuardrailResult(
            allowed=self._allowed,
            mutated=mutated,
            reason="allowed" if self._allowed else "blocked",
        )


class _AfterToolCallGuardrail:
    name = "after_tool_call_guardrail"

    def __init__(
        self,
        allowed: bool = True,
        replacement_tool_result: ToolResult | None = None,
        replacement_value: str | None = None,
    ) -> None:
        self._allowed = allowed
        self._replacement_tool_result = replacement_tool_result
        self._replacement_value = replacement_value
        self.context: AfterToolCallGuardrailContext | None = None

    def check(self, context: object) -> GuardrailResult:
        """Record the context and optionally mutate the tool result."""
        if not isinstance(context, AfterToolCallGuardrailContext):
            raise TypeError("Expected AfterToolCallGuardrailContext.")

        self.context = context

        if self._replacement_tool_result is not None:
            context.tool_result = self._replacement_tool_result
            return GuardrailResult(
                allowed=self._allowed,
                mutated=True,
                reason="replaced tool result",
            )

        if self._replacement_value is not None:
            context.tool_result.data["value"] = self._replacement_value
            return GuardrailResult(
                allowed=self._allowed,
                mutated=True,
                reason="mutated tool result",
            )

        return GuardrailResult(
            allowed=self._allowed,
            mutated=False,
            reason="allowed" if self._allowed else "blocked",
        )


class _FinalDecisionGuardrail:
    name = "final_decision_guardrail"

    def __init__(
        self,
        allowed: bool = True,
        replacement_decision: FinalDecision | None = None,
        replacement_message: str | None = None,
    ) -> None:
        self._allowed = allowed
        self._replacement_decision = replacement_decision
        self._replacement_message = replacement_message
        self.context: FinalDecisionGuardrailContext | None = None

    def check(self, context: object) -> GuardrailResult:
        """Record the context and optionally mutate the final decision."""
        if not isinstance(context, FinalDecisionGuardrailContext):
            raise TypeError("Expected FinalDecisionGuardrailContext.")

        self.context = context

        if self._replacement_decision is not None:
            context.decision = self._replacement_decision
            return GuardrailResult(
                allowed=self._allowed,
                mutated=True,
                reason="replaced final decision",
            )

        if self._replacement_message is not None:
            context.decision.details["message"] = self._replacement_message
            return GuardrailResult(
                allowed=self._allowed,
                mutated=True,
                reason="mutated final decision details",
            )

        return GuardrailResult(
            allowed=self._allowed,
            mutated=False,
            reason="allowed" if self._allowed else "blocked",
        )


def test_before_run_guardrail_allows_agent_run() -> None:
    """Verify an allowing before-run guardrail lets the agent complete."""
    agent = _CompletingAgent()
    goal_state = _create_goal_state()
    guardrail = _BeforeRunGuardrail(allowed=True)

    result = AgentHarness().run_agent_goal(
        agent=agent,
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=()),
        max_agent_turns=1,
        guardrails=GuardrailSet(before_run=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details == {"message": "complete"}
    assert goal_state.status == GoalStatus.COMPLETED
    assert agent.decide_call_count == 1
    assert guardrail.context is not None
    assert guardrail.context.agent_name == "completing_agent"
    assert guardrail.context.goal_state is goal_state


def test_final_decision_guardrail_allows_final_decision() -> None:
    """Verify an allowing final-decision guardrail lets the goal complete."""
    goal_state = _create_goal_state()
    guardrail = _FinalDecisionGuardrail(allowed=True)

    result = AgentHarness().run_agent_goal(
        agent=_CompletingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=()),
        max_agent_turns=1,
        guardrails=GuardrailSet(final_decision=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.completion_type == "done"
    assert result.details == {"message": "complete"}
    assert goal_state.status == GoalStatus.COMPLETED
    assert guardrail.context is not None
    assert guardrail.context.goal_state is goal_state
    assert guardrail.context.decision.details == {"message": "complete"}


def test_before_tool_call_guardrail_allows_tool_call() -> None:
    """Verify an allowing before-tool guardrail lets tool execution continue."""
    tool = _FakeTool()
    guardrail = _BeforeToolCallGuardrail(allowed=True)

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=(tool,)),
        max_agent_turns=2,
        guardrails=GuardrailSet(before_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details["tool_name"] == "fake_tool"
    assert result.details["arguments"] == {"value": "original"}
    assert result.details["data"] == {"value": "original"}
    assert tool.requests == [{"value": "original"}]
    assert guardrail.context is not None
    assert guardrail.context.tool_name == "fake_tool"
    assert guardrail.context.arguments == {"value": "original"}


def test_before_tool_call_guardrail_blocks_tool_call() -> None:
    """Verify a blocking before-tool guardrail records a blocked tool result."""
    tool = _FakeTool()
    guardrail = _BeforeToolCallGuardrail(allowed=False)
    goal_state = _create_goal_state()

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=(tool,)),
        max_agent_turns=2,
        guardrails=GuardrailSet(before_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.completion_type == "done"
    assert result.details == {
        "tool_name": "fake_tool",
        "arguments": {"value": "original"},
        "data": {
            "blocked": True,
            "reason": "blocked",
            "reason_code": "guardrail_blocked",
        },
    }
    assert goal_state.tool_results == [
        ToolResult(
            tool_name="fake_tool",
            arguments={"value": "original"},
            data={
                "blocked": True,
                "reason": "blocked",
                "reason_code": "guardrail_blocked",
            },
        )
    ]
    assert tool.requests == []
    assert guardrail.context is not None
    assert guardrail.context.tool_name == "fake_tool"


def test_before_tool_call_guardrail_can_mutate_tool_arguments() -> None:
    """Verify a guardrail can replace arguments before tool execution."""
    tool = _FakeTool()
    guardrail = _BeforeToolCallGuardrail(
        replacement_arguments={"value": "replacement"},
    )

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=(tool,)),
        max_agent_turns=2,
        guardrails=GuardrailSet(before_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details["arguments"] == {"value": "replacement"}
    assert result.details["data"] == {"value": "replacement"}
    assert tool.requests == [{"value": "replacement"}]


def test_before_tool_call_guardrail_can_replace_tool_name() -> None:
    """Verify a guardrail can replace the tool name before execution."""
    fake_tool = _FakeTool()
    replacement_tool = _ReplacementTool()
    guardrail = _BeforeToolCallGuardrail(
        replacement_tool_name="replacement_tool",
        replacement_arguments={"value": "replacement"},
    )

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=(fake_tool, replacement_tool)),
        max_agent_turns=2,
        guardrails=GuardrailSet(before_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details["tool_name"] == "replacement_tool"
    assert result.details["arguments"] == {"value": "replacement"}
    assert fake_tool.requests == []
    assert replacement_tool.requests == [{"value": "replacement"}]


def test_after_tool_call_guardrail_allows_tool_result() -> None:
    """Verify an allowing after-tool guardrail stores the tool result."""
    guardrail = _AfterToolCallGuardrail(allowed=True)

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=(_FakeTool(),)),
        max_agent_turns=2,
        guardrails=GuardrailSet(after_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details["data"] == {"value": "original"}
    assert guardrail.context is not None
    assert guardrail.context.tool_result.data == {"value": "original"}


def test_after_tool_call_guardrail_blocks_tool_result() -> None:
    """Verify a blocking after-tool guardrail prevents storing the result."""
    goal_state = _create_goal_state()
    guardrail = _AfterToolCallGuardrail(allowed=False)

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=(_FakeTool(),)),
        max_agent_turns=2,
        guardrails=GuardrailSet(after_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.FAILED
    assert result.completion_type == "guardrail_blocked"
    assert result.details == {
        "agent": "tool_using_agent",
        "reason_code": "guardrail_blocked",
        "reason": "blocked",
    }
    assert goal_state.tool_results == []
    assert guardrail.context is not None


def test_after_tool_call_guardrail_can_mutate_tool_result_data() -> None:
    """Verify a guardrail can mutate tool result data before storage."""
    guardrail = _AfterToolCallGuardrail(replacement_value="[REDACTED]")

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=(_FakeTool(),)),
        max_agent_turns=2,
        guardrails=GuardrailSet(after_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details["data"] == {"value": "[REDACTED]"}


def test_after_tool_call_guardrail_can_replace_tool_result() -> None:
    """Verify the harness stores a tool result replaced by a guardrail."""
    replacement_tool_result = ToolResult(
        tool_name="replacement_tool",
        arguments={"value": "replacement"},
        data={"value": "replacement"},
    )
    guardrail = _AfterToolCallGuardrail(
        replacement_tool_result=replacement_tool_result,
    )

    result = AgentHarness().run_agent_goal(
        agent=_ToolUsingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=(_FakeTool(),)),
        max_agent_turns=2,
        guardrails=GuardrailSet(after_tool_call=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details == {
        "tool_name": "replacement_tool",
        "arguments": {"value": "replacement"},
        "data": {"value": "replacement"},
    }


def test_final_decision_guardrail_blocks_final_decision() -> None:
    """Verify a blocking final-decision guardrail fails the goal."""
    goal_state = _create_goal_state()
    guardrail = _FinalDecisionGuardrail(allowed=False)

    result = AgentHarness().run_agent_goal(
        agent=_CompletingAgent(),
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=()),
        max_agent_turns=1,
        guardrails=GuardrailSet(final_decision=(guardrail,)),
    )

    assert result.status == RunStatus.FAILED
    assert result.completion_type == "guardrail_blocked"
    assert result.details == {
        "agent": "completing_agent",
        "reason_code": "guardrail_blocked",
        "reason": "blocked",
    }
    assert goal_state.status == GoalStatus.FAILED
    assert guardrail.context is not None
    assert guardrail.context.goal_state is goal_state


def test_final_decision_guardrail_can_mutate_final_decision_details() -> None:
    """Verify a guardrail can mutate final decision details in place."""
    guardrail = _FinalDecisionGuardrail(
        replacement_message="[REDACTED]",
    )

    result = AgentHarness().run_agent_goal(
        agent=_CompletingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=()),
        max_agent_turns=1,
        guardrails=GuardrailSet(final_decision=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.details == {"message": "[REDACTED]"}


def test_final_decision_guardrail_can_replace_final_decision() -> None:
    """Verify the harness records a final decision replaced by a guardrail."""
    replacement_decision = FinalDecision(
        reason="The guardrail replaced the final decision.",
        completion_type="done",
        details={"message": "replacement"},
    )
    guardrail = _FinalDecisionGuardrail(
        replacement_decision=replacement_decision,
    )

    result = AgentHarness().run_agent_goal(
        agent=_CompletingAgent(),
        goal_state=_create_goal_state(),
        tool_registry=ToolRegistry(tools=()),
        max_agent_turns=1,
        guardrails=GuardrailSet(final_decision=(guardrail,)),
    )

    assert result.status == RunStatus.COMPLETED
    assert result.completion_type == "done"
    assert result.details == {"message": "replacement"}


def test_before_run_guardrail_blocks_agent_run() -> None:
    """Verify a blocking before-run guardrail prevents the agent from running."""
    agent = _CompletingAgent()
    goal_state = _create_goal_state()
    guardrail = _BeforeRunGuardrail(allowed=False)

    result = AgentHarness().run_agent_goal(
        agent=agent,
        goal_state=goal_state,
        tool_registry=ToolRegistry(tools=()),
        max_agent_turns=1,
        guardrails=GuardrailSet(before_run=(guardrail,)),
    )

    assert result.status == RunStatus.FAILED
    assert result.details == {
        "agent": "completing_agent",
        "reason_code": "guardrail_blocked",
        "reason": "blocked",
    }
    assert goal_state.status == GoalStatus.FAILED
    assert agent.decide_call_count == 0
    assert guardrail.context is not None
    assert guardrail.context.agent_name == "completing_agent"
    assert guardrail.context.goal_state is goal_state


def _create_goal_state() -> GoalState:
    return GoalState(
        goal_id="fake-goal",
        status=GoalStatus.RUNNING,
        root_entity=EntityRef(
            entity_type="fake_entity",
            entity_id="fake-entity",
        ),
    )
