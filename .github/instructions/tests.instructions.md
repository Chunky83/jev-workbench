---
applyTo: "tests/**,test-kits/**"
---

# Test conventions

- Keep tests deterministic, local, and readable. Use temporary directories and synthetic fixtures; do not require real credentials, customer data, live accounts, or production services.
- Test observable contracts and safety invariants rather than implementation wording. Include failure, invalid-input, stale-revision, interruption, or permission cases when the changed behavior has them.
- Preserve the distinction between an assistant proposal, a Jev hypothesis, and independently verified evidence. A confidence value or successful model call is not proof that a check passed.
- Do not weaken assertions merely to accept a changed implementation. If intended behavior changes, make the new expectation and its reason clear.
- Add a focused regression test close to the affected module. Run that test while iterating, then run the broader affected suite before completion.
- Keep offline test-kit claims scoped to their fixtures. Do not describe them as validation of a real repository, website, account, or customer incident.
