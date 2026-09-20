"""Local workflow sidecar. Transactions serialize desktop and assistant writes."""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

HOSTS = ('claude', 'chatgpt', 'codex', 'preview')

def encode(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False)

def digest(value):
    return hashlib.sha256(encode(value).encode('utf-8')).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def identifier(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 100 or any(
            character not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_' for character in value):
        raise ValueError('Invalid identifier. Paths are not accepted.')
    return value

def bounded_text(value, label, limit=16000):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > limit:
        raise ValueError(label + ' must be nonempty text within ' + str(limit) + ' bytes.')
    return value

class Store:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS workflow_meta (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
            db.execute("INSERT OR IGNORE INTO workflow_meta VALUES ('workspace_id', ?)", ('workspace-' + uuid4().hex,))
            db.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, source TEXT UNIQUE, payload TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS records (id TEXT PRIMARY KEY, case_id TEXT NOT NULL, kind TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL)')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def get_case(self, db, case_id, host=None, expected=None):
        row = db.execute('SELECT payload FROM cases WHERE id=?', (identifier(case_id),)).fetchone()
        if row is None:
            raise ValueError('Case is unavailable or not shared with this connection.')
        case = json.loads(row['payload'])
        if host is not None and (host not in HOSTS or host not in case['shared_with']):
            raise ValueError('Case is unavailable or not shared with this connection.')
        if expected is not None and expected != case['revision']:
            raise ValueError('Stale revision. Read the case again and review new evidence.')
        return case

    def put_case(self, db, case):
        db.execute('UPDATE cases SET payload=? WHERE id=?', (encode(case), case['case_id']))

    def advance(self, db, case):
        case['revision'] = 'rev-' + uuid4().hex
        self.put_case(db, case)

    def ensure_idle(self, db):
        runs = db.execute("SELECT id FROM records WHERE kind='run'").fetchall()
        outcomes = db.execute("SELECT payload FROM records WHERE kind='outcome'").fetchall()
        completed = {json.loads(row['payload'])['run_id'] for row in outcomes}
        if any(row['id'] not in completed for row in runs):
            raise ValueError('A run is active or incomplete. Stop it in its owning client before starting another.')

    def add(self, db, case_id, kind, payload):
        if kind in ('evidence', 'state', 'proposal'):
            count = db.execute('SELECT count(*) FROM records WHERE case_id=? AND kind=?', (case_id, kind)).fetchone()[0]
            if count >= 20:
                raise ValueError('Preview limit: 20 records per kind per case. Start a new case for further work.')
        record_id = kind + '-' + uuid4().hex
        payload = dict(payload, id=record_id, created_at=now(), workflow_schema_version=1)
        db.execute('INSERT INTO records VALUES (?,?,?,?,?)',
                   (record_id, case_id, kind, encode(payload), digest(payload)))
        from ..activity import insert
        insert(db, payload.get('submitted_by', 'worker'), kind, 'recorded', case_id=case_id, record_id=record_id)
        return payload

    def records(self, db, case_id, kind):
        rows = db.execute('SELECT payload,hash FROM records WHERE case_id=? AND kind=? ORDER BY rowid DESC LIMIT 100', (case_id, kind))
        result = []
        for row in rows:
            value = json.loads(row['payload'])
            if digest(value) != row['hash']:
                raise ValueError('Stored record integrity check failed.')
            result.append(value)
        return result

    def record(self, db, case_id, kind, record_id):
        row = db.execute('SELECT payload,hash FROM records WHERE id=? AND case_id=? AND kind=?',
                         (identifier(record_id), case_id, kind)).fetchone()
        if row is None:
            raise ValueError('Referenced record does not belong to this case.')
        value = json.loads(row['payload'])
        if digest(value) != row['hash']:
            raise ValueError('Stored record integrity check failed.')
        return value
