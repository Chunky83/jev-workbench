"""Cross-case delivery and safe review of assistant proposals."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jev_diagnostics.case_store import save_case
from jev_diagnostics.connectors.tool_handlers import Tools
from jev_diagnostics.workflow import inbox
from jev_diagnostics.workflow.approvals import approve_and_run
from jev_diagnostics.workflow.budget import configure
from jev_diagnostics.workflow.state_service import share
from jev_diagnostics.workflow.storage import Store, digest
from test_workbench import sample


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'workflow-v1.sqlite3'
        self.store = Store(self.database)
        # Reproduce the confusing real workflow: identical demo titles and an
        # unrelated case open in the editor while Claude works on another one.
        self.case_a, self.folder_a = self.create_case('editor-case')
        self.case_b, self.folder_b = self.create_case('assistant-case')

    def create_case(self, directory, hosts=None):
        folder = self.root / directory
        save_case(folder, dict(sample(), title='Synthetic connector walkthrough'))
        return share(self.store, folder, hosts or ['claude', 'chatgpt', 'codex']), folder

    def submit(self, case, host='claude'):
        tools = Tools(self.database, host)
        evidence = tools.call('submit_evidence', {
            'case_id': case['case_id'], 'expected_revision': case['revision'],
            'content': 'Synthetic observation: guest denied with HTTP 401.',
            'origin': 'Inbox integration test'})
        case['revision'] = evidence['revision']
        result = tools.call('submit_proposal', {
            'case_id': case['case_id'], 'expected_revision': case['revision'],
            'evidence_ids': [evidence['evidence']['id']],
            'summary': 'Verify the guest access fixture',
            'check_id': 'guest_access_fixture',
            'expected_result': 'Guest denied without protected content; owner permitted.'})
        case['revision'] = result['revision']
        return result

    def item(self, proposal_id):
        return next(item for item in inbox.snapshot(self.store)['proposals']
                    if item['proposal_id'] == proposal_id)

    def review_record(self, case, result):
        view = inbox.review(self.store, case['case_id'], result['proposal']['id'])
        record = next(record for record in view['records']['proposal']
                      if record['id'] == result['proposal']['id'])
        return view, record

    def workflow_rows(self):
        with self.store.transaction() as db:
            return {
                'cases': [tuple(row) for row in db.execute('SELECT * FROM cases ORDER BY id')],
                'records': [tuple(row) for row in db.execute('SELECT * FROM records ORDER BY id')],
            }

    def test_external_case_is_delivered_and_exact_case_is_reviewed(self):
        result = self.submit(self.case_b)
        listing = inbox.snapshot(self.store)['proposals']
        self.assertEqual(len(listing), 1)
        item = listing[0]
        self.assertEqual(item['case_id'], self.case_b['case_id'])
        self.assertNotEqual(item['case_id'], self.case_a['case_id'])
        self.assertEqual(item['proposal_id'], result['proposal']['id'])
        self.assertEqual(item['title'], self.case_b['snapshot']['title'])
        self.assertEqual(item['submitted_by'], 'claude')
        self.assertEqual(item['summary'], result['proposal']['summary'])
        self.assertEqual(item['created_at'], result['proposal']['created_at'])
        self.assertEqual(item['revision'], self.case_b['revision'])
        self.assertEqual(item['status'], 'ready')
        view, proposal = self.review_record(self.case_b, result)
        self.assertEqual(view['case'], self.case_b)
        self.assertEqual(view['proposal_id'], result['proposal']['id'])
        self.assertEqual(proposal['id'], item['proposal_id'])
        self.assertEqual(len(view['records']['evidence']), 1)

    def test_all_external_hosts_are_included_and_preview_is_excluded(self):
        expected = {self.submit(self.case_a, 'claude')['proposal']['id'],
                    self.submit(self.case_b, 'chatgpt')['proposal']['id']}
        codex_case, _ = self.create_case('codex-case')
        expected.add(self.submit(codex_case, 'codex')['proposal']['id'])
        preview_case, _ = self.create_case('preview-case', ['preview'])
        preview_id = self.submit(preview_case, 'preview')['proposal']['id']
        actual = {item['proposal_id'] for item in inbox.snapshot(self.store)['proposals']}
        self.assertEqual(actual, expected)
        self.assertNotIn(preview_id, actual)

    def test_connector_reread_after_submit_does_not_stale_proposal(self):
        result = self.submit(self.case_b)
        tools = Tools(self.database, 'claude')
        for _ in range(2):
            read = tools.call('read_case', {'case_id': self.case_b['case_id']})
            self.assertEqual(read['case']['revision'], result['revision'])
            self.assertEqual(self.item(result['proposal']['id'])['status'], 'ready')
        self.assertEqual(self.item(result['proposal']['id'])['revision'], result['revision'])

    def test_share_and_allowance_changes_keep_stale_proposals_visible(self):
        for operation in ('share', 'budget'):
            with self.subTest(operation=operation):
                case, folder = self.create_case(operation + '-case')
                result = self.submit(case)
                if operation == 'share':
                    updated = share(self.store, folder, ['claude'])
                else:
                    with self.store.transaction() as db:
                        updated = self.store.get_case(db, case['case_id'])
                        configure(self.store, db, updated, 1)
                item = self.item(result['proposal']['id'])
                self.assertEqual(item['status'], 'stale')
                view, reviewed = self.review_record(updated, result)
                self.assertEqual(view['case']['revision'], updated['revision'])
                self.assertEqual(reviewed['review_revision'], result['revision'])
                with self.assertRaises(ValueError):
                    approve_and_run(self.store, case['case_id'], updated['revision'],
                                    result['proposal']['id'], reviewed['review_hash'])

    def test_revoked_proposal_remains_visible_but_cannot_be_approved(self):
        result = self.submit(self.case_b)
        revoked = share(self.store, self.folder_b, [])
        self.assertEqual(self.item(result['proposal']['id'])['status'], 'revoked')
        view, reviewed = self.review_record(revoked, result)
        self.assertEqual(view['case']['shared_with'], [])
        with patch('jev_diagnostics.workflow.approvals.execute') as execute:
            with self.assertRaises(ValueError):
                approve_and_run(self.store, revoked['case_id'], revoked['revision'],
                                result['proposal']['id'], reviewed['review_hash'])
            execute.assert_not_called()

    def test_approved_proposal_leaves_inbox_but_its_review_is_preserved(self):
        result = self.submit(self.case_b)
        _, reviewed = self.review_record(self.case_b, result)
        with patch('jev_diagnostics.workflow.approvals.execute', return_value={
                'verification': {'status': 'passed', 'scope': 'Synthetic fixture only'}}) as execute:
            approve_and_run(self.store, self.case_b['case_id'], self.case_b['revision'],
                            result['proposal']['id'], reviewed['review_hash'])
            execute.assert_called_once_with('guest_access_fixture', None)
        self.assertNotIn(result['proposal']['id'],
                         [item['proposal_id'] for item in inbox.snapshot(self.store)['proposals']])
        view, reviewed_again = self.review_record(self.case_b, result)
        self.assertEqual(len(view['records']['approval']), 1)
        self.assertEqual(len(view['records']['outcome']), 1)
        self.assertEqual(reviewed_again['review_hash'], result['proposal_hash'])

    def test_wrong_case_and_missing_proposal_references_are_rejected(self):
        result = self.submit(self.case_b)
        for case_id, proposal_id in (
                (self.case_a['case_id'], result['proposal']['id']),
                (self.case_b['case_id'], 'proposal-missing'),
                ('case-missing', result['proposal']['id']),
                (self.case_b['case_id'], '../outside')):
            with self.subTest(case_id=case_id, proposal_id=proposal_id):
                with self.assertRaises(ValueError):
                    inbox.review(self.store, case_id, proposal_id)

    def test_review_hash_is_of_original_record_and_is_never_stored(self):
        result = self.submit(self.case_b)
        _, reviewed = self.review_record(self.case_b, result)
        self.assertEqual(reviewed['review_hash'], result['proposal_hash'])
        without_review_hash = {key: value for key, value in reviewed.items() if key != 'review_hash'}
        self.assertEqual(without_review_hash, result['proposal'])
        self.assertEqual(reviewed['review_hash'], digest(without_review_hash))
        with self.store.transaction() as db:
            original = self.store.record(db, self.case_b['case_id'], 'proposal', result['proposal']['id'])
        self.assertNotIn('review_hash', original)

    def test_tampered_proposal_is_rejected_by_delivery_and_review(self):
        result = self.submit(self.case_b)
        changed = dict(result['proposal'], summary='Tampered after submission')
        with self.store.transaction() as db:
            db.execute('UPDATE records SET payload=? WHERE id=?',
                       (json.dumps(changed), result['proposal']['id']))
        with self.assertRaises(ValueError):
            inbox.snapshot(self.store)
        with self.assertRaises(ValueError):
            inbox.review(self.store, self.case_b['case_id'], result['proposal']['id'])

    def test_review_rejects_tampered_supporting_evidence(self):
        result = self.submit(self.case_b)
        with self.store.transaction() as db:
            db.execute('UPDATE records SET payload=? WHERE id=?',
                       ('{}', result['proposal']['evidence_ids'][0]))
        with self.assertRaises(ValueError):
            inbox.review(self.store, self.case_b['case_id'], result['proposal']['id'])

    def test_workspace_identity_survives_reload_and_distinguishes_databases(self):
        identity = inbox.snapshot(self.store)['workspace_id']
        self.assertIsInstance(identity, str)
        self.assertTrue(identity)
        self.assertEqual(inbox.snapshot(Store(self.database))['workspace_id'], identity)
        other = Store(self.root / 'another-workspace' / 'workflow-v1.sqlite3')
        self.assertNotEqual(inbox.snapshot(other)['workspace_id'], identity)

    def test_delivery_and_review_do_not_modify_cases_or_execute(self):
        result = self.submit(self.case_b)
        inbox.snapshot(self.store)
        before = self.workflow_rows()
        with patch('jev_diagnostics.workflow.approvals.execute') as execute:
            for _ in range(3):
                inbox.snapshot(self.store)
                inbox.review(self.store, self.case_b['case_id'], result['proposal']['id'])
            execute.assert_not_called()
        self.assertEqual(self.workflow_rows(), before)
        with self.store.transaction() as db:
            self.assertEqual(self.store.records(db, self.case_b['case_id'], 'approval'), [])
            self.assertEqual(self.store.records(db, self.case_b['case_id'], 'run'), [])


if __name__ == '__main__':
    unittest.main()
