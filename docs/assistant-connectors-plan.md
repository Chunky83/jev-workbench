# Jev Workbench: assistant connectors and real task workflows

Status: proposed implementation plan. September 19, 2026.

## Recommendation

Build one Python MCP server around the existing Workbench engine. MCP is the tool interface that lets a signed-in assistant read a case, contribute evidence, request a Jev evaluation, and submit a proposed repair. Keep the desktop in C++/Qt and all AI integration, validation, and execution in Python.

Start with assistant-led work: use Claude Desktop or Codex to investigate a real issue, while Workbench holds the evidence, decisions, and results. Add the ChatGPT connection using its documented private tunnel where available, or an authenticated remote endpoint. Then consider starting assistant sessions from inside Workbench.

This builds a coordinated system using existing models. It does not train a new model. The improvement comes from better evidence, reusable task instructions, focused Jev questions, and verified outcomes.

## What connectors actually provide

| Connection | Intended use | Authentication and hosting |
|---|---|---|
| Claude Desktop local MCP | Claude calls our tools on this computer | User signs into Claude; local MCP is separate from remote connectors. No Anthropic API key in Workbench. |
| ChatGPT MCP connection | ChatGPT calls the same tool contract | Developer-mode availability depends on account/workspace policy. Use Secure MCP Tunnel if available, otherwise authenticated HTTPS. |
| Claude remote connector | Use Workbench tools from claude.ai and other supported clients | Remote server must be reachable from Anthropic infrastructure; a laptop localhost address alone is insufficient. |
| Codex local integration | Practical repository investigation and coding with ChatGPT account access | Start with MCP tools in the signed-in client; optionally integrate the documented Codex app-server later. |

Connectors expose our tools to an assistant; they do not supply a general inference endpoint to our program. Chat usage and subscription limits still apply. Jev continues to use the existing TypeSafe key and credits. Authentication to our remote connector, if used, is a separate OAuth connection, not an OpenAI or Anthropic inference key.

OpenAI documents MCP connection testing, HTTPS or Secure MCP Tunnel, and account-dependent developer mode in its [official connection guide](https://developers.openai.com/plugins/deploy/connect-chatgpt). Claude documents the remote/local distinction in its [custom connector guide](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp).

For a later Workbench-hosted assistant experience, [Codex app-server](https://learn.chatgpt.com/docs/app-server) supports managed ChatGPT sign-in. Let Codex own that authentication lifecycle. Claude Code documents [programmatic structured output](https://code.claude.com/docs/en/headless) and [subscription login](https://code.claude.com/docs/en/authentication), but these do not authorize copying Claude login tokens into our own inference client. Keep the first Claude integration assistant-led. Any later integration that launches the unmodified Claude Code binary needs a separate packaging and terms review against its [documented integration conditions](https://code.claude.com/docs/en/legal-and-compliance).

## The useful loop

1. **Choose a task.** Select an existing issue, repository, branch, and desired result. Record exactly what would demonstrate success.
2. **Gather evidence.** The assistant uses its available repository/browser tools, or a named Workbench collector. Save relevant logs, file references, test results, and screenshot observations with origins and timestamps.
3. **Prepare state.** Python validates the evidence and writes a new state revision. Facts, reported symptoms, assistant hypotheses, and missing information remain separate.
4. **Ask Jev focused questions.** For example: which proposed explanation best fits these observations, or is the evidence sufficient to choose a next check? Include an insufficient-evidence answer. Preserve the actual model response.
5. **Propose work.** The assistant submits a structured proposal containing the patch or named check, supporting evidence, expected result, and verification steps.
6. **Review and execute.** The user approves the concrete proposal in Workbench. Python performs the approved action in the selected workspace. Changing the patch, inputs, or workspace invalidates that approval.
7. **Verify.** Run real assertions and record observed results. A model's opinion cannot set a task to verified. A failing test starts a new evidence revision; stop when the task succeeds or the configured budget is exhausted.

Jev evaluates state against typed questions and returns structured answers; it is not the patch-writing engine. The existing TypeSafe integration remains responsible for its authenticated requests. See the [TypeSafe API reference](https://docs.typesafe.ai/api).

## First real workflow

Use one existing failing test or diagnostic issue in a separate target-project worktree. Do not invent a failure or assume the earlier customer-configuration example is real.

The assistant reads the failure and relevant code, submits a small evidence packet, and offers up to three explanations with next checks. Jev evaluates those candidates. The assistant prepares a patch, the user reviews it, and Workbench runs the approved existing test and relevant regression checks. The result links the original failure, patch, and verification output.

For visual debugging, record screenshot dimensions and capture time, element bounds, hit-testing, console errors, and interaction results. Vision descriptions are assistant observations; DOM measurements and click results are separate evidence. Do not treat an interpretation of a screenshot as proof that a control is clickable.

For website security testing, each case specifies authorized hosts, permitted test accounts, allowed checks, and request limits. Start with a named access-control regression check against local or staging environments. No arbitrary model-generated shell or unrestricted URL scanner is exposed through MCP.

## Shared files and contracts

Retain the existing transactional case manifest and revision directories. Add a versioned workflow format alongside them, with an explicit migration when needed; do not reinterpret existing schema-version-1 cases silently. Application version and data-schema version remain independent.

```text
case/
  test.json                         Case identity and current revision
  revisions/<revision>/
    state.json                      Facts, hypotheses, gaps, evidence references
    primitives.json                 Jev questions and criteria
    instructions.md                 Plain-language task instructions
    runner.json                     Named checks and limits
  evidence/<evidence-id>/
    metadata.json                   Origin, capture time, content hash, sensitivity
    content.txt                     Selected log or code excerpt
  proposals/<proposal-id>.json       Candidate change and verification plan
  approvals/<approval-id>.json       User approval tied to exact proposal hash
  runs/<run-id>/
    inputs.json                     Immutable input and revision identifiers
    jev-response.json               Actual response, when called
    execution.json                  Exit status and captured output
    verification.json               Assertions and evidence, not model confidence
    result.json                     Final normalized outcome
```

Keep credentials outside this tree. Evidence files containing private information stay out of source control. Retain raw evidence locally; share selected excerpts. A collector should omit sensitive fields by construction, with a review step for free text. Do not promise perfect automatic redaction.

Proposed code modules:

```text
src/jev_diagnostics/
  connectors/mcp_server.py           Transport and tool declarations
  connectors/tool_handlers.py        Route validated calls to services
  workflow/state_service.py          Revisions and evidence references
  workflow/proposals.py              Validate proposed work
  workflow/approvals.py              User approval and expiration
  workflow/runner.py                 Execute registered actions
  workflow/verification.py           Evaluate real test assertions
  workflow/budget.py                 Call, time, and size limits
  collectors/                       Named evidence collectors
schemas/                            JSON contracts, separately versioned
instructions/                       Shared workflow and host-specific guidance
tests/                              Contract, permission, and replay checks
```

Use descriptive functions, ordinary JSON parsing, and explicit checks. No regular expressions. Reuse current case storage, request builder, response validation, and reporting rather than maintaining separate connector implementations.

## Small initial tool surface

| Tool | Result and permission |
|---|---|
| `list_cases` | Names and summaries of explicitly shared cases |
| `read_case` | A selected revision and bounded evidence excerpts |
| `submit_evidence` | Validated new evidence, attributed to the submitting assistant |
| `propose_state` | A proposed revision; no overwrite of unsaved desktop edits |
| `evaluate_case` | Jev answers for an exact revision, within a user-enabled budget |
| `submit_proposal` | Structured patch/check proposal; does not execute it |
| `read_run` | Observed execution and verification results |

Execution is initiated by the Workbench approval UI in the first release. The connector cannot mint approvals. Writes use an expected-revision check so Claude and ChatGPT cannot silently overwrite one another. Tool declarations describe side effects; Python enforces permissions independently of those declarations.

MCP inputs and outputs have schemas, but schemas alone do not establish truth. Validate referenced evidence IDs, allowed repositories, file paths, size limits, expected revisions, and registered check IDs. Reject unsupported actions with a readable error. Persist accepted proposals as structured data even if the assistant also supplies prose.

Example proposal, illustrative rather than an actual diagnosis:

```json
{
  "schema_version": 1,
  "case_id": "case-001",
  "based_on_revision": "rev-003",
  "status": "needs_evidence",
  "summary": "The timeout is reported, but no matching request trace is attached.",
  "evidence_ids": ["ev-001"],
  "missing_evidence": ["Request trace matching the reported failure"],
  "proposed_action": {
    "kind": "collect_evidence",
    "collector_id": "request_trace_excerpt",
    "inputs": {"request_reference": "local-reference-001"}
  },
  "verification": [],
  "approval_required": true
}
```

This collector ID must exist in the registry before the proposal becomes runnable. Missing evidence should produce this kind of useful next step, not another confident but unsupported diagnosis.

## Desktop behavior

Keep all four quadrants as the default workspace with both Print Shop and Night Shift themes. Show the current case, save/share status, and observed assistant activity. Use focused in-window panels for sharing, setup, evidence, and exact proposal review. Cases now lists saved work with sharing and result context; History combines case-linked desktop runs with assistant evidence, proposals, approvals and outcomes. Older unlinked runs remain separate.

State shows evidence origins and pending incoming revisions. Results separates Assistant proposal, Jev assessment, and Verified checks. A proposal opens a concrete diff/check review with Approve and run. Stop cancels active local work; interrupted runs are marked interrupted, not passed. Never replace a dirty editor without resolving the conflict.

## Build sequence and completion checks

### Phase 1 — Shared state and local MCP (P0)

Extract reusable services from the current one-request worker without breaking desktop behavior. Add evidence/proposal contracts, local MCP tools, revision checks, and host instructions. Connect Claude Desktop and Codex individually.

Done when each signed-in assistant can read the same test case, submit schema-valid evidence and a proposal, and see it in Workbench. Invalid evidence references, path traversal, concurrent stale writes, and attempted execution through proposal tools are rejected. Existing saved cases still open.

### Phase 2 — ChatGPT and remote connectivity (P0)

Check actual account capability first. Use ChatGPT's documented private tunnel if available. If unavailable, design an authenticated HTTPS relay with an outbound local bridge; expose only shared cases, never the whole disk. A Claude remote connection can reuse the HTTPS transport. Use case-scoped access, short-lived authorizations, revocation, and no secret values in tool responses.

Done when ChatGPT can complete the same evidence/proposal round trip. Disconnecting the bridge yields a clear offline response. Unauthorized case IDs fail. Authentication and revocation work. This phase is not complete merely because the server runs locally.

### Phase 3 — One real task through verification (P0)

Register a real project check, implement concrete approval and execution records, and finish the selected existing issue in a separate worktree. Establish bounded working directories, argument lists rather than shell strings, timeouts, output limits, and cancellation. Project tests run with the workspace permissions the user grants; a named script is not automatically harmless.

Done when a reviewed change has before/after evidence and appropriate regression results, and a deliberately failing verification cannot be labeled successful. No production publication or merge is implied.

### Phase 4 — Efficiency and broader workflows (P1)

Add saved task templates for debugging, visual inspection, code review, and authorized access checks. Optionally add the managed Codex app-server for launching sessions from Workbench. Consider the separate Claude Code integration only after confirming its supported distribution/authentication arrangement.

Default to one assistant per task. Ask the other for an independent review only when useful. Do not send every task to both assistants and Jev repeatedly.

## Limits and measurement

Proposed starting defaults: one active run, at most three Jev evaluations per run, one assistant proposal revision after feedback, a ten-minute execution deadline, and bounded evidence excerpts. These are product defaults to tune, not provider limits. The host assistant may continue chatting, but our tools enforce their own budgets.

Use deterministic checks before AI when they answer the question. Send evidence references and deltas instead of entire repositories. Cache unchanged Jev evaluations by state, question, instruction, and model identity; invalidate when any changes. Keep the default model alias, but record the returned model version and use a pinned version for controlled comparisons.

Measure time to a verified result, model calls, reported token usage where available, evidence payload size, unsupported claims, invalid proposals, and failed verifications. Display unavailable usage as unavailable. Subscription usage is not zero cost and cannot always be converted into exact per-task dollars.

Before expanding, replay a small set of known resolved cases plus missing-evidence and misleading-log cases. Compare an assistant-only baseline with assistant-plus-Jev. Keep Jev stages that improve decisions or reduce work; remove redundant evaluations. No savings claim until measured.

## Decisions to confirm during implementation

- Which Claude and ChatGPT accounts have the needed connector features and workspace permissions?
- Is local desktop access sufficient initially, or is browser/mobile access essential?
- If a remote endpoint is needed, where should it run and how should users authenticate?
- Which existing issue and test command form the first end-to-end acceptance case?

These do not block designing the shared Python contracts. They do gate configuring the actual connections and enabling real execution.
