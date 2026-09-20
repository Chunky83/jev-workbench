# Jev Workbench

## Register

product

## Users and purpose

People who want to use Jev in a simplified desktop environment use the workbench to learn Jev, collect evidence, edit bounded questions, and repeat diagnostic tests. Save and reload ordinary files without terminal command juggling.

## Design direction

Approved Print Shop neubrutalist style with Test Bench comparisons. Night Shift dark mode is required alongside light mode, including all controls. Four resizable editor quadrants: State, Primitives, Instructions, Results. Bottom taskbar offers Actions, Preview, and Run.

## Principles

- C++ and Qt/QML own the desktop. Python owns all AI and test execution.
- Separate editable JSON state and primitives from plain-language instructions.
- Model judgments and verified test assertions stay visibly distinct.
- Keys never enter saved cases or run records.
- Make invalid input and missing evidence understandable.
- No automatic model-selected execution; no regular expressions.

## Accessibility

Keyboard controls, visible focus, high-contrast text, text alongside status colors, no decorative motion. The user works at a desktop in both daylight and evening, so light and dark themes are equally supported.

## Desktop workflow

The four quadrants are the primary workspace. Keep the case name, save status,
sharing state, and next action visible. Use focused in-window panels for sharing,
assistant setup, evidence, proposal review, and diagnostics. Setup instructions
must not stand between an already configured assistant and case sharing.

Discover supported profiles automatically; require a scoped review and approval
before changing external settings. Distinguish saved configuration, observed tool
activity, account identity, and case sharing. Automatically surface proposals and
results without replacing unsaved editor content. Every blocked or completed
action needs an explanation and a useful next step.

Saved cases are selected from a readable catalogue. Case history combines
assistant proposals, approvals, observed sample checks, and Jev assessments while
keeping their meanings distinct. Reuse samples by default; creating another one
is explicit. Archive retains files and history and revokes sharing; restore does
not reconnect assistants. Never infer case ownership from a repeated title.
