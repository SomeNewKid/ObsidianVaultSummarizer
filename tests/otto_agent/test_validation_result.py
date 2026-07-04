from otto_agent.validation import (
    ValidationError,
    ValidationResult,
)


def test_validation_result_is_accepted_when_empty() -> None:
    result = ValidationResult()

    assert result.accepted


def test_validation_result_is_not_accepted_when_errors_are_present() -> None:
    result = ValidationResult(
        errors=[
            ValidationError(
                code="invalid_decision",
                message="The decision is invalid.",
            )
        ]
    )

    assert not result.accepted
