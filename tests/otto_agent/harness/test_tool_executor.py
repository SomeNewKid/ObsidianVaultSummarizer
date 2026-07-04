import pytest

from otto_agent.harness.tool_executor import ToolExecutor
from otto_agent.state import ToolResult
from otto_agent.tool import ToolArgument, ToolRegistry, ToolRequest, ToolRuntime


class _FakeTool:
    name = "fake_tool"
    description = "Fake tool used by tool executor tests."
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
            data={"value": tool_request["value"]},
        )


def test_tool_executor_executes_registered_tool() -> None:
    result = ToolExecutor(ToolRegistry(tools=(_FakeTool(),))).execute(
        tool_name="fake_tool",
        tool_request={"value": "example"},
        tool_runtime=ToolRuntime(),
    )

    assert result == ToolResult(
        tool_name="fake_tool",
        arguments={"value": "example"},
        data={"value": "example"},
    )


def test_tool_executor_rejects_unregistered_tool() -> None:
    executor = ToolExecutor(ToolRegistry(tools=()))

    with pytest.raises(ValueError, match="Tool 'missing_tool' is not registered."):
        executor.execute(
            tool_name="missing_tool",
            tool_request={},
            tool_runtime=ToolRuntime(),
        )
