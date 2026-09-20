"""The four fictional worlds use exact proposal inputs and fixed local oracles."""

import asyncio
import os
from pathlib import Path
import sys
import tempfile
import unittest

from jev_diagnostics.case_store import load_case, save_case, validate_case
from jev_diagnostics.connectors.tool_handlers import Tools
from jev_diagnostics.workflow import library
from jev_diagnostics.workflow.approvals import approve_and_run
from jev_diagnostics.workflow.state_service import share
from jev_diagnostics.workflow.storage import Store
from jev_diagnostics.workflow.story_worlds import (
    WORLD_RUNNERS,
    create_saved_case,
    load,
    run_fixture,
    workbench_case,
)


def proposal_values(world_id):
    case, oracle = load(world_id, include_oracle=True)
    rationale = [{
        "card_id": card["id"],
        "evidence": [card["facts"][0]],
        "summary": "The proposed decision uses only this supplied fictional fact.",
    } for card in case["cards"]]
    return oracle["expected_decisions"], rationale


class StoryWorldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def shared_world(self, world_id):
        folder = self.root / world_id
        snapshot = workbench_case(world_id)
        save_case(folder, snapshot)
        database = self.root / (world_id + ".sqlite3")
        store = Store(database)
        case = share(store, folder, ["claude"])
        return store, case, Tools(database, "claude")

    def submit(self, world_id, decisions=None, rationale=None):
        store, case, tools = self.shared_world(world_id)
        evidence = tools.call("submit_evidence", {
            "case_id": case["case_id"],
            "expected_revision": case["revision"],
            "content": "Assistant-selected fictional card facts; not independently verified.",
            "origin": "Story-world protocol test",
        })
        expected, expected_rationale = proposal_values(world_id)
        result = tools.call("submit_proposal", {
            "case_id": case["case_id"],
            "expected_revision": evidence["revision"],
            "summary": "Check one decision for every fictional story card.",
            "evidence_ids": [evidence["evidence"]["id"]],
            "check_id": WORLD_RUNNERS[world_id],
            "expected_result": "Every decision follows the bundled fictional rulebook.",
            "decisions": expected if decisions is None else decisions,
            "rationale": expected_rationale if rationale is None else rationale,
        })
        return store, case, tools, result

    def test_every_world_round_trips_as_a_version_one_workbench_case(self):
        for world_id, runner_id in WORLD_RUNNERS.items():
            with self.subTest(world_id=world_id):
                case = workbench_case(world_id)
                validate_case(case)
                self.assertEqual(case["runner"], {"check": runner_id, "iterations": 1})
                self.assertEqual(len(case["state"]["story_world"]["cards"]), 5)
                self.assertEqual(len(case["primitives"]), 5)
                folder = self.root / (world_id + "-saved")
                save_case(folder, case)
                self.assertEqual(load_case(folder), case)

    def test_desktop_creation_reuses_each_saved_world_without_sharing_it(self):
        store = Store(self.root / "workflow.sqlite3")
        first = create_saved_case(store, "astral-post-office")
        second = create_saved_case(store, "astral-post-office")
        self.assertEqual(first, second)
        self.assertEqual(first["case"]["runner"]["check"], "astral_post_office_fixture")
        with store.transaction() as db:
            row = db.execute("SELECT payload FROM cases").fetchone()
            self.assertIsNotNone(row)
            self.assertNotIn("claude", row["payload"])

    def test_opening_a_bundled_world_never_overwrites_an_edited_saved_copy(self):
        store = Store(self.root / "workflow.sqlite3")
        original = create_saved_case(store, "lantern-room")
        edited = dict(original["case"], instructions="My saved variation")
        save_case(original["folder"], edited)
        reopened = create_saved_case(store, "lantern-room")
        reopened_again = create_saved_case(store, "lantern-room")
        self.assertNotEqual(reopened["folder"], original["folder"])
        self.assertEqual(reopened_again, reopened)
        self.assertEqual(load_case(original["folder"])["instructions"], "My saved variation")
        self.assertEqual(reopened["case"], workbench_case("lantern-room"))
        with store.transaction() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM cases").fetchone()[0], 2)
        folders = [path for path in (self.root / "story-worlds").iterdir() if path.is_dir()]
        self.assertEqual(len(folders), 2)

    def test_opening_a_world_does_not_reuse_an_archived_pristine_copy(self):
        store = Store(self.root / "workflow.sqlite3")
        original = create_saved_case(store, "lantern-room")
        save_case(original["folder"], dict(original["case"], instructions="My saved variation"))
        archived = create_saved_case(store, "lantern-room")
        with store.transaction() as db:
            archived_id = db.execute("SELECT id FROM cases WHERE source=?",
                                     (archived["folder"],)).fetchone()["id"]
        library.set_archived(store, archived_id, True)

        active = create_saved_case(store, "lantern-room")

        self.assertNotEqual(active["folder"], archived["folder"])
        self.assertEqual(create_saved_case(store, "lantern-room"), active)
        with store.transaction() as db:
            active_id = db.execute("SELECT id FROM cases WHERE source=?",
                                   (active["folder"],)).fetchone()["id"]
            self.assertFalse(library.metadata(db, active_id).get("archived"))
            self.assertEqual(db.execute("SELECT count(*) FROM cases").fetchone()[0], 3)

    def test_exact_story_proposal_runs_only_after_desktop_approval(self):
        store, case, tools, result = self.submit("lantern-room")
        self.assertEqual(tools.call("read_case", {"case_id": case["case_id"]})["recent_runs"], [])
        outcome = approve_and_run(store, case["case_id"], result["revision"],
                                  result["proposal"]["id"], result["proposal_hash"])
        self.assertEqual(outcome["verification"]["status"], "passed")
        self.assertEqual(len(outcome["verification"]["assertions"]), 5)
        self.assertTrue(all(item["passed"] for item in outcome["checks"]["observations"]))
        history = library.timeline(store, case["case_id"])["events"]
        run = next(item for item in history if item["kind"] == "assistant_check")
        self.assertIn("The Lantern Room", run["summary"])
        self.assertNotIn("guest-access", run["summary"])

    def test_wrong_decision_is_preserved_as_a_failed_fixture_result(self):
        expected, rationale = proposal_values("museum-of-tiny-planets")
        wrong = dict(expected)
        wrong["pollen-six"] = "observe_before_cataloging"
        store, case, unused_tools, result = self.submit(
            "museum-of-tiny-planets", decisions=wrong, rationale=rationale)
        outcome = approve_and_run(store, case["case_id"], result["revision"],
                                  result["proposal"]["id"], result["proposal_hash"])
        self.assertEqual(outcome["verification"]["status"], "failed")
        failed = [item for item in outcome["checks"]["observations"] if not item["passed"]]
        self.assertEqual([item["id"] for item in failed], ["pollen-six"])

    def test_fixture_digest_prevents_rules_changing_after_review(self):
        unused_store, unused_case, unused_tools, result = self.submit("lantern-room")
        changed = dict(result["proposal"]["inputs"], fixture_digest="changed-after-review")
        with self.assertRaises(ValueError):
            run_fixture("lantern_room_fixture", changed)

    def test_incomplete_or_mismatched_story_inputs_are_rejected_without_a_run(self):
        store, case, tools = self.shared_world("pocket-weather-bureau")
        evidence = tools.call("submit_evidence", {
            "case_id": case["case_id"], "expected_revision": case["revision"],
            "content": "Selected fictional facts.", "origin": "test"})
        expected, rationale = proposal_values("pocket-weather-bureau")
        del expected["bell-tower"]
        common = {
            "case_id": case["case_id"], "expected_revision": evidence["revision"],
            "summary": "Incomplete decision set", "evidence_ids": [evidence["evidence"]["id"]],
            "check_id": "pocket_weather_bureau_fixture", "expected_result": "No claim",
            "decisions": expected, "rationale": rationale,
        }
        with self.assertRaises(ValueError):
            tools.call("submit_proposal", common)
        complete, valid_rationale = proposal_values("pocket-weather-bureau")
        invented = [dict(item, evidence=list(item["evidence"])) for item in valid_rationale]
        invented[0]["evidence"] = ["Invented sensor reading"]
        common.update(decisions=complete, rationale=invented)
        with self.assertRaises(ValueError):
            tools.call("submit_proposal", common)
        with store.transaction() as db:
            self.assertEqual(store.records(db, case["case_id"], "run"), [])

        guest_folder = self.root / "guest"
        from test_workbench import sample
        save_case(guest_folder, sample())
        guest = share(store, guest_folder, ["claude"])
        guest_evidence = tools.call("submit_evidence", {
            "case_id": guest["case_id"], "expected_revision": guest["revision"],
            "content": "Not a story world.", "origin": "test"})
        common.update(case_id=guest["case_id"], expected_revision=guest_evidence["revision"],
                      evidence_ids=[guest_evidence["evidence"]["id"]])
        with self.assertRaises(ValueError):
            tools.call("submit_proposal", common)

    def test_story_proposal_round_trips_through_the_real_mcp_protocol(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        store, case, unused_tools = self.shared_world("astral-post-office")
        decisions, rationale = proposal_values("astral-post-office")

        async def round_trip():
            parameters = StdioServerParameters(
                command=os.environ.get("JEV_MCP_TEST_PYTHON", sys.executable),
                args=["-m", "jev_diagnostics.connectors.mcp_server", "--database",
                      str(store.path), "--host", "claude"],
                env={"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
            )
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    evidence = await session.call_tool("submit_evidence", {
                        "case_id": case["case_id"], "expected_revision": case["revision"],
                        "content": "Selected fictional facts.", "origin": "MCP story test"})
                    self.assertFalse(evidence.isError)
                    submitted = await session.call_tool("submit_proposal", {
                        "case_id": case["case_id"],
                        "expected_revision": evidence.structuredContent["revision"],
                        "summary": "Sort every fictional letter.",
                        "evidence_ids": [evidence.structuredContent["evidence"]["id"]],
                        "check_id": "astral_post_office_fixture",
                        "expected_result": "Every letter follows the fictional rulebook.",
                        "decisions": decisions,
                        "rationale": rationale,
                    })
                    self.assertFalse(submitted.isError)
                    return submitted.structuredContent

        submitted = asyncio.run(round_trip())
        outcome = approve_and_run(store, case["case_id"], submitted["revision"],
                                  submitted["proposal"]["id"], submitted["proposal_hash"])
        self.assertEqual(outcome["verification"]["status"], "passed")


if __name__ == "__main__":
    unittest.main()
