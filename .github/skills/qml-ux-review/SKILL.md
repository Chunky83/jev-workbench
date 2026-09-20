---
name: qml-ux-review
description: Review Jev Workbench QML changes for workflow continuity, interaction quality, accessibility, theme parity, truthful execution feedback, and desktop power-user usability. Use for reviews of QML screens, dialogs, panels, menus, controls, or execution feedback; not for general C++ or Python review.
---

# Review QML UX

Review the change without modifying code unless implementation is explicitly requested. Read `PRODUCT.md` and the relevant workflow in `docs/desktop.md`, then inspect the actual QML and rendered behavior when available.

Evaluate the following:

1. User intent

   - Is the purpose of the screen or control obvious?
   - Is the primary action clear and positioned consistently?
   - Does the user know what object or context is active?

2. Workflow continuity

   - Can the user complete the happy path with minimal unnecessary context switching?
   - Does the UI preserve user context after a run, error, save, or navigation event?
   - Is there an obvious next step after success?

3. State coverage

   - Empty
   - Loading
   - Disabled
   - Validation failure
   - Execution failure
   - Offline or disconnected
   - Permission-limited
   - Canceled or interrupted
   - Verification unavailable
   - Success and completion

4. Desktop usability

   - Keyboard navigation and focus order
   - Keyboard shortcut discoverability
   - Tooltips for unfamiliar icons
   - Resizable panel and layout behavior
   - Suitable density for expert users

5. Accessibility and clarity

   - Do not communicate state by color alone.
   - Ensure labels and status text are understandable without hidden context.
   - Use specific labels rather than generic actions such as "Submit" or "Continue".
   - Error messages must include a recovery action.

6. Visual consistency

   - Reuse project controls and theme behavior.
   - Avoid duplicating spacing, colors, or state logic.
   - Keep advanced controls progressively disclosed.
   - Check legibility and behavior in Light, Night Shift, and System themes.

7. Truthful execution feedback

   - Distinguish assistant proposals, Jev hypotheses, user approval, observed checks, and verified results.
   - Do not imply that a connection works until a real account round trip has been observed.
   - Do not present a synthetic fixture as proof about a real repository, website, account, or customer incident.
   - Treat failed, canceled, interrupted, and unavailable verification as distinct non-success states.

## Output format

For each finding:

- Severity: blocker, high, medium, low, or observation
- Location: file and component
- User impact
- Evidence
- Recommended change
- Suggested acceptance test

If there are no findings, say so and list any themes, states, keyboard paths, or runtime behavior that were not inspected.
