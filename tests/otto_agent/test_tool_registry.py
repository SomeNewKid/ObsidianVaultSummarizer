import pytest

from otto_agent.state import ToolResult
from otto_agent.tool import (
    ToolArgument,
    ToolRegistry,
    ToolRequest,
    ToolRuntime,
)


class _FakeTool:
    name = "fake_tool"
    description = "Fake tool used by tool registry tests."
    arguments = (
        ToolArgument(
            name="value",
            argument_type="string",
            description="A fake value.",
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
            data={"runtime_value_count": len(tool_runtime.values)},
        )


class _DuplicateFakeTool(_FakeTool):
    name = "fake_tool"


def test_tool_registry_returns_registered_tool() -> None:
    tool = _FakeTool()
    registry = ToolRegistry(tools=(tool,))

    assert registry.get("fake_tool") is tool


def test_tool_registry_returns_none_for_missing_tool() -> None:
    registry = ToolRegistry(tools=(_FakeTool(),))

    assert registry.get("missing_tool") is None


def test_tool_registry_rejects_duplicate_tool_names() -> None:
    with pytest.raises(ValueError, match="Duplicate tool name: fake_tool"):
        ToolRegistry(tools=(_FakeTool(), _DuplicateFakeTool()))
