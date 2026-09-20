import unittest
import json
import tempfile
from pathlib import Path
from jev_diagnostics.evidence import load_evidence

from jev_diagnostics.state import (
    DiagnosticState,
    IssueReference,
    VerifiedObservation,
)


class DiagnosticStateTests(unittest.TestCase):
    def test_saved_diagnostic_state_can_be_loaded_again(self):
        original = load_evidence(Path(__file__).parent.parent / "examples" / "demo_timeout.json")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evidence.json"
            path.write_text(json.dumps(original.to_dictionary()), encoding="utf-8")
            self.assertEqual(load_evidence(path), original)

    def test_requires_verified_observation(self) -> None:
        diagnostic_state = DiagnosticState(
            issue=IssueReference(number=1, title="Example", url="https://example.com"),
            environment="local",
            service="backend",
            reported_behavior="The request failed.",
            verified_observations=(),
            unverified_claims=(),
            source_locations=(),
        )

        with self.assertRaises(ValueError):
            diagnostic_state.validate()

    def test_accepts_clear_verified_evidence(self) -> None:
        diagnostic_state = DiagnosticState(
            issue=IssueReference(number=1, title="Example", url="https://example.com"),
            environment="production",
            service="backend",
            reported_behavior="The request failed.",
            verified_observations=(
                VerifiedObservation(
                    observation_id="E001",
                    source="cloud_log",
                    observed_at="2026-09-19T00:00:00Z",
                    text="The request returned status 500.",
                ),
            ),
            unverified_claims=(),
            source_locations=(),
        )

        diagnostic_state.validate()


if __name__ == "__main__":
    unittest.main()
