# Repository instructions

- Keep the program readable for a developer who is learning Jev.
- Do not use regular expressions.
- Preserve the architecture boundary: QML presents the interface, C++ owns the Qt/desktop boundary, and Python owns Jev requests, connectors, workflow state, validation, execution, and reporting.
- Keep state, primitives, instructions, API-key loading, API access, and reporting in separate modules.
- Treat Jev results as hypotheses until independent evidence verifies them.
- Never store API keys, authorization headers, cookies, or customer identifiers in source control.
- Do not execute a model-selected action automatically.
- Do not change CMake, packaging, dependencies, schemas, or persisted formats unless the requested behavior requires it. Explain compatibility or migration effects when it does.
- Run the smallest relevant checks while developing, then run the broader affected suite before declaring the work complete. Do not describe synthetic fixtures as proof about a real repository, website, account, or customer incident.
