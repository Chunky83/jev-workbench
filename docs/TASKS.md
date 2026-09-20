# Project task list

Updated September 19, 2026 for the public 0.1.0 baseline.

## Completed

- [x] Validate the Windows Claude proposal, desktop approval, and result round trip.
- [x] Consolidate the four-world test kit under `test-kits/four-worlds`.
- [x] Document the current source layout and portable build commands.

## Next

- [x] Make the four editors primary and separate sharing, setup, and review into focused in-window panels.
- [x] Unify case selection and case history, with private saved cases, sample reuse and reversible archive.
- [ ] Validate the simplified workflow with a first-time user.
- [ ] Test ChatGPT account-side setup and its complete proposal/result workflow.
- [x] Connect the four-world fixtures to typed assistant proposals, explicit desktop approval, and fixed offline verification.
- [ ] Validate the Apple Silicon package on a real Mac: first launch, local checks, saved cases, and both themes.
- [ ] Define a real diagnostic scenario and independently verifiable success criteria.
- [ ] Add Apple Developer ID signing and notarization when a signing setup is available. Keep credentials out of source control and saved cases.
- [ ] Publish tested packages with release notes and checksums.
- [ ] Keep Mac builds manual-only and Apple Silicon-only.

## Case selection and history

Implemented locally: saved-case chooser, case-linked desktop runs, combined case
history, sample reuse/explicit new sample, and reversible archive with sharing
revoked. History reads preserve drafts and cannot execute work. Saved files and
prior run records remain compatible. Older unlinked runs remain separate.

Validation: focused service tests cover duplicate names, private registration,
shared snapshot preservation, archive/restore, old-case compatibility, failed Jev
records, tamper rejection, and exact approval invalidation. Native walkthroughs
cover editor preservation and the case/history controls in both themes. A fresh
signed-in assistant and first-use usability walkthrough remain due.

## Four story worlds

Implemented locally: each bundled world opens as a private saved Workbench case,
uses its own registered runner ID, and requires a complete decisions object plus
one bounded rationale per card. Assistant submission cannot execute a fixture.
The desktop review binds approval to the exact proposal hash and case revision;
the local oracle then reports every fictional card as passed or failed. Edited
story fixtures are rejected instead of being compared with a mismatched oracle.

Validation covers all four case conversions, save/load compatibility, invalid
and mismatched proposals, passing and failing oracle results, a real MCP stdio
round trip, the native build, and the desktop worker smoke path. A fresh
signed-in assistant walkthrough remains due and must not be described as proven
by these synthetic fixtures.
