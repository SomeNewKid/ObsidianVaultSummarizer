import pytest

from otto_agent.model import (
    ModelCallBudget,
    ModelClient,
    ModelClientRegistration,
    ModelClientRegistry,
    ModelRequest,
    ModelResponse,
)


class _FakeModelClient:
    def __init__(self, label: str) -> None:
        self.label = label
        self.requests: list[ModelRequest] = []

    def complete(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        return ModelResponse(data={"label": self.label})


def test_model_client_registry_returns_client_by_name() -> None:
    client = _FakeModelClient("named")
    registry = ModelClientRegistry(
        clients=(
            _registration(
                name="named_client",
                client=client,
                is_text_enabled=True,
            ),
        )
    )

    assert registry.get_by_name("named_client") is client
    assert registry.get_by_name("missing_client") is None


def test_model_client_registry_rejects_duplicate_names() -> None:
    with pytest.raises(ValueError, match="Duplicate model client name: model"):
        ModelClientRegistry(
            clients=(
                _registration(name="model", client=_FakeModelClient("first")),
                _registration(name="model", client=_FakeModelClient("second")),
            )
        )


def test_model_client_registry_returns_text_client() -> None:
    vision_client = _FakeModelClient("vision")
    text_client = _FakeModelClient("text")
    registry = ModelClientRegistry(
        clients=(
            _registration(
                name="vision",
                client=vision_client,
                is_vision_enabled=True,
            ),
            _registration(
                name="text",
                client=text_client,
                is_text_enabled=True,
            ),
        )
    )

    assert registry.get_text_client() is text_client


def test_model_client_registry_returns_vision_client() -> None:
    text_client = _FakeModelClient("text")
    vision_client = _FakeModelClient("vision")
    registry = ModelClientRegistry(
        clients=(
            _registration(
                name="text",
                client=text_client,
                is_text_enabled=True,
            ),
            _registration(
                name="vision",
                client=vision_client,
                is_vision_enabled=True,
            ),
        )
    )

    assert registry.get_vision_client() is vision_client


def test_model_client_registry_prefers_free_client() -> None:
    paid_client = _FakeModelClient("paid")
    free_client = _FakeModelClient("free")
    registry = ModelClientRegistry(
        model_call_budget=ModelCallBudget(max_paid_model_calls=1),
        clients=(
            _registration(
                name="paid_text",
                client=paid_client,
                is_text_enabled=True,
                is_paid=True,
            ),
            _registration(
                name="free_text",
                client=free_client,
                is_text_enabled=True,
            ),
        ),
    )

    assert registry.get_text_client() is free_client


def test_model_client_registry_can_prefer_first_paid_client() -> None:
    paid_client = _FakeModelClient("paid")
    free_client = _FakeModelClient("free")
    budget = ModelCallBudget(max_paid_model_calls=1)
    registry = ModelClientRegistry(
        model_call_budget=budget,
        clients=(
            _registration(
                name="paid_text",
                client=paid_client,
                is_text_enabled=True,
                is_paid=True,
            ),
            _registration(
                name="free_text",
                client=free_client,
                is_text_enabled=True,
            ),
        ),
    )
    model_client = registry.get_text_client(prefer_free=False)

    assert model_client is not None
    response = model_client.complete(_model_request())

    assert response == ModelResponse(data={"label": "paid"})
    assert budget.paid_model_call_count == 1
    assert len(paid_client.requests) == 1
    assert len(free_client.requests) == 0


def test_paid_model_client_requires_budget() -> None:
    registry = ModelClientRegistry(
        clients=(
            _registration(
                name="paid_text",
                client=_FakeModelClient("paid"),
                is_text_enabled=True,
                is_paid=True,
            ),
        )
    )

    with pytest.raises(RuntimeError, match="Paid model client requires a model call"):
        registry.get_text_client()


def test_paid_model_client_enforces_budget() -> None:
    registry = ModelClientRegistry(
        model_call_budget=ModelCallBudget(max_paid_model_calls=1),
        clients=(
            _registration(
                name="paid_text",
                client=_FakeModelClient("paid"),
                is_text_enabled=True,
                is_paid=True,
            ),
        ),
    )
    model_client = registry.get_text_client()

    assert model_client is not None
    model_client.complete(_model_request())

    with pytest.raises(RuntimeError, match="Paid model call limit exceeded."):
        model_client.complete(_model_request())


def test_model_client_registry_returns_none_when_capability_is_missing() -> None:
    registry = ModelClientRegistry(
        clients=(
            _registration(
                name="text",
                client=_FakeModelClient("text"),
                is_text_enabled=True,
            ),
        )
    )

    assert registry.get_vision_client() is None


def _registration(
    name: str,
    client: ModelClient,
    is_text_enabled: bool = False,
    is_vision_enabled: bool = False,
    is_paid: bool = False,
) -> ModelClientRegistration:
    return ModelClientRegistration(
        name=name,
        client=client,
        is_text_enabled=is_text_enabled,
        is_vision_enabled=is_vision_enabled,
        is_paid=is_paid,
    )


def _model_request() -> ModelRequest:
    return ModelRequest(
        system_prompt="System prompt.",
        user_prompt="User prompt.",
        input_data={},
    )
