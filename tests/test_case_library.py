"""Case identity and history must survive duplicate names without granting access."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jev_diagnostics.case_store import save_case, load_case
from jev_diagnostics.worker import dispatch
from jev_diagnostics.workflow import library
from jev_diagnostics.workflow.storage import Store, digest
from jev_diagnostics.workflow.state_service import share
from jev_diagnostics.workflow.demo import create
from jev_diagnostics.workflow.approvals import approve_and_run
from jev_diagnostics.connectors.tool_handlers import Tools
from test_workbench import sample


class CaseLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'workflow-v1.sqlite3')
        self.folder = self.root / 'case-a'
        self.case = sample()
        save_case(self.folder, self.case)

    def worker(self, **message):
        return dispatch(dict(activity_database=str(self.store.path), **message))

    def test_open_and_save_register_privately_and_preserve_shared_snapshot(self):
        self.worker(action='open', folder=str(self.folder))
        first = library.list_cases(self.store)['cases'][0]
        self.assertEqual(first['shared_with'], [])
        self.assertEqual(Tools(self.store.path, 'claude').call('list_cases', {})['cases'], [])
        shared = share(self.store, self.folder, ['claude'])
        self.assertEqual(shared['case_id'], first['case_id'])
        changed = dict(self.case, title='Renamed saved case')
        self.worker(action='save', folder=str(self.folder), case=changed)
        current = library.list_cases(self.store)['cases'][0]
        self.assertEqual(current['title'], changed['title'])
        self.assertEqual(current['case_id'], first['case_id'])
        read = Tools(self.store.path, 'claude').call('read_case', {'case_id': first['case_id']})
        self.assertEqual(read['case'], shared)
        with patch('jev_diagnostics.integrations.claude.status', return_value={}):
            view = self.worker(action='workflow', operation='status', database=str(self.store.path), folder=str(self.folder))['workflow']
        self.assertFalse(view['saved_snapshot_current'])

    def test_duplicate_names_are_separate_and_runs_are_linked_by_identity(self):
        self.worker(action='open', folder=str(self.folder))
        first = library.list_cases(self.store)['cases'][0]
        other = self.root / 'case-b'
        self.worker(action='save', folder=str(other), case=self.case)
        changed = dict(self.case, instructions='Different unsaved input')
        result = self.worker(action='run', case=changed, mode='local', folder=str(self.folder),
                             runs_folder=str(self.root / 'runs'))['result']
        self.assertEqual(result['case_id'], first['case_id'])
        self.assertEqual(result['input_hash'], digest(changed))
        self.assertEqual(load_case(self.folder), self.case)
        entries = library.list_cases(self.store)['cases']
        second = next(item for item in entries if item['case_id'] != first['case_id'])
        self.assertEqual(first['title'], second['title'])
        timeline = library.timeline(self.store, first['case_id'])
        runs = [item for item in timeline['events'] if item['kind'] == 'local_check']
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]['status'], 'completed')
        self.assertEqual(runs[0]['verification'], 'Passed')
        self.assertEqual(library.timeline(self.store, second['case_id'])['events'], [])

    def test_legacy_runs_are_unlinked_even_when_title_matches(self):
        self.worker(action='open', folder=str(self.folder))
        item = library.list_cases(self.store)['cases'][0]
        dispatch({'action': 'run', 'case': self.case, 'mode': 'local', 'runs_folder': str(self.root / 'runs')})
        self.assertEqual(library.timeline(self.store, item['case_id'])['events'], [])
        self.assertEqual(len(library.timeline(self.store, '')['events']), 1)

    def test_sample_reuse_preserves_identity_and_explicit_new_creates_another(self):
        first = create(self.store, self.case)
        self.assertEqual(create(self.store, self.case, fresh=False), first)
        self.assertEqual(len(library.list_cases(self.store)['cases']), 1)
        second = create(self.store, self.case, fresh=True)
        self.assertNotEqual(first, second)
        self.assertEqual(len(library.list_cases(self.store)['cases']), 2)

    def test_archive_revokes_access_preserves_history_and_restore_stays_private(self):
        folder = create(self.store, self.case)
        case = share(self.store, folder, ['claude'])
        before = library.timeline(self.store, case['case_id'])['events']
        library.set_archived(self.store, case['case_id'], True)
        self.assertNotIn(case['case_id'], [x['case_id'] for x in library.list_cases(self.store)['cases']])
        self.assertTrue(library.list_cases(self.store, archived=True)['cases'][0]['archived'])
        self.assertEqual(library.timeline(self.store, case['case_id'])['events'], before)
        with self.assertRaises(ValueError):
            Tools(self.store.path, 'claude').call('read_case', {'case_id': case['case_id']})
        self.assertTrue((Path(folder) / 'test.json').exists())
        library.set_archived(self.store, case['case_id'], False)
        with self.store.transaction() as db:
            restored = self.store.get_case(db, case['case_id'])
        self.assertEqual(restored['shared_with'], [])
        self.assertNotEqual(restored['revision'], case['revision'])
        self.assertEqual(library.timeline(self.store, case['case_id'])['events'], before)

    def test_archive_rejects_incomplete_run_and_no_history_read_executes(self):
        case = share(self.store, self.folder, ['claude'])
        with self.store.transaction() as db:
            self.store.add(db, case['case_id'], 'run', {'kind': 'jev_assessment', 'status': 'running'})
        with self.assertRaises(ValueError):
            library.set_archived(self.store, case['case_id'], True)
        with patch('jev_diagnostics.workflow.approvals.execute') as execute:
            event = library.timeline(self.store, case['case_id'])['events'][0]
            self.assertEqual(event['status'], 'incomplete')
            self.assertEqual(event['verification'], 'Not performed')
            execute.assert_not_called()

    def test_mixed_timeline_retains_proposal_and_exact_observed_outcome(self):
        folder = create(self.store, self.case)
        case = library.list_cases(self.store)['cases'][0]
        with self.store.transaction() as db:
            shared = self.store.get_case(db, case['case_id'])
            proposal = self.store.records(db, case['case_id'], 'proposal')[0]
        approve_and_run(self.store, case['case_id'], shared['revision'], proposal['id'], digest(proposal))
        timeline = library.timeline(self.store, case['case_id'])
        kinds = {event['kind'] for event in timeline['events']}
        self.assertTrue({'evidence', 'proposal', 'approval', 'assistant_check'}.issubset(kinds))
        run = next(x for x in timeline['events'] if x['kind'] == 'assistant_check')
        self.assertEqual(run['status'], 'completed')
        self.assertEqual(run['verification'], 'passed')
        self.assertEqual(run['proposal_id'], proposal['id'])
        self.assertEqual(run['details']['outcome']['verification']['status'], 'passed')

    def test_pre_catalogue_shared_case_is_visible_without_rewriting_records(self):
        case = share(self.store, self.folder, ['claude'])
        with self.store.transaction() as db:
            db.execute('DELETE FROM desktop_case_meta')
        listed = library.list_cases(self.store)['cases'][0]
        self.assertEqual(listed['case_id'], case['case_id'])
        self.assertEqual(listed['shared_with'], ['claude'])
        with self.store.transaction() as db:
            self.assertEqual(self.store.get_case(db, case['case_id']), case)

    def test_archive_invalidates_old_approval_and_cannot_be_shared_until_restored(self):
        folder = create(self.store, self.case)
        item = library.list_cases(self.store)['cases'][0]
        with self.store.transaction() as db:
            case = self.store.get_case(db, item['case_id'])
            proposal = self.store.records(db, item['case_id'], 'proposal')[0]
        library.set_archived(self.store, item['case_id'], True)
        with self.assertRaises(ValueError):
            share(self.store, folder, ['claude'])
        library.set_archived(self.store, item['case_id'], False)
        with patch('jev_diagnostics.workflow.approvals.execute') as execute:
            with self.assertRaises(ValueError):
                approve_and_run(self.store, item['case_id'], case['revision'], proposal['id'], digest(proposal))
            execute.assert_not_called()

    def test_sample_reuse_opens_saved_changes_without_resharing(self):
        folder = create(self.store, self.case)
        with self.store.transaction() as db:
            original = json.loads(db.execute('SELECT payload FROM cases').fetchone()['payload'])
        changed = dict(self.case, title='My edited sample')
        self.worker(action='save', folder=folder, case=changed)
        with patch('jev_diagnostics.integrations.claude.status', return_value={}):
            response = self.worker(action='workflow', operation='demo', database=str(self.store.path),
                                   sample=self.case, fresh=False)
        self.assertEqual(response['workflow']['demo_case'], changed)
        self.assertEqual(response['workflow']['case'], original)

    def test_failed_and_jev_runs_keep_their_different_meanings(self):
        case = share(self.store, self.folder, [])
        with patch('jev_diagnostics.worker.submit_request', side_effect=RuntimeError('Test failure')) as request:
            result = self.worker(action='run', case=self.case, mode='live', api_key='synthetic-secret',
                                 folder=str(self.folder), runs_folder=str(self.root / 'runs'))['result']
        request.assert_called_once()
        event = library.timeline(self.store, case['case_id'])['events'][0]
        self.assertEqual(event['kind'], 'jev_assessment')
        self.assertEqual(event['status'], 'failed')
        self.assertEqual(event['verification'], 'Not performed')
        self.assertNotIn('synthetic-secret', json.dumps(event))
        self.assertEqual(event['id'], result['run_id'])

    def test_timeline_detects_tampered_assistant_records(self):
        folder = create(self.store, self.case)
        item = library.list_cases(self.store)['cases'][0]
        with self.store.transaction() as db:
            db.execute("UPDATE records SET payload='{}' WHERE kind='evidence'")
        with self.assertRaises(ValueError):
            library.timeline(self.store, item['case_id'])

    def test_delivery_token_changes_for_history_updates_but_not_history_reads(self):
        from jev_diagnostics.workflow.inbox import snapshot
        self.worker(action='open', folder=str(self.folder))
        case = library.list_cases(self.store)['cases'][0]
        before = snapshot(self.store)['change_token']
        library.timeline(self.store, case['case_id'])
        self.assertEqual(snapshot(self.store)['change_token'], before)
        self.worker(action='run', case=self.case, mode='local', folder=str(self.folder),
                    runs_folder=str(self.root / 'runs'))
        self.assertNotEqual(snapshot(self.store)['change_token'], before)

    def test_missing_source_and_bad_identity_are_actionable(self):
        case = share(self.store, self.folder, [])
        (self.folder / 'test.json').unlink()
        self.assertFalse(library.list_cases(self.store)['cases'][0]['available'])
        with self.assertRaises(ValueError):
            library.open_case(self.store, case['case_id'])
        for identity in ('case-missing', '../outside'):
            with self.assertRaises(ValueError):
                library.timeline(self.store, identity)


if __name__ == '__main__':
    unittest.main()
