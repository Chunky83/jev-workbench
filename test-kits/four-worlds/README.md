# Jev Workbench Story Worlds

These are original, self-contained test worlds for Jev Workbench. They are
intended to feel like a small invitation into the product instead of a
throwaway technical demo.

Each world has a clear fictional rulebook, a cast, a gentle antagonist, and
five small decisions. That gives an assistant enough room to demonstrate
reasoning, uncertainty, evidence handling, proposal delivery, approval, and a
deterministic result without touching a real project, website, account, or
customer record.

## The four worlds

| World | Story hook | Primary implementation | What it proves |
| --- | --- | --- | --- |
| The Astral Post Office | A star-mail clerk saves a night route from the Address Eater. | Claude Code or another assistant connected to Workbench. | A shared case can travel to an assistant, return as a structured proposal, surface automatically, and run only after approval. |
| The Museum of Tiny Planets | An apprentice curator keeps miniature worlds from drifting out of their stories. | A bare terminal and deterministic code. | JSON inputs and outputs stay clear, repeatable, and easy to inspect without a graphical client. |
| The Lantern Room | A lighthouse keeper separates real calls for help from the Whispering Static. | Evidence-aware connector work. | An assistant can cite supplied facts, keep uncertainty intact, and escalate only the right signals. |
| The Pocket Weather Bureau | A cloud-and-brass apprentice prevents the Barometer Bandit from swapping forecasts. | Terminal work with illustrative picture cards. | Visual cards can make a terminal exercise inviting while structured text stays the source of truth. |

## What is in each world folder

- case.json is the safe snapshot a connected assistant may read.
- oracle.json is the local expected-result fixture. Do not include it in an
  assistant share.
- STORY.md contains the story, cast, visual direction, and the intended
  first-run experience.
- assistant-prompt.md is the concise prompt for a Claude Code or Workbench
  connector test.

The cover art in assets is original illustrative material. It establishes the
visual mood; no test requires vision or OCR. The factual card fields in
case.json remain the authority.

## Terminal preview

The portable terminal runner needs only Python 3. It makes no network calls and
does not write to the repository.

    python test-kits/four-worlds/run_world.py list
    python test-kits/four-worlds/run_world.py story astral-post-office
    python test-kits/four-worlds/run_world.py check astral-post-office --demo

To check an implementation's result, give the runner a JSON file containing a
decisions object:

    python test-kits/four-worlds/run_world.py check lantern-room result.json

The runner reports every individual card and exits with a nonzero status when a
decision is missing, invalid, or wrong.

## Future Workbench connector contract

The current preview only has an unrelated guest-access fixture. These worlds
are deliberately kept as a ready-to-wire pack rather than pretending that they
already run through that fixture.

When the story-world runner is added to Workbench, each case should use a
bounded named fixture and a typed proposal payload:

    {
      "world_id": "astral-post-office",
      "case_version": 1,
      "runner_id": "astral_post_office_fixture",
      "decisions": {
        "violet-envelope": "deliver"
      },
      "rationale": [
        {
          "card_id": "violet-envelope",
          "evidence": ["recipient", "destination"],
          "summary": "One named recipient and one complete destination."
        }
      ]
    }

The local fixture should compare decisions with that world's oracle and report
every card as passed, failed, or incomplete. It should not make a network call,
inspect project files, invoke arbitrary commands, or turn a fictional story
result into a real-world claim.

For the connector experience, a valid incoming proposal should immediately
reveal a single review card in Workbench. The review card needs to show:

1. the assistant's decisions and short evidence citations;
2. the exact named local fixture that would run;
3. the fact that approval is still required; and
4. the result for each story card after the check completes.

This makes the interesting moment visible: the assistant made a suggestion,
you decided whether to run it, and the local fixture showed exactly what
matched the rulebook.
