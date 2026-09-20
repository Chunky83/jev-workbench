# Jev Workbench 0.1.0 local connector preview

This preview supports a local desktop workflow. Its source is public; saved cases,
client settings, and credentials remain local. Connection setup and execution
require explicit approval.

## Guided preview

Launch the current packaged executable with `--local-preview`; see [the workspace map](../WORKSPACE.md).
Keep the package in place after connecting: the connection uses its runtime location.
The preview uses a separate application data/settings namespace from the regular launch.

For an account-free sample, choose **Try a sample** on the overview. Workbench saves the
sample automatically and opens the review. Approve the synthetic check once, then open
its results. This does not connect an assistant or test a real project.

For Claude on Windows:

1. Choose **Connect assistants**. Workbench checks conventional and Microsoft Store profiles.
2. Select the profile if more than one appears. Choose **Review setup**.
3. Read the change summary and target, then choose **Approve setup**. Existing settings are
   preserved and a backup is created. No case is shared by setup.
4. Quit and reopen Claude when ready. Ask it to list your Jev Workbench cases, then select
   **Check connection** here. The app reports successful tool activity with its timestamp;
   it does not verify account identity or claim a live connection from saved settings.
5. Use the sample or save a test. Select Claude and choose **Share saved snapshot**.
6. Ask Claude to read the case, submit evidence and propose a `guest_access_fixture` check.
   Workbench automatically shows the proposal in **Inbox**, even if another case is open. Choose **Review proposal**, inspect its scope, then approve it to run. The result appears in the same review.

Unsaved editor changes are never shared. Incoming state is a proposal: accepting it changes
the editor; save and share again to update the assistant's snapshot. Previous proposals and
results stay in history. A new run requires a new proposal. Revocation removes case access.

Advanced options contain the manual launch configuration, TypeSafe allowance and explicit
undo for the last applied Claude setup. Undo stops if Claude settings changed afterwards.
Close/cancel never grants setup approval. No passwords, session tokens or provider inference
keys are needed for local Claude setup.

## Supported connection setup

The Python transport uses the official MCP SDK (`mcp` 1.30.0 tested), stdio, seven typed tools,
generated input/output schemas and side-effect annotations. No OpenAI or Anthropic inference
API key or copied session token is used. Signing into a provider remains the client's job.

Claude Desktop on Windows: use the guided automatic setup above. Standard and Microsoft
Store profiles are supported. Workbench preserves unrelated configuration values, rejects
malformed/duplicate-key settings, expires reviews after 15 minutes and rejects changes made
after review. Other platforms remain manual. Backups stay beside the client configuration;
they may contain that client's existing credentials and must not be exported as diagnostics.

ChatGPT: official documentation supports Secure MCP Tunnel to a private stdio or HTTP MCP
server. Developer mode and tunnel availability depend on the account/workspace. Use the
displayed `chatgpt` launch configuration as the local stdio target with the official tunnel
client. Associate the tunnel with the correct ChatGPT workspace, then select it when adding
the MCP connection. Tunnel setup is not performed by this build. No public unauthenticated
listener or token-copying workaround is supplied. If a tunnel is unavailable, an authenticated
HTTPS relay remains future work requiring an explicit hosting/authentication decision.

Codex: the same stdio server can be configured in the signed-in Codex client with the `codex`
host label. This preview does not embed an assistant inference session in the desktop.

Configuration and historical successful tool activity are displayed separately.
Provider account identity remains **unverified**. A Windows Claude proposal, approval,
and result readback has been checked in the client; see [result handoff](result-handoff.md).
ChatGPT account-side validation remains outstanding.

## Jev budget and credentials

Each saved shared snapshot starts with zero Jev calls. Set an additional allowance of 0–3
in Connections. Each `evaluate_case` consumes a call before requesting TypeSafe, including
failures; there is no automatic retry. It evaluates the saved shared snapshot, not pending
assistant state. The server reads `TYPESAFE_API_KEY` from its own process environment.
A key entered into the desktop's session-only key field is not transferred to an independently
launched MCP process. Do not put credentials in source, cases, evidence or connector config.

## Storage and trust boundaries

Existing schema-version-1 case folders remain unchanged. The explicitly separate workflow
schema is version 1, stored in `workflow-v1.sqlite3` in the application data directory shown
by Connections. This is a transactional SQLite sidecar, rather than silently migrating
existing case manifests. Snapshots are copied only by an explicit share action. Evidence,
state proposals, check proposals, approvals, run inputs and outcomes are append-only records
with SHA-256 integrity checks. New evidence advances the workflow revision; stale writes
fail across concurrent clients. Proposals cannot grant approvals. Approval binds the exact
proposal hash and revision and is consumed once. Revocation invalidates pending proposals.

The preview caps incoming records at 20 per kind per case and permits one workflow run at a time.
An incomplete run blocks another run until resolved in the owning client.

This is a same-user local trust boundary, not a sandbox against other processes running as
the same Windows user. Local database writers could alter both a record and its hash.
Keep the database private and outside source control. Excerpts are not automatically redacted.
Assistant observations are explicitly unverified, regardless of their text or reported origin.

## Current limits

Only the existing synthetic HTTP fixture is registered. No arbitrary shell, project command,
patch application, collectors, external URL scanner or real issue verification is implemented.
A real diagnostic scenario remains to be defined. A failing fixture cannot be labeled passed.
Stop records an interrupted outcome; an abrupt application crash may leave an incomplete
run, which is never treated as passed. ChatGPT tunnel authentication and account-side
revocation tests remain outstanding.

macOS remains manual-only and Apple Silicon-only. The existing PyInstaller single executable
and `-appstore-compliant` packaging fix are retained. This Windows session does not validate
a macOS build. Apple Developer ID signing, notarization and a simple Releases download are
backlog items only; see TASKS.md.

## Validation

Run `.venv/Scripts/python -m unittest discover -s tests` with `PYTHONPATH=src` after
installing the `connectors` extra. Contract tests cover sharing, traversal, stale writes,
concurrent writers, evidence integrity, dirty-state isolation, unsupported execution,
concrete approval, replay, revoked access, budgets, failed assertions and SDK stdio calls.
Native `--smoke-test` and `--ui-smoke --theme Light|Dark` checks cover desktop behavior.

Official references verified September 19, 2026:

- https://developers.openai.com/plugins/deploy/connect-chatgpt
- https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
- https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp
- https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop
- https://github.com/modelcontextprotocol/python-sdk
