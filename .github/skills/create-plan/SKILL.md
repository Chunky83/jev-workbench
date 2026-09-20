---
name: create-plan
description: Create an implementation plan for a non-trivial Jev Workbench change before editing code. Use for features, cross-file refactors, workflow changes, connector changes, or changes that affect QML and C++ boundaries.
---

# Plan a Jev Workbench Change

Before proposing code changes:

1. Read `AGENTS.md`, `PRODUCT.md`, `WORKSPACE.md`, and the relevant implementation files. Inspect the worktree and preserve unrelated or in-progress changes.
2. State the user goal in one sentence.
3. Identify the current behavior and affected user workflow.
4. Identify affected layers:
   - QML presentation
   - C++ presentation/application boundary
   - Domain or connector logic
   - Persistence/workspace state
   - Tests, docs, examples, prompts, instructions, and schemas
5. Produce a plan with small, ordered implementation steps.
6. List files expected to change and why.
7. State non-goals, dependencies, assumptions, and unresolved decisions that could change the approach.
8. Identify compatibility, security, performance, migration, rollback, and UX risks when applicable.
9. Define acceptance criteria and the minimum targeted test commands or manual evidence.
10. Do not modify files until the plan is accepted unless the request explicitly asks for implementation.

## Output format

- Goal
- Non-goals
- Current behavior
- Proposed approach
- Files and responsibilities
- Implementation steps
- Dependencies, assumptions, and unresolved decisions
- UX considerations
- Risks and mitigations
- Acceptance criteria
- Validation plan
