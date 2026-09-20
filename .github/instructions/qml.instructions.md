---
applyTo: "desktop/**/*.qml"
---

# QML conventions

- Keep QML responsible for presentation, interaction state, accessibility metadata, and calls into the `Workbench` Qt object. Do not add filesystem, process, network, connector, or Jev API behavior to QML.
- Use the shared `root.colors` palette and existing reusable controls. Every change must remain legible and operable in Light, Night Shift, and System modes.
- Preserve keyboard operation, visible focus, text labels alongside color, and the no-decorative-motion accessibility direction in `PRODUCT.md`.
- Keep user-visible states honest: distinguish proposals, Jev hypotheses, observed checks, failures, interruptions, and unavailable verification.
- Make blocked and completed states explain what happened and offer a useful next step. Do not silently discard dirty editor content.
- Keep JavaScript in QML limited to view composition and simple presentation transformations. Move validation or workflow decisions to C++ or Python according to the repository boundary.
- For interaction changes, run the relevant UI smoke path in both Light and Dark when the local Qt environment is available. If it is unavailable, state that limitation.
