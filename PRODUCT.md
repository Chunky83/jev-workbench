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

## Guided desktop workflow (19 September 2026)

Default to a task-first overview: connect an assistant, try a saved-for-you sample, or open
a saved test. Keep the four existing quadrants under Advanced editor. Discover supported
application profiles automatically; require a readable, scoped review before changing
external settings. Distinguish discovered profiles, saved configuration, observed tool
activity, account identity and case sharing. Every blocked or completed action needs an
explanation and a useful next step. See docs/desktop-workflow-review.md for the staged
architecture and explicit remaining work.
