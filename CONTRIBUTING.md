# Contributing to Jev Workbench

Jev Workbench is an independently maintained hobby project. Bug reports,
feature ideas, and pull requests are welcome, but review or acceptance is not
guaranteed and no response schedule is promised.

## Before opening an issue

- Search existing issues before creating a new one.
- Remove API keys, authorization data, customer identifiers, private files,
  local paths, and unrelated personal information.
- Report suspected vulnerabilities through the private process in
  [SECURITY.md](.github/SECURITY.md), not through a public issue.
- Treat Jev results as hypotheses unless independent evidence verifies them.

## Pull requests

Keep changes focused and explain the user problem, the proposed behavior, and
how the change was tested. New behavior should include tests when practical.
All automated checks must pass before a change can be considered.

Do not add secrets, private data, generated build output, or dependencies that
are not needed. Do not add a path that automatically executes a model-selected
action. Preserve the separation between state, primitives, instructions,
API-key loading, API access, and reporting. Keep the implementation readable
for developers who are learning Jev, and do not use regular expressions.

You must have the right to submit the contribution. By submitting it, you agree
that it may be distributed under the repository's MIT License. Review any
AI-assisted work yourself and submit only changes you understand and can
support.

## Review and merging

Submitting a contribution does not grant repository access. The maintainer
decides whether and when to merge a change. Sensitive areas, including GitHub
workflows, connector boundaries, packaging, and security policy, require owner
review.
