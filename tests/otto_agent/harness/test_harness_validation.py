from otto_agent.agent import AgentDecision, FinalDecision
from otto_agent.harness.validation import validate_decision
from otto_agent.state import EntityRef, GoalState, GoalStatus
from otto_agent.validation import ValidationError


class _RejectRule:
    def validate(
        self,
        decision: AgentDecision,
        goal_state: GoalState,
    ) -> list[ValidationError]:
        return [
            ValidationError(
                code="rejected_for_test",
                message="The decision was rejected.",
            )
        ]


def test_validate_decision_collects_rule_errors() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={},
        reason="The goal is complete.",
    )

    result = validate_decision(decision, _goal_state(), [_RejectRule()])

    assert not result.accepted
    assert result.errors == [
        ValidationError(
            code="rejected_for_test",
            message="The decision was rejected.",
        )
    ]


def _goal_state() -> GoalState:
    root_entity = EntityRef(entity_type="task", entity_id="T001")
    return GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=root_entity,
    )
