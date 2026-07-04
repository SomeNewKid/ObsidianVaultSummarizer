from __future__ import annotations

from pathlib import Path

from otto_agent.function_tool import FunctionTool
from otto_agent.guardrail import (
    BeforeToolCallGuardrailContext,
    Guardrail,
    GuardrailResult,
)
from otto_agent.tool import ToolArgument

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_VAULT_DIRECTORY = _PROJECT_ROOT / "vault"
VERBOSE_LOGGING = False


def list_vault_files() -> list[str]:
    """Return the Markdown file names in the local Obsidian vault."""
    if VERBOSE_LOGGING:
        print("Tool call: list_vault_files()")
    return sorted(path.name for path in _VAULT_DIRECTORY.iterdir() if path.is_file())


def read_vault_file(file_name: str) -> str:
    """Return the content of a single file in the local Obsidian vault."""
    if VERBOSE_LOGGING:
        print(f"Tool call: read_vault_file({file_name!r})")

    vault_directory = _VAULT_DIRECTORY.resolve()
    requested_path = (vault_directory / file_name).resolve()

    if requested_path.parent != vault_directory:
        raise ValueError("File name must refer to a file directly in the vault.")

    if not requested_path.is_file():
        raise FileNotFoundError(f"Vault file not found: {file_name}")

    return requested_path.read_text(encoding="utf-8")


LIST_VAULT_FILES_TOOL = FunctionTool(
    name="list_vault_files",
    description="List the files available in the local Obsidian vault.",
    function=list_vault_files,
    result_key="file_names",
)

READ_VAULT_FILE_TOOL = FunctionTool(
    name="read_vault_file",
    description=(
        "Read the Markdown content of a named file in the local Obsidian vault."
    ),
    function=read_vault_file,
    arguments=(
        ToolArgument(
            name="file_name",
            argument_type="string",
            description="The name of the file to read from the vault.",
        ),
    ),
    result_key="content",
)


class SecretFileGuardrail(Guardrail):
    name = "secret_file_guardrail"

    def check(self, context: object) -> GuardrailResult:
        if not isinstance(context, BeforeToolCallGuardrailContext):
            return GuardrailResult(
                allowed=True, mutated=False, reason="Not a tool-call context."
            )

        if context.tool_name != "read_vault_file":
            return GuardrailResult(
                allowed=True, mutated=False, reason="Not a file-read tool."
            )

        file_name = context.arguments.get("file_name")
        if not isinstance(file_name, str):
            return GuardrailResult(
                allowed=False,
                mutated=False,
                reason="File name argument is not a string.",
            )
        if file_name.lower() == "secret.md":
            return GuardrailResult(
                allowed=False, mutated=False, reason="Secret.md may not be read."
            )

        return GuardrailResult(allowed=True, mutated=False, reason="Tool call allowed.")
