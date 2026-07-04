from otto_agent.agents.model_prompt import create_model_user_prompt
from otto_agent.agents.skill import AgentSkill, FinalDetailField
from otto_agent.state import EntityRef, GoalState, GoalStatus, ToolResult
from otto_agent.tool import ToolArgument, ToolRegistry, ToolRequest, ToolRuntime
from otto_agent.vocabulary import COMPLETION_TYPES, STATE_UPDATE_OPERATIONS


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


def test_model_prompt_includes_tool_details() -> None:
    prompt = _prompt()

    assert "Available tools:" in prompt
    assert "inspect_record" in prompt
    assert "record_id" in prompt
    assert "Identifier of the record." in prompt


def test_model_prompt_includes_completion_types() -> None:
    prompt = _prompt()

    for completion_type in COMPLETION_TYPES:
        assert completion_type in prompt


def test_model_prompt_includes_state_update_operations() -> None:
    prompt = _prompt()

    for operation in STATE_UPDATE_OPERATIONS:
        assert operation in prompt


def test_model_prompt_includes_skill_vocabulary() -> None:
    prompt = _prompt()

    assert "reported_condition" in prompt
    assert "verified_condition" in prompt
    assert "draft_note" in prompt
    assert "result_code" in prompt
    assert "success" in prompt


def test_model_prompt_has_separate_tool_results_section() -> None:
    prompt = create_model_user_prompt(
        skill=_skill(),
        goal_state=_goal_state(
            tool_results=[
                ToolResult(
                    tool_name="inspect_record",
                    arguments={"record_id": "R001"},
                    data={"value": "example"},
                )
            ],
        ),
        tool_registry=_tool_registry(),
    )
    goal_state_section = prompt.split("Prior tool results:")[0]
    tool_results_section = prompt.split("Prior tool results:")[1]

    assert "tool_results" not in goal_state_section
    assert "inspect_record" in tool_results_section
    assert "example" in tool_results_section


def _prompt() -> str:
    return create_model_user_prompt(
        skill=_skill(),
        goal_state=_goal_state(),
        tool_registry=_tool_registry(),
    )


def _skill() -> AgentSkill:
    return AgentSkill(
        name="fake_skill",
        goal="Complete a generic goal.",
        instructions="Prefer verified data over unverified data.",
        claim_types={
            "reported_condition": "A condition reported by an external source.",
        },
        fact_types={
            "verified_condition": "A condition verified from available evidence.",
        },
        output_types={
            "draft_note": "A note drafted while working on the goal.",
        },
        final_detail_fields={
            "result_code": FinalDetailField(
                description="The structured result code.",
                allowed_values={"success": "The goal succeeded."},
            )
        },
    )


def _goal_state(tool_results: list[ToolResult] | None = None) -> GoalState:
    root_entity = EntityRef(entity_type="task", entity_id="T001")
    return GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=root_entity,
        tool_results=tool_results or [],
    )


def _tool_registry() -> ToolRegistry:
    return ToolRegistry(tools=(_FakeTool(),))
