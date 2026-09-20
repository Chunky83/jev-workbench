"""Desktop setup against disposable profiles; never mutate installed client settings."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from jev_diagnostics.integrations import claude
from jev_diagnostics.workflow.storage import Store

class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = {'APPDATA': str(self.root / 'Roaming'), 'LOCALAPPDATA': str(self.root / 'Local')}
        self.profile = self.root / 'Local/Packages/Claude_test/LocalCache/Roaming/Claude'
        self.profile.mkdir(parents=True)
        self.path = self.profile / 'claude_desktop_config.json'
        self.original = b'{"mcpServers":{"other":{"env":{"SECRET":"do-not-return"}}},"theme":"dark"}'
        self.path.write_bytes(self.original)
        self.store = Store(self.root / 'workflow.sqlite3')
        self.launcher = {'command': sys.executable, 'args': ['-m', 'jev_diagnostics.connectors.mcp_server', '--host', 'claude'], 'env': {}}
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, self.env).start()
        patch.object(claude.sys, 'platform', 'win32').start()

    def prepare(self):
        profile = claude.status(self.store, self.launcher)['profiles'][0]
        claude.prepare(self.store, profile['id'], self.launcher)
        return claude.status(self.store, self.launcher)['plan']['id']

    def test_store_profile_discovery_and_no_secret_output(self):
        result = claude.status(self.store, self.launcher)
        self.assertEqual(len(result['profiles']), 1)
        self.assertIn('Microsoft Store', result['profiles'][0]['label'])
        self.assertNotIn('do-not-return', json.dumps(result))
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_multiple_profiles_and_missing_config(self):
        standard = self.root / 'Roaming/Claude'
        standard.mkdir(parents=True)
        profiles, _ = claude.candidates()
        self.assertEqual(len(profiles), 2)
        self.assertNotEqual(profiles[0]['id'], profiles[1]['id'])
        claude.prepare(self.store, profiles[0]['id'], self.launcher)
        plan = claude.status(self.store)['plan']
        self.assertFalse((standard / 'claude_desktop_config.json').exists())
        claude.apply(self.store, plan['id'])
        self.assertTrue((standard / 'claude_desktop_config.json').exists())
        claude.restore(self.store, plan['id'])
        self.assertFalse((standard / 'claude_desktop_config.json').exists())

    def test_review_apply_backup_restore_and_replay(self):
        plan = self.prepare()
        self.assertEqual(self.path.read_bytes(), self.original)
        claude.apply(self.store, plan)
        updated = json.loads(self.path.read_bytes())
        self.assertEqual(updated['mcpServers']['other']['env']['SECRET'], 'do-not-return')
        self.assertEqual(updated['theme'], 'dark')
        self.assertEqual(updated['mcpServers']['jev-workbench'], self.launcher)
        self.assertEqual(next(self.profile.glob('*.jev-backup-*')).read_bytes(), self.original)
        self.assertTrue(claude.status(self.store, self.launcher)['profiles'][0]['configured'])
        self.assertEqual(claude.status(self.store)['activity'], [])
        with self.assertRaises(ValueError):
            claude.apply(self.store, plan)
        claude.restore(self.store, plan)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_changed_settings_between_review_and_approval(self):
        plan = self.prepare()
        changed = self.original + b' '
        self.path.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'changed after review'):
            claude.apply(self.store, plan)
        self.assertEqual(self.path.read_bytes(), changed)

    def test_undo_preserves_later_edits(self):
        plan = self.prepare()
        claude.apply(self.store, plan)
        changed = self.path.read_bytes() + b' '
        self.path.write_bytes(changed)
        with self.assertRaisesRegex(ValueError, 'changed since setup'):
            claude.restore(self.store, plan)
        self.assertEqual(self.path.read_bytes(), changed)

    def test_invalid_duplicate_and_oversized_settings_are_not_replaced(self):
        for raw in (b'{broken', b'{"mcpServers":{},"mcpServers":{}}', b'{"mcpServers":[]}', b'x' * (claude.MAX_CONFIG + 1)):
            self.path.write_bytes(raw)
            profile = claude.status(self.store)['profiles'][0]
            self.assertFalse(profile['available'])
            with self.assertRaises(ValueError):
                claude.prepare(self.store, profile['id'], self.launcher)
            self.assertEqual(self.path.read_bytes(), raw)

    def test_arbitrary_path_and_missing_runtime_are_rejected(self):
        with self.assertRaises(ValueError):
            claude.prepare(self.store, str(self.path), self.launcher)
        with self.assertRaises(ValueError):
            claude.prepare(self.store, 'invalid', {'command': str(self.root / 'missing')})

    def test_expired_review_and_corrupt_backup(self):
        plan = self.prepare()
        with self.store.transaction() as db:
            payload = json.loads(db.execute('SELECT payload FROM integration_plans WHERE id=?', (plan,)).fetchone()['payload'])
            payload['created'] = '2000-01-01T00:00:00+00:00'
            db.execute('UPDATE integration_plans SET payload=? WHERE id=?', (json.dumps(payload), plan))
        with self.assertRaisesRegex(ValueError, 'expired'):
            claude.apply(self.store, plan)
        plan = self.prepare()
        claude.apply(self.store, plan)
        next(self.profile.glob('*.jev-backup-*')).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'backup changed'):
            claude.restore(self.store, plan)

    def test_desktop_feedback_and_setup_cancellation(self):
        from jev_diagnostics.workflow.desktop_service import dispatch
        profile = claude.status(self.store)['profiles'][0]
        message = {'database': str(self.store.path), 'launcher': self.launcher}
        view = dispatch(dict(message, operation='setup_review', profile_id=profile['id']))['workflow']
        self.assertIn('Review', view['notice'])
        plan = view['integration']['plan']['id']
        view = dispatch(dict(message, operation='setup_cancel', plan_id=plan))['workflow']
        self.assertIn('cancelled', view['notice'])
        self.assertEqual(self.path.read_bytes(), self.original)
        view = dispatch(dict(message, operation='connection_check'))['workflow']
        self.assertIn('No Claude tool request', view['notice'])
        plan = self.prepare()
        view = dispatch(dict(message, operation='setup_apply', plan_id=plan))['workflow']
        self.assertIn('Setup saved', view['notice'])

    def test_configuration_receipt_recovers_after_process_exit(self):
        plan = self.prepare()
        claude.apply(self.store, plan)
        with self.store.transaction() as db:
            payload = json.loads(db.execute('SELECT payload FROM integration_plans WHERE id=?', (plan,)).fetchone()['payload'])
            payload['state'] = 'review'
            db.execute('UPDATE integration_plans SET payload=? WHERE id=?', (json.dumps(payload), plan))
        self.assertEqual(claude.status(self.store)['plan']['state'], 'applied')
        claude.restore(self.store, plan)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_activity_requires_successful_protocol_tool_call(self):
        from jev_diagnostics.connectors.mcp_server import create_server
        import asyncio
        server = create_server(self.store.path, 'claude')
        self.assertEqual(claude.status(self.store)['activity'], [])
        asyncio.run(server.call_tool('list_cases', {}))
        activity = claude.status(self.store)['activity']
        self.assertEqual(activity[0]['tool'], 'list_cases')
        self.assertEqual(activity[0]['host'], 'claude')

if __name__ == '__main__':
    unittest.main()
