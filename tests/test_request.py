import unittest
from pathlib import Path

from jev_diagnostics.diagnosis import build_request
from jev_diagnostics.evidence import load_evidence


class RequestTests(unittest.TestCase):
    def test_example_builds_three_choice_questions(self) -> None:
        repository_root = Path(__file__).resolve().parents[1]
        diagnostic_state = load_evidence(repository_root / "examples" / "demo_timeout.json")

        request_body = build_request(diagnostic_state)

        self.assertEqual(request_body["model"], "jev-latest")
        self.assertEqual(set(request_body["questions"]), {"subsystem", "next_check", "evidence"})
        self.assertTrue(
            all(question["type"] == "choice" for question in request_body["questions"].values())
        )
        self.assertEqual(request_body["state"]["environment"], "test")


if __name__ == "__main__":
    unittest.main()
