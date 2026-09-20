---
name: test-first-change
description: Implement a Jev Workbench change with an automatable behavior contract by first capturing it in a focused regression test, then making the smallest compatible change and running affected checks. Use for testable bug fixes and behavior changes; not for documentation-only work or purely visual, packaging, or platform behavior without a stable automated boundary.
---

# Test-First Change

Use tests to define observable behavior and safety invariants, not private implementation details or exact incidental wording.

If the behavior cannot be exercised reliably in automation, define the manual acceptance evidence before implementation instead of inventing a brittle test. Examples include visual-only QML adjustments, installer behavior, signing, notarization, and device-specific validation.

## Workflow

1. Locate the narrowest existing test module and the public boundary that demonstrates the requested behavior. If no stable automated boundary exists, record why and use a concrete manual validation plan.
2. Add or adjust a focused test that fails for the right reason before changing production code. Use synthetic data and temporary directories; never require real secrets, accounts, customer identifiers, or production services.
3. Cover the relevant negative path when the behavior involves invalid input, stale revisions, permissions, cancellation, interruption, or missing evidence.
4. Implement the smallest readable change while preserving module separation and persisted-format compatibility. Do not use regular expressions.
5. Run the focused test until it passes, then run the broader affected test module or suite. Use the full Python suite when shared workflow, connector, storage, or request behavior changes.
6. For QML/C++ changes, also run the relevant native or UI smoke path when the environment permits. For package behavior, test the packaged runtime rather than inferring it from development tests.

Report the contract captured by the test or manual acceptance evidence, the implementation result, and the exact checks run. Do not weaken a safety assertion to make the change pass, and do not claim unrun platform coverage.
