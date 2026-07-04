# Obsidian Vault Summarizer

Obsidian Vault Summarizer is a small Python command-line sample for exploring
how a lightweight first-party agent framework can support guardrails around
agent runs, final decisions, and tool calls.

> [!WARNING]
> This is an experimental project and should not be considered production-ready.

The project summarizes the knowledge contained in a tiny local Markdown note
vault. It uses `otto_agent`, a small in-project agent core that separates
generic agent and harness concerns from the Obsidian-specific application code.
This version of `otto_agent` adds guardrail support so the harness can allow,
block, or mutate data at important points in the agent loop.

## What It Does

Run the vault summarizer from the repository root:

```powershell
.\.venv\Scripts\python.exe -m obsidian_vault_summarizer
```

The agent flow is:

1. Create an Obsidian vault summary goal for the local `vault` directory.
2. Ask the model-backed vault summarizer agent for the next structured decision.
3. Execute a tool that lists available vault files.
4. Execute a tool that reads individual vault files.
5. Apply a before-tool guardrail that blocks reads of `Secret.md`.
6. Record blocked tool calls as tool results so the agent can continue.
7. Ask the agent to summarize the accessible knowledge in the vault.
8. Print the final summary and, when verbose logging is enabled, the full
   `RunResult` with trace events.

The sample vault is intentionally tiny. Its purpose is to exercise the agent
loop and guardrail behavior, not to be a realistic personal knowledge base.

## Requirements

- Python 3.11.
- PowerShell on Windows.
- An `OPENAI_API_KEY` environment variable for OpenAI model calls.

## Setup

Create the virtual environment and install the project with development
dependencies:

```powershell
.\scripts\setup-dev.ps1
```

The setup script expects Python 3.11 and uses a local `.venv` directory.

## Running

Run the CLI:

```powershell
.\.venv\Scripts\python.exe -m obsidian_vault_summarizer
```

The command prints the final summary. With verbose CLI logging enabled, it also
prints structured output for the full agent run. A successful result includes
final details such as:

```json
{
  "summary": "The notes describe the concepts of agents and tools...",
  "main_topics": "agent, tool, action selection, interaction, task execution",
  "note_relationships": "Agents select actions and utilize tools...",
  "files_read": "Agent.md, Index.md, Tool.md",
  "reason_code": "summary_created"
}
```

OpenAI API calls may incur usage costs. The current agent uses `gpt-4.1-mini`
with a paid model-call budget of 10 calls per run.

## Guardrails

The main framework feature demonstrated by this project is guardrail support in
`otto_agent`.

Guardrails can run:

- before the agent loop starts
- when an agent returns a final decision
- before a tool call is executed
- after a tool call returns

Each guardrail returns a `GuardrailResult` with:

- `allowed`: whether processing may continue
- `mutated`: whether the guardrail changed the context data
- `reason`: a short explanation for trace output and failure details

The harness passes mutable context objects to guardrails. This lets guardrails
redact or replace data without requiring the whole run to fail.

For before-tool guardrails, a blocked call is recorded as a synthetic
`ToolResult` instead of executing the tool. This lets the model see that the
tool call was attempted and blocked, then continue toward the goal using the
available information.

## Development Checks

Run formatting, linting, type checking, and tests:

```powershell
.\scripts\check.ps1
```

This runs:

- `ruff format .`
- `ruff check .`
- `pyright`
- `pytest`

The normal test suite uses deterministic tests and fake model clients. It does
not need to make OpenAI API calls.

## Project Structure

```text
src/otto_agent/
  agent.py                 Generic agent request and decision contracts
  state.py                 Goal state, entity references, facts, claims, results
  tool.py                  Tool and tool registry contracts
  function_tool.py         Adapter for exposing simple functions as tools
  guardrail.py             Guardrail result, context, and set contracts
  model.py                 Generic model client contracts and paid-call budget
  openai_helper.py         OpenAI model-client helper
  skilled_agent.py         Reusable AgentSkill-backed model agent
  reducer.py               Reducer protocol for deterministic state updates
  validation.py            Validation result and rule contracts
  vocabulary.py            Shared completion and state-update vocabulary
  utilities.py             Small output and serialization helpers
  agents/                  Prompt, schema, skill, and model-decision helpers
  harness/                 Agent loop, validation, tracing, tools, guardrails

src/obsidian_vault_summarizer/
  __main__.py              Package entry point for python -m
  cli.py                   Command-line entry point
  agent.py                 Vault agent, goal, tools, guardrails, runtime wiring
  skill.py                 Vault summarizer skill vocabulary
  tools.py                 Vault file-listing and file-reading tools

tests/
  otto_agent/              Tests for the reusable agent core
  obsidian_vault_summarizer/
                            Tests for app-specific agent, skill, and tools

vault/
  Agent.md
  Index.md
  Tool.md
  Secret.md

scripts/
  setup-dev.ps1
  check.ps1
```

## Notes

`otto_agent` is intentionally small. It exists to make the core mechanics
visible: agents propose structured decisions, the harness validates those
decisions, tools provide controlled side effects, model providers sit behind a
generic `ModelClient` boundary, and guardrails can block or mutate data at
well-defined points.

Obsidian Vault Summarizer is deliberately narrow. It is not a production
Obsidian integration, search index, note-management system, privacy tool, or
general document summarizer. The point of the project is to exercise guardrail
mechanics in a concrete agent workflow.

## Third-Party Notices

This project has a direct runtime dependency on the `openai` Python package
(Apache-2.0). See the package's PyPI license metadata for full license and
notice terms.

## License

GNU General Public License v3.0. See the `LICENSE` file for details.
