"""Meaningful boundaries: persistence, protocol, response validation, and real checks."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jev_diagnostics.case_store import load_case, save_case
from jev_diagnostics.local_checks import run_guest_fixture
from jev_diagnostics.workbench_request import build_workbench_request, validate_response
from jev_diagnostics.worker import dispatch


def sample():
    return {"schema_version": 1, "title": "Guest access", "model": "jev-1.13.0",
            "state": {"observations": [{"id": "E001", "status": 401}]},
            "instructions": "Use only supplied evidence.",
            "primitives": {"outcome": {"type": "choice", "instructions": "Was access denied?",
                                      "criteria": {"yes": "Denied", "no": "Allowed"}}}}


class WorkbenchTests(unittest.TestCase):
    def test_save_open_and_failed_save_preserve_previous_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            original = sample()
            save_case(directory, original)
            self.assertEqual(load_case(directory), original)
            changed = sample()
            changed["title"] = "Edited title"
            with patch("jev_diagnostics.case_store.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    save_case(directory, changed)
            self.assertEqual(load_case(directory), original)

    def test_case_cannot_reference_files_outside_folder(self):
        with tempfile.TemporaryDirectory() as directory:
            save_case(directory, sample())
            path = Path(directory) / "test.json"
            manifest = json.loads(path.read_text())
            manifest["revision"] = "../outside"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                load_case(directory)

    def test_all_three_primitives_share_common_rules(self):
        case = sample()
        case["primitives"].update({
            "complete": {"type": "noul", "instructions": "Is evidence complete?"},
            "quality": {"type": "score", "instructions": "Rate evidence.", "criteria": ["Absent", "Complete"]}})
        request = build_workbench_request(case["state"], case["primitives"], case["instructions"], case["model"])
        self.assertEqual(len(request["questions"]), 3)
        for question in request["questions"].values():
            self.assertTrue(question["instructions"].startswith(case["instructions"]))

    def test_invalid_confidence_distribution_and_missing_answers_rejected(self):
        question = sample()["primitives"]
        answer = {"type": "choice", "choice": "yes", "confidence": 0.8,
                  "probabilities": {"yes": 0.9, "no": 0.1}}
        response = {"model": "jev-1.13.0", "answers": {"outcome": answer},
                    "usage": {"input_tokens": 42, "output_tokens": 0}}
        validate_response(response, question)
        for bad in (True, float("nan"), 1.2):
            answer["confidence"] = bad
            with self.assertRaises(ValueError):
                validate_response(response, question)
        answer["confidence"] = 0.8
        answer["probabilities"]["no"] = 0.8
        with self.assertRaises(ValueError):
            validate_response(response, question)
        response["answers"] = {}
        with self.assertRaises(ValueError):
            validate_response(response, question)

    def test_offline_fixture_checks_status_and_protected_content(self):
        checks = run_guest_fixture()
        self.assertTrue(checks["passed"])
        self.assertFalse(checks["observations"][0]["protected_content_present"])
        self.assertTrue(checks["observations"][1]["protected_content_present"])

    def test_bounded_loop_and_runner_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            case = sample()
            case["runner"] = {"check": "guest_access_fixture", "iterations": 3}
            save_case(Path(directory) / "case", case)
            self.assertEqual(load_case(Path(directory) / "case"), case)
            result = dispatch({"action": "run", "case": case, "mode": "local", "runs_folder": directory})["result"]
            self.assertEqual(len(result["iterations"]), 3)
            case["runner"]["iterations"] = 100
            with self.assertRaises(ValueError):
                save_case(Path(directory) / "invalid", case)

    def test_live_run_records_inputs_but_never_key(self):
        with tempfile.TemporaryDirectory() as directory:
            response = {"model": "jev-1.13.0", "answers": {"outcome": {
                "type": "choice", "choice": "yes", "confidence": 0.8,
                "probabilities": {"yes": 0.9, "no": 0.1}}}, "usage": {"input_tokens": 42, "output_tokens": 0}}
            with patch("jev_diagnostics.worker.submit_request", return_value=response) as submit:
                result = dispatch({"action": "run", "case": sample(), "mode": "live",
                                   "api_key": "synthetic-secret", "runs_folder": directory})["result"]
            submit.assert_called_once()
            self.assertEqual(result["status"], "completed")
            self.assertEqual(result["verification"], "Not performed")
            for path in Path(directory).glob("*/*"):
                self.assertNotIn("synthetic-secret", path.read_text())

    def test_failed_live_run_is_preserved_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("jev_diagnostics.worker.submit_request", side_effect=RuntimeError("HTTP 429")) as submit:
                result = dispatch({"action": "run", "case": sample(), "mode": "live",
                                   "api_key": "synthetic-secret", "runs_folder": directory})["result"]
            submit.assert_called_once()
            self.assertEqual(result["status"], "failed")
            self.assertTrue((Path(result["folder"]) / "result.json").exists())


if __name__ == "__main__":
    unittest.main()
