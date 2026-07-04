from otto_agent.agent import FinalDecision, StateUpdate
from otto_agent.agents.skill import AgentSkill, FinalDetailField
from otto_agent.agents.skill_validation import SkillVocabularyRule
from otto_agent.state import EntityRef, GoalState, GoalStatus


def test_skill_vocabulary_rule_accepts_valid_vocabulary() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={"result_code": "success"},
        reason="The goal is complete.",
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
                    "fact_type": "verified_condition",
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

    errors = SkillVocabularyRule(_skill()).validate(decision, _goal_state())

    assert errors == []


def test_skill_vocabulary_rule_rejects_invalid_state_update_type() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={"result_code": "success"},
        reason="The goal is complete.",
        state_updates=[
            StateUpdate(
                operation="add_fact",
                arguments={
                    "fact_type": "unsupported_fact",
                    "data": {"verified": True},
                },
            )
        ],
    )

    errors = SkillVocabularyRule(_skill()).validate(decision, _goal_state())

    assert len(errors) == 1
    assert errors[0].code == "invalid_fact_type"


def test_skill_vocabulary_rule_rejects_invalid_final_detail_value() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={"result_code": "unsupported"},
        reason="The goal is complete.",
    )

    errors = SkillVocabularyRule(_skill()).validate(decision, _goal_state())

    assert len(errors) == 1
    assert errors[0].code == "invalid_final_detail_value"


def test_skill_vocabulary_rule_rejects_missing_final_detail_field() -> None:
    decision = FinalDecision(
        completion_type="done",
        details={},
        reason="The goal is complete.",
    )

    errors = SkillVocabularyRule(_skill()).validate(decision, _goal_state())

    assert len(errors) == 1
    assert errors[0].code == "missing_final_detail_field"


def _skill() -> AgentSkill:
    return AgentSkill(
        name="fake_skill",
        goal="Complete a generic goal.",
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


def _goal_state() -> GoalState:
    root_entity = EntityRef(entity_type="task", entity_id="T001")
    return GoalState(
        goal_id="goal-T001",
        status=GoalStatus.RUNNING,
        root_entity=root_entity,
    )
