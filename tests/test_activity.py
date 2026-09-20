import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4
from jev_diagnostics import activity
from jev_diagnostics.workflow.storage import Store
from jev_diagnostics.integrations import claude
from jev_diagnostics.integrations.diagnostics import run
from jev_diagnostics.worker import dispatch
from jev_diagnostics.case_store import save_case
from test_workbench import sample

class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'workflow.sqlite3'
        self.store = Store(self.database)

    def events(self):
        return activity.timeline(self.database, 10000)['events']

    def test_success_failure_and_correlation_without_content(self):
        request = uuid4().hex
        result = activity.trace(self.database, 'claude', 'read_case', lambda: {'secret': 'not-logged'}, request)
        self.assertEqual(result['secret'], 'not-logged')
        with self.assertRaises(ValueError):
            activity.trace(self.database, 'claude', 'read_case', lambda: (_ for _ in ()).throw(ValueError('token-secret')), case_id='private-secret')
        events = self.events()
        self.assertEqual(len(events), 4)
        self.assertEqual(len([e for e in events if e['request_id'] == request]), 2)
        self.assertTrue(any(e['status'] == 'rejected' for e in events))
        self.assertNotIn('secret', json.dumps(events))

    def test_invalid_tool_arguments_are_logged_without_argument_values(self):
        from jev_diagnostics.connectors.mcp_server import create_server
        import asyncio
        server = create_server(self.database, 'claude')
        with self.assertRaises(Exception):
            asyncio.run(server.call_tool('read_case', {'wrong': 'private-secret'}))
        events = self.events()
        self.assertEqual(events[0]['status'], 'failed')
        self.assertNotIn('private-secret', json.dumps(events))

    def test_every_call_is_retained(self):
        from jev_diagnostics.connectors.mcp_server import create_server
        import asyncio
        server = create_server(self.database, 'claude')
        for _ in range(3):
            asyncio.run(server.call_tool('list_cases', {}))
        self.assertEqual(len([e for e in self.events() if e['status'] == 'succeeded']), 3)

    def test_log_write_failure_does_not_repeat_business_action(self):
        calls = []
        with patch.object(activity, 'emit', return_value=False):
            value = activity.trace(self.database, 'worker', 'save', lambda: calls.append(1) or 'done')
        self.assertEqual(value, 'done')
        self.assertEqual(calls, [1])

    def test_export_filters_native_fields_and_malformed_lines(self):
        event = {'created_at': '2026-09-19T12:00:00+00:00', 'actor': 'desktop', 'operation': 'save',
                 'status': 'succeeded', 'request_id': 'secret-token', 'private': 'private-evidence', 'error': 'password-secret'}
        # Use a current timestamp so this test remains valid after September.
        from datetime import datetime, timezone
        event['created_at'] = datetime.now(timezone.utc).isoformat()
        (self.root / 'desktop-activity.jsonl').write_text(json.dumps(event) + '\n{truncated', encoding='utf-8')
        report = json.loads(Path(activity.export(self.database)).read_text())
        self.assertEqual(len(report['events']), 1)
        self.assertNotIn('secret', json.dumps(report))
        self.assertNotIn('private-evidence', json.dumps(report))
        self.assertTrue(report['warnings'])

    def test_old_events_and_count_are_bounded(self):
        activity.emit(self.database, 'worker', 'status', 'started')
        with self.store.transaction() as db:
            db.execute("INSERT INTO activity_events(created_at,payload) VALUES ('2000-01-01','{}')")
            db.executemany("INSERT INTO activity_events(created_at,payload) VALUES ('2999-01-01','{}')", [()]*10010)
        activity.emit(self.database, 'worker', 'status', 'succeeded')
        with self.store.transaction() as db:
            self.assertLessEqual(db.execute('SELECT count(*) FROM activity_events').fetchone()[0], 10000)
            self.assertEqual(db.execute("SELECT count(*) FROM activity_events WHERE created_at='2000-01-01'").fetchone()[0], 0)

    def test_transactional_records_share_revoke_budget_and_approval(self):
        from jev_diagnostics.workflow.state_service import share
        from jev_diagnostics.workflow.budget import configure
        folder = self.root / 'case'
        save_case(folder, sample())
        case = share(self.store, folder, ['claude'])
        with self.store.transaction() as db:
            configure(self.store, db, case, 2)
            record = self.store.add(db, case['case_id'], 'approval', {'proposal_id': 'synthetic'})
        dispatch({'action': 'workflow', 'operation': 'revoke', 'database': str(self.database), 'folder': str(folder)})
        events = self.events()
        self.assertTrue({'share', 'budget', 'approval', 'revoke'}.issubset({e['operation'] for e in events}))
        self.assertTrue(any(e['record_id'] == record['id'] for e in events))

    def test_real_local_diagnostic_does_not_claim_claude_activity(self):
        launcher = {'command': sys.executable, 'args': ['-m', 'jev_diagnostics.connectors.mcp_server', '--database', str(self.database), '--host', 'claude'], 'env': {'PYTHONPATH': str(Path(__file__).resolve().parents[1] / 'src')}}
        result = run(launcher)
        self.assertEqual(result['status'], 'passed', result)
        self.assertEqual(claude.status(self.store)['activity'], [])
        self.assertTrue(any(e['actor'] == 'diagnostic' and e['operation'] == 'list_cases' for e in self.events()))

    def test_missing_runtime_diagnostic_is_failure_not_claude_success(self):
        result = run({'command': str(self.root / 'missing'), 'args': []})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(claude.status(self.store)['activity'], [])

    def test_failure_returned_as_data_is_not_logged_as_success(self):
        activity.trace(self.database, 'worker', 'diagnostics', lambda: {'workflow': {'diagnostic': {'status': 'failed'}}})
        self.assertEqual(self.events()[0]['status'], 'failed')
