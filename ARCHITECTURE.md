# Architecture

## Design Goal

This project demonstrates a small agentic Obsidian vault summarizer without
using a third-party agent framework.

The project has two related goals:

- provide a concrete application that can read a small Markdown note vault and
  summarize the accessible knowledge it contains
- evolve `otto_agent`, a small first-party agent core, so that future agents can
  use harness-managed guardrails around runs, final decisions, and tool calls

The central design idea is to separate these responsibilities:

- the **agent** decides what should happen next
- the **harness** controls whether and how that decision is applied
- **guardrails** inspect, block, or mutate data at defined harness boundaries
- the **application runtime** wires concrete dependencies together
- the **application package** contains vault-specific skills, tools, guardrails,
  and command-line behavior
- `otto_agent` contains generic contracts, reusable agent-loop machinery, and
  small helpers for common agent patterns

The result is intentionally smaller than a general-purpose SDK, but more
structured than a single application script. This project uses the Obsidian
vault scenario to test whether `otto_agent` can make guardrail behavior explicit
without making the framework large.

## Package Responsibilities

### `otto_agent`

`otto_agent` is the reusable agent core.

The root package contains shared contracts, value types, and public helpers:

- `Agent`, `AgentRequest`, `ActionDecision`, and `FinalDecision`
- `StateUpdate`
- `GoalState`, `ToolResult`, `Claim`, `Fact`, `GoalOutput`, and `GoalResult`
- `Tool`, `ToolRegistry`, `ToolRequest`, and `ToolRuntime`
- `FunctionTool`, which exposes ordinary Python functions as tools
- `Guardrail`, `GuardrailResult`, `GuardrailSet`, and guardrail context types
- `ModelClient`, `ModelClientRegistry`, and paid-call budgeting
- `SkilledAgent`, a reusable model-backed agent configured by an `AgentSkill`
- OpenAI model-client helper functions
- validation and reducer protocols
- shared vocabulary such as completion types and state update operations
- small utilities such as JSON-safe pretty printing

The root package is the public surface of the small framework. The `agents` and
`harness` subpackages hold generic implementation helpers that support that
surface.

### `otto_agent.harness`

`otto_agent.harness` runs the generic agent loop.

It is responsible for:

- creating the per-turn `AgentRequest`
- asking the agent for a decision
- validating the decision with harness rules
- validating requested tool access
- applying accepted state updates
- applying configured guardrails
- executing requested tools through `ToolExecutor`
- appending `ToolResult` values to `GoalState`
- applying reducers after tool execution
- enforcing maximum agent turns
- collecting trace events
- returning a public `RunResult`

The harness does not know what an Obsidian vault is, where note data comes from,
which files are sensitive, or which model provider is being used.

### `otto_agent.agents`

`otto_agent.agents` contains generic helpers for model-backed agents.

It provides:

- `AgentSkill`
- final detail field definitions
- domain-neutral prompt construction
- structured model decision schema construction
- model output adaptation into `ActionDecision` or `FinalDecision`
- skill vocabulary validation

These helpers are used by `SkilledAgent`. Application code defines the skill
vocabulary, while `SkilledAgent` handles the repeated model-backed decision
plumbing.

### `obsidian_vault_summarizer`

`obsidian_vault_summarizer` is the concrete application package.

It contains:

- Obsidian vault summary goal-state creation
- `OBSIDIAN_VAULT_SUMMARIZER_SKILL`
- vault file-listing and file-reading functions
- function-backed tool definitions
- `SecretFileGuardrail`, which blocks attempts to read `Secret.md`
- runtime wiring for the agent, tools, guardrails, harness, and OpenAI model
  client
- the command-line interface

This package depends on `otto_agent`, but `otto_agent` does not depend on this
package.

## Agent, Harness, Runtime, And Guardrails

The runtime starts the work. It creates the initial vault-summary goal state,
registers the tools available to this run, creates the model client registry,
constructs the vault summarizer agent, configures guardrails, and calls the
harness.

The harness then owns the run.

The agent receives an `AgentRequest`, which contains:

- the current `GoalState`
- the `ToolRegistry` available to that agent

The agent returns an agent decision. The harness validates and processes that
decision. Guardrails run at harness-controlled boundaries, so the agent can
propose tool calls and final answers while the harness decides what is allowed
to happen.

## Skilled Agents

`SkilledAgent` is the reusable model-backed agent implementation.

Application code supplies:

- an agent name
- an `AgentSkill`
- a `ModelClientRegistry`
- a response schema name
- optional reducers
- an optional input-data factory
- an optional system prompt

For Obsidian Vault Summarizer, `create_obsidian_vault_summarizer_agent()`
configures a `SkilledAgent` with `OBSIDIAN_VAULT_SUMMARIZER_SKILL` and the model
registry.

## Goal State

`GoalState` is harness-owned state for one run.

It contains:

- `goal_id`
- `status`
- `root_entity`
- known entity references
- prior tool results
- recorded claims
- recorded facts
- outputs
- final results

For this application, the root entity is a local Obsidian vault whose entity id
is `local_vault`.

Agents can request state changes through structured `StateUpdate` values, but
the harness decides whether to apply them. The current summarizer does not need
custom reducers because the model prompt already includes prior tool results,
and the vault sample is intentionally small.

## Agent Decisions

Agents return one of two concrete decision types.

### `ActionDecision`

An `ActionDecision` asks the harness to call a tool:

```python
ActionDecision(
    tool_name="read_vault_file",
    arguments={"file_name": "Agent.md"},
    reason="Need the note content before summarizing the vault.",
)
```

The harness validates the tool request, applies before-tool guardrails, executes
the tool when allowed, applies after-tool guardrails, records the `ToolResult`,
applies reducers if any are configured, and continues the loop.

If a before-tool guardrail blocks a tool call, the harness records a synthetic
`ToolResult` that describes the blocked call instead of executing the tool. This
lets the agent see that the call was attempted and blocked, then continue using
the information that is available.

### `FinalDecision`

A `FinalDecision` asks the harness to complete the goal:

```python
FinalDecision(
    completion_type="done",
    details={
        "summary": "The notes describe agents and tools...",
        "main_topics": "agent, tool, action selection",
        "note_relationships": "Agents use tools to do external work.",
        "files_read": "Agent.md, Index.md, Tool.md",
        "reason_code": "summary_created",
    },
    reason="The accessible vault notes have been read.",
)
```

The harness validates the decision, applies final-decision guardrails, records a
`GoalResult`, and returns a public `RunResult`.

## Guardrails

Guardrails are harness-managed checks that can allow, block, or mutate data at
defined points in the run.

A guardrail returns a `GuardrailResult`:

- `allowed`: whether processing may continue
- `mutated`: whether the guardrail changed the context data
- `reason`: a short explanation used in trace events and failure details

`GuardrailSet` groups four kinds of guardrails:

- `before_run`
- `final_decision`
- `before_tool_call`
- `after_tool_call`

Each guardrail receives a mutable context object:

- `BeforeRunGuardrailContext`
- `FinalDecisionGuardrailContext`
- `BeforeToolCallGuardrailContext`
- `AfterToolCallGuardrailContext`

This makes it possible for guardrails to redact or replace data without
requiring the whole run to fail. For example, an after-tool guardrail can modify
a `ToolResult` before it is recorded in `GoalState`, and a final-decision
guardrail can change `FinalDecision.details` before the result is returned.

Blocking behavior depends on the point where the guardrail runs. A blocked
before-run or final-decision guardrail fails the goal. A blocked after-tool
guardrail also fails the goal because unsafe tool output has already been
produced. A blocked before-tool guardrail skips the real tool call, records a
blocked `ToolResult`, and lets the agent continue.

The application configures `SecretFileGuardrail` as a before-tool guardrail. It
blocks attempts to call `read_vault_file` for `Secret.md`, while still allowing
the agent to summarize the accessible notes.

## Agent Loop

The harness loop is intentionally simple:

1. Apply before-run guardrails before the loop starts.
2. Build an `AgentRequest`.
3. Ask the agent to decide.
4. Validate the decision with harness rules.
5. Validate registered tool access when needed.
6. Validate with agent-specific rules.
7. Apply accepted state updates.
8. If final, apply final-decision guardrails, record the result, and stop.
9. If action, apply before-tool guardrails.
10. Execute the tool, or record a blocked `ToolResult` when a before-tool
    guardrail blocks the call.
11. Apply after-tool guardrails to real tool results.
12. Record the tool result, apply reducers, and continue.
13. Stop with failure if `max_agent_turns` is reached.

This is the main place where the distinction between the agent and harness is
visible. The agent proposes; the harness controls.

## Tools And Function Tools

Tools are ordinary Python objects implementing the `Tool` protocol from
`otto_agent`.

A tool receives:

- a `ToolRequest`, which contains the arguments requested by the agent
- a `ToolRuntime`, which can carry harness-provided runtime services

A tool returns a `ToolResult`.

`FunctionTool` reduces tool boilerplate. It wraps an ordinary Python function,
maps structured tool arguments into keyword arguments, calls the function, and
converts the result into `ToolResult.data`.

Obsidian Vault Summarizer exposes two function-backed tools:

- `list_vault_files`, which returns the file names in the local vault
- `read_vault_file`, which returns the content of one named vault file

The file-reading tool guards against directory traversal by resolving the
requested path and ensuring it stays directly inside the vault directory.

## Tool Registry

`ToolRegistry` is a typed collection of tools available to one agent run.

The runtime creates the registry for this application. A tool is not available
to an agent unless the runtime explicitly includes it in the registry passed to
the harness.

This keeps tool access controlled by runtime wiring rather than by whatever
Python functions happen to exist in the codebase. Guardrails add another layer
of control around tool calls that are otherwise registered and valid.

## Reducers

Reducers update harness-owned state from tool results.

The reducer protocol remains part of `otto_agent`, but Obsidian Vault
Summarizer does not currently define custom reducers. The tool results are
compact, and the generic prompt builder includes prior tool results on later
agent turns.

Reducers would become useful if the application needed deterministic state
updates after tool execution. For example, a later version could record
normalized note metadata, topic facts, or link relationships as `Fact` values.

## State Updates And Validation

An agent decision may include `state_updates`.

Supported operations are:

- `add_claim`
- `add_fact`
- `add_output`

Harness-level validation checks the generic shape of state updates. For example,
`add_fact` must include a non-empty `fact_type` and a `data` dictionary.

Agent-level validation checks application vocabulary. `SkillVocabularyRule`
checks that a fact type, output type, final detail field, or final detail value
is allowed by `OBSIDIAN_VAULT_SUMMARIZER_SKILL`.

The validation order is deliberate:

1. generic harness rules
2. registered tool rule
3. agent-specific rules

If harness validation fails, agent-specific validation is not run. Guardrails
run after validation, at the point where the harness is ready to act on an
accepted decision.

## Skills

An `AgentSkill` packages model-facing guidance and vocabulary for one agent
capability.

A skill can define:

- the goal
- agent-specific instructions
- allowed claim types
- allowed fact types
- allowed output types
- final detail fields and allowed values

`otto_agent.agents` uses the skill to build the model prompt and structured
response schema. `SkilledAgent` uses the same skill to provide validation rules.

For this project, `OBSIDIAN_VAULT_SUMMARIZER_SKILL` defines vault-specific
concepts such as `vault_file_list`, `note_content`, `note_reference`,
`knowledge_topic`, `summary`, `main_topics`, `note_relationships`, `files_read`,
and `reason_code`. Those terms live in `obsidian_vault_summarizer`, not in the
generic harness loop.

The skill also tells the model to summarize only accessible knowledge and not to
mention blocked, inaccessible, hidden, filtered, unreadable, or unavailable
files in the final summary.

## Model Client Boundary

Model-provider code sits behind the `ModelClient` protocol in `otto_agent`.

The runtime provides a `ModelClientRegistry`. Agents request model clients by
capability, such as text or vision, rather than constructing provider clients
directly.

Paid model calls are controlled by `ModelCallBudget` and `BudgetedModelClient`.

This project includes an OpenAI helper in `otto_agent.openai_helper` because
multiple small Otto Agent samples are expected to use the same OpenAI-backed
client shape. Application code still receives a generic `ModelClientRegistry`,
and tests can use fake model clients without making OpenAI calls.

## Obsidian Vault Summary Flow

A typical real run looks like this:

1. The CLI starts with no command-line arguments.
2. Runtime creates an Obsidian vault summary goal state for `local_vault`.
3. Runtime registers the vault file-listing and file-reading tools.
4. Runtime configures `SecretFileGuardrail` as a before-tool guardrail.
5. Runtime creates an OpenAI-backed model client registry.
6. Runtime constructs a `SkilledAgent` configured with
   `OBSIDIAN_VAULT_SUMMARIZER_SKILL`.
7. The harness asks the agent for a decision.
8. The agent asks to list vault files.
9. The harness executes the file-listing tool and records the result.
10. The agent asks to read individual files.
11. The harness executes allowed file reads and records their results.
12. If the agent asks to read `Secret.md`, the guardrail blocks the real tool
    call and records a blocked `ToolResult`.
13. The agent continues with the accessible file contents.
14. The agent returns a final summary.
15. The harness records the final result and returns a structured `RunResult`.

## Testing Strategy

Normal checks run with:

```powershell
.\scripts\check.ps1
```

The normal check path should avoid live network and paid model calls. Tests can
use fake agents, fake tools, fake guardrails, fake model clients, and local
deterministic inputs where possible.

The most important test boundaries are:

- `otto_agent` harness behavior
- guardrail allow, block, and mutation behavior
- generic validation rules
- tool registry behavior
- `FunctionTool` result adaptation
- model client registry and budget enforcement
- `SkilledAgent` prompt/schema/model-response behavior
- Obsidian vault summarizer skill vocabulary
- Obsidian vault summarizer runtime wiring
- vault tool behavior, including directory traversal protection

This keeps the reusable core testable without the Obsidian application, and
keeps the Obsidian application testable without relying on a live model call for
every check.
