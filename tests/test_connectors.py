"""Permission, integrity, concurrency, approval and real stdio protocol boundaries."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from jev_diagnostics.case_store import save_case, load_case
from jev_diagnostics.connectors.tool_handlers import Tools
from jev_diagnostics.workflow.storage import Store, digest
from jev_diagnostics.workflow.state_service import share
from jev_diagnostics.workflow.desktop_service import dispatch
from jev_diagnostics.workflow.approvals import approve_and_run, interrupt
from jev_diagnostics.workflow.verification import classify
from test_workbench import sample

class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'case'
        save_case(self.folder, sample())
        self.database = self.root / 'workflow-v1.sqlite3'
        self.store = Store(self.database)
        self.case = share(self.store, self.folder, ['claude', 'chatgpt'])
        self.tools = Tools(self.database, 'claude')

    def args(self):
        return {'case_id': self.case['case_id'], 'expected_revision': self.case['revision']}

    def evidence(self):
        result = self.tools.call('submit_evidence', dict(self.args(), content='Reported HTTP 401; assistant observation only.', origin='Synthetic protocol test'))
        self.case['revision'] = result['revision']
        return result['evidence']['id']

    def proposal(self):
        evidence_id = self.evidence()
        result = self.tools.call('submit_proposal', dict(self.args(), evidence_ids=[evidence_id], summary='Check the synthetic fixture', check_id='guest_access_fixture', expected_result='Guest denied; owner permitted.'))
        self.case['revision'] = result['revision']
        return result

    def test_explicit_sharing_and_path_rejection(self):
        self.assertEqual(Tools(self.database, 'codex').call('list_cases', {})['cases'], [])
        for case_id in (self.case['case_id'], '../outside', str(self.root.resolve() / 'outside')):
            with self.assertRaises(ValueError):
                Tools(self.database, 'codex').call('read_case', {'case_id': case_id})
        output = json.dumps(self.tools.call('read_case', {'case_id': self.case['case_id']}))
        self.assertNotIn(str(self.folder), output)

    def test_stale_and_missing_revision_are_rejected(self):
        old = self.args()
        self.evidence()
        for args in (old, {'case_id': self.case['case_id']}):
            with self.assertRaises(ValueError):
                self.tools.call('submit_evidence', dict(args, content='Second observation', origin='test'))

    def test_two_concurrent_writes_only_one_wins(self):
        args = dict(self.args(), content='Concurrent excerpt', origin='test')
        def submit():
            try:
                self.tools.call('submit_evidence', args)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(sorted(results), [False, True])

    def test_evidence_bounds_and_unknown_references(self):
        with self.assertRaises(ValueError):
            self.tools.call('submit_evidence', dict(self.args(), content='x' * 16001, origin='test'))
        with self.assertRaises(ValueError):
            self.tools.call('propose_state', dict(self.args(), state={}, evidence_ids=['evidence-unknown']))

    def test_evidence_tampering_is_detected(self):
        evidence_id = self.evidence()
        with self.store.transaction() as db:
            db.execute('UPDATE records SET payload=? WHERE id=?', ('{}', evidence_id))
        with self.assertRaises(ValueError):
            self.tools.call('read_case', {'case_id': self.case['case_id']})

    def test_proposed_state_never_overwrites_saved_case(self):
        evidence_id = self.evidence()
        self.tools.call('propose_state', dict(self.args(), state={'hypothesis': 'unverified'}, evidence_ids=[evidence_id]))
        self.assertEqual(load_case(self.folder), sample())
        self.assertEqual(self.tools.call('read_case', {'case_id': self.case['case_id']})['case']['snapshot'], sample())

    def test_unsupported_execution_and_check_are_rejected(self):
        for name in ('execute', 'approve', 'approve_and_run', 'share', 'budget'):
            with self.assertRaises(ValueError):
                self.tools.call(name, self.args())
        evidence_id = self.evidence()
        with self.assertRaises(ValueError):
            self.tools.call('submit_proposal', dict(self.args(), evidence_ids=[evidence_id], summary='Run arbitrary command', check_id='shell', expected_result='passed'))

    def test_approval_hash_revision_and_replay(self):
        result = self.proposal()
        proposal = result['proposal']
        with self.assertRaises(ValueError):
            approve_and_run(self.store, self.case['case_id'], self.case['revision'], proposal['id'], 'wrong-hash')
        outcome = approve_and_run(self.store, self.case['case_id'], self.case['revision'], proposal['id'], result['proposal_hash'])
        self.assertEqual(outcome['verification']['status'], 'passed')
        self.assertIn('Synthetic', outcome['verification']['scope'])
        with self.assertRaises(ValueError):
            approve_and_run(self.store, self.case['case_id'], self.case['revision'], proposal['id'], result['proposal_hash'])
        read = self.tools.call('read_run', {'case_id': self.case['case_id'], 'run_id': outcome['run_id']})
        self.assertEqual(read['outcome']['status'], 'completed')

    def test_completed_runs_are_discoverable_without_changing_the_case(self):
        proposal = self.proposal()
        before = self.tools.call('read_case', {'case_id': self.case['case_id']})
        self.assertEqual(before['recent_runs'], [])
        outcome = approve_and_run(self.store, self.case['case_id'], self.case['revision'],
                                 proposal['proposal']['id'], proposal['proposal_hash'])
        after = self.tools.call('read_case', {'case_id': self.case['case_id']})
        self.assertEqual(after['case'], before['case'])
        run = after['recent_runs'][0]
        self.assertEqual(run['proposal_id'], proposal['proposal']['id'])
        self.assertEqual(run['run_id'], outcome['run_id'])
        self.assertEqual(run['status'], 'completed')
        self.assertEqual(run['verification']['status'], 'passed')
        read = self.tools.call('read_run', {'case_id': self.case['case_id'], 'run_id': run['run_id']})
        self.assertEqual(read['current'], run)
        self.assertEqual(read['run']['status'], 'running')
        self.assertNotIn(str(self.folder), json.dumps(after))
        with self.assertRaises(ValueError):
            Tools(self.database, 'codex').call('read_run', {'case_id': self.case['case_id'], 'run_id': run['run_id']})
        dispatch({'database': str(self.database), 'folder': str(self.folder), 'operation': 'revoke'})
        with self.assertRaises(ValueError):
            self.tools.call('read_case', {'case_id': self.case['case_id']})

    def test_recent_runs_are_bounded_and_never_infer_success(self):
        with self.store.transaction() as db:
            for index in range(22):
                run = self.store.add(db, self.case['case_id'], 'run', {'status': 'running'})
            self.store.add(db, self.case['case_id'], 'outcome', {'run_id': run['id'], 'status': 'failed'})
        recent = self.tools.call('read_case', {'case_id': self.case['case_id']})['recent_runs']
        self.assertEqual(len(recent), 20)
        self.assertEqual(recent[0]['run_id'], run['id'])
        self.assertEqual(recent[0]['status'], 'failed')
        self.assertEqual(recent[1]['status'], 'incomplete')
        self.assertTrue(all(item['verification'] == 'Not performed' for item in recent))

    def test_new_evidence_invalidates_old_proposal_even_with_fresh_revision(self):
        result = self.proposal()
        self.evidence()
        with self.assertRaises(ValueError):
            approve_and_run(self.store, self.case['case_id'], self.case['revision'], result['proposal']['id'], result['proposal_hash'])

    def test_revocation_takes_effect_without_server_restart(self):
        dispatch({'database': str(self.database), 'folder': str(self.folder), 'operation': 'revoke'})
        with self.assertRaises(ValueError):
            self.tools.call('read_case', {'case_id': self.case['case_id']})

    def test_budget_is_off_then_bounded_and_failed_calls_consume_it(self):
        with self.assertRaises(ValueError):
            self.tools.call('evaluate_case', self.args())
        view = dispatch({'database': str(self.database), 'folder': str(self.folder), 'operation': 'budget', 'limit': 1})
        self.case = view['workflow']['case']
        with patch('jev_diagnostics.worker.run_case', return_value={'status': 'failed'}) as run:
            result = self.tools.call('evaluate_case', self.args())
            self.assertEqual(result['verification'], 'Not performed')
            with self.assertRaises(ValueError):
                self.tools.call('evaluate_case', self.args())
            run.assert_called_once()

    def test_failed_assertions_and_interrupted_runs_never_pass(self):
        self.assertEqual(classify({'passed': True, 'observations': [{'passed': False}]})['status'], 'failed')
        with self.store.transaction() as db:
            run = self.store.add(db, self.case['case_id'], 'run', {'status': 'running', 'approval_id': 'test-approval'})
        interrupt(self.store, self.case['case_id'])
        result = self.tools.call('read_run', {'case_id': self.case['case_id'], 'run_id': run['id']})
        self.assertEqual(result['outcome']['status'], 'interrupted')
        self.assertEqual(result['outcome']['verification'], 'Not performed')

    def test_saved_inputs_change_invalidates_approval(self):
        result = self.proposal()
        save_case(self.folder, dict(sample(), title='Changed saved inputs'))
        with self.assertRaises(ValueError):
            approve_and_run(self.store, self.case['case_id'], self.case['revision'], result['proposal']['id'], result['proposal_hash'])

    def test_incomplete_run_prevents_concurrent_execution(self):
        result = self.proposal()
        with self.store.transaction() as db:
            self.store.add(db, self.case['case_id'], 'run', {'status': 'running', 'approval_id': 'test'})
        with self.assertRaises(ValueError):
            approve_and_run(self.store, self.case['case_id'], self.case['revision'], result['proposal']['id'], result['proposal_hash'])

    def test_share_after_approval_preserves_history_and_changes_access(self):
        result = self.proposal()
        approve_and_run(self.store, self.case['case_id'], self.case['revision'], result['proposal']['id'], result['proposal_hash'])
        view = dispatch({'database': str(self.database), 'folder': str(self.folder), 'operation': 'share', 'hosts': ['claude']})['workflow']
        self.assertIn('shared with claude', view['notice'])
        self.assertNotEqual(view['case']['revision'], self.case['revision'])
        self.assertEqual(len(view['records']['approval']), 1)
        self.assertEqual(len(view['records']['outcome']), 1)
        self.assertTrue(all(item['review_revision'] != view['case']['revision'] for item in view['records']['proposal']))
        with self.assertRaises(ValueError):
            Tools(self.database, 'chatgpt').call('read_case', {'case_id': self.case['case_id']})

    def test_sdk_stdio_round_trip(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        async def round_trip():
            parameters = StdioServerParameters(command=os.environ.get('JEV_MCP_TEST_PYTHON', sys.executable), args=[
                '-m', 'jev_diagnostics.connectors.mcp_server', '--database', str(self.database), '--host', 'chatgpt'],
                env={'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')})
            async with stdio_client(parameters) as (reader, writer):
                async with ClientSession(reader, writer) as session:
                    await session.initialize()
                    listing = await session.list_tools()
                    self.assertEqual(len(listing.tools), 7)
                    self.assertTrue(all(tool.outputSchema for tool in listing.tools))
                    self.assertNotIn('approve', [tool.name for tool in listing.tools])
                    cases = await session.call_tool('list_cases', {})
                    self.assertFalse(cases.isError)
                    evidence = await session.call_tool('submit_evidence', dict(self.args(), content='SDK protocol fixture', origin='test client'))
                    self.assertFalse(evidence.isError)
                    data = evidence.structuredContent
                    proposal = await session.call_tool('submit_proposal', {'case_id': self.case['case_id'], 'expected_revision': data['revision'], 'evidence_ids': [data['evidence']['id']], 'summary': 'Check fixture', 'check_id': 'guest_access_fixture', 'expected_result': 'Guest is denied'})
                    self.assertFalse(proposal.isError)
                    submitted = proposal.structuredContent
                    approve_and_run(self.store, self.case['case_id'], submitted['revision'],
                                    submitted['proposal']['id'], submitted['proposal_hash'])
                    refreshed = await session.call_tool('read_case', {'case_id': self.case['case_id']})
                    recent = refreshed.structuredContent['recent_runs'][0]
                    self.assertEqual(recent['proposal_id'], submitted['proposal']['id'])
                    result = await session.call_tool('read_run', {'case_id': self.case['case_id'], 'run_id': recent['run_id']})
                    self.assertEqual(result.structuredContent['current']['status'], 'completed')
                    self.assertEqual(result.structuredContent['outcome']['verification']['status'], 'passed')
                    forbidden = await session.call_tool('approve', {})
                    self.assertTrue(forbidden.isError)
        asyncio.run(round_trip())

if __name__ == '__main__':
    unittest.main()
