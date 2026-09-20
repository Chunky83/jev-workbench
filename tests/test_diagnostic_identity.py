from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from jev_diagnostics.integrations import diagnostics
from jev_diagnostics.workflow.storage import Store


class DiagnosticIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.database = self.root / 'workflow.sqlite3'
        self.store = Store(self.database)

    def test_existing_workspace_and_physical_file_are_reported_without_mutation(self):
        before = self.database.read_bytes()
        with closing(sqlite3.connect(self.database)) as db:
            expected = db.execute("SELECT value FROM workflow_meta WHERE name='workspace_id'").fetchone()[0]
            identity = diagnostics.database_identity(self.database, db)
        self.assertEqual(identity['workspace_id'], expected)
        self.assertTrue(os.path.samefile(identity['physical_database_path'], self.database))
        self.assertEqual(self.database.read_bytes(), before)

    def test_legacy_database_is_not_initialized_by_identity_lookup(self):
        legacy = self.root / 'legacy.sqlite3'
        with closing(sqlite3.connect(legacy)) as db:
            db.execute('CREATE TABLE cases (id TEXT PRIMARY KEY)')
        before = legacy.read_bytes()
        with closing(sqlite3.connect(legacy)) as db:
            identity = diagnostics.database_identity(legacy, db)
            self.assertIsNone(identity['workspace_id'])
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE name='workflow_meta'").fetchall(), [])
        self.assertEqual(legacy.read_bytes(), before)

    def test_unavailable_path_does_not_invent_identity_or_expose_error_details(self):
        missing = self.root / 'missing.sqlite3'
        with closing(sqlite3.connect(self.database)) as db:
            with patch.object(diagnostics, 'physical_database_path', side_effect=OSError('private-path-secret')):
                identity = diagnostics.database_identity(missing, db)
        self.assertIsNone(identity['physical_database_path'])
        self.assertEqual(identity['identity_error'], 'OSError')
        self.assertNotIn('secret', json.dumps(identity))
        self.assertFalse(missing.exists())

    @unittest.skipUnless(os.name == 'nt', 'Windows handle resolution')
    def test_windows_handle_is_closed_when_native_resolution_fails(self):
        stream = self.database.open('rb')
        library = Mock()
        library.GetFinalPathNameByHandleW.return_value = 0
        with patch.object(Path, 'open', return_value=stream), patch('ctypes.WinDLL', return_value=library):
            with self.assertRaises(OSError):
                diagnostics.physical_database_path(self.database)
        self.assertTrue(stream.closed)

    def test_identity_survives_protocol_failure_in_local_result(self):
        launcher = {'command': sys.executable, 'args': ['-m', 'jev_diagnostics.connectors.mcp_server',
                    '--database', str(self.database), '--host', 'claude']}
        async def failing_protocol(_):
            raise RuntimeError('private-runtime-details')
        with patch.object(diagnostics, 'protocol', failing_protocol):
            result = diagnostics.run(launcher)
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['workspace_id'].startswith('workspace-'))
        self.assertTrue(os.path.samefile(result['physical_database_path'], self.database))
        self.assertNotIn('private-runtime-details', json.dumps(result))
