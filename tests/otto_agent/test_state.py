import pytest

from otto_agent.state import (
    Claim,
    EntityRef,
    Fact,
    GoalOutput,
    GoalResult,
    GoalState,
    GoalStatus,
    ToolResult,
)


def test_goal_state_records_root_entity_reference() -> None:
    root_entity = EntityRef(entity_type="task", entity_id="T001")

    goal_state = GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=root_entity,
    )

    assert goal_state.entities == [root_entity]


def test_goal_state_ignores_duplicate_entity_reference() -> None:
    root_entity = EntityRef(entity_type="task", entity_id="T001")
    goal_state = GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=root_entity,
    )

    goal_state.set_entity_reference(root_entity)

    assert goal_state.entities == [root_entity]


def test_goal_state_rejects_conflicting_entity_reference() -> None:
    goal_state = GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=EntityRef(entity_type="task", entity_id="T001"),
    )

    with pytest.raises(RuntimeError, match="Conflicting entity reference for task."):
        goal_state.set_entity_reference(EntityRef(entity_type="task", entity_id="T002"))


def test_goal_state_records_mutations() -> None:
    goal_state = GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=EntityRef(entity_type="task", entity_id="T001"),
    )
    tool_result = ToolResult(
        tool_name="lookup_record",
        arguments={"record_id": "R001"},
        data={"found": True},
    )

    goal_state.add_tool_result(tool_result)
    goal_state.add_claim("reported_condition", {"source": "request"})
    goal_state.add_fact("verified_condition", {"verified": True})
    goal_state.add_output("draft_message", {"text": "Hello"})
    goal_state.add_result("done", {"reason": "complete"})

    assert goal_state.tool_results == [tool_result]
    assert goal_state.claims == [
        Claim(claim_type="reported_condition", data={"source": "request"})
    ]
    assert goal_state.facts == [
        Fact(fact_type="verified_condition", data={"verified": True})
    ]
    assert goal_state.outputs == [
        GoalOutput(output_type="draft_message", data={"text": "Hello"})
    ]
    assert goal_state.results == [
        GoalResult(result_type="done", data={"reason": "complete"})
    ]
