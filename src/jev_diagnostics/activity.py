"""Bounded metadata-only activity history. Never persist arguments or exception text."""
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import time
from uuid import uuid4

correlation = ContextVar('activity_correlation', default='')
OPERATIONS = {'case_list', 'case_history', 'open_case', 'archive_case', 'restore_case', 'review_proposal', 'inbox', 'status', 'demo', 'share', 'approve', 'interrupt', 'budget', 'revoke',
    'setup_review', 'setup_cancel', 'setup_apply', 'setup_undo', 'connection_check',
    'diagnostics', 'activity', 'activity_export', 'open', 'save', 'preview', 'run', 'history',
    'list_cases', 'read_case', 'submit_evidence', 'propose_state', 'evaluate_case',
    'submit_proposal', 'read_run', 'session', 'evidence', 'state', 'proposal', 'approval',
    'outcome', 'allowance_consumed', 'unknown'}
ACTORS = {'desktop', 'worker', 'claude', 'chatgpt', 'codex', 'preview', 'diagnostic'}
STATUSES = {'started', 'succeeded', 'failed', 'cancelled', 'recorded', 'stopped', 'timeout', 'rejected'}
ERRORS = {'ValueError', 'KeyError', 'TypeError', 'OSError', 'PermissionError', 'RuntimeError',
          'TimeoutError', 'OperationalError', 'Exception', 'worker_exit', 'invalid_response',
          'failed_to_start', 'output_limit', 'logging_unavailable', 'none'}

def safe_id(value):
    if not isinstance(value, str) or len(value) > 100:
        return ''
    suffix = value
    for prefix in ('case-', 'rev-', 'evidence-', 'state-', 'proposal-', 'approval-', 'run-', 'outcome-'):
        if value.startswith(prefix):
            suffix = value[len(prefix):]
            break
    compact = suffix.replace('-', '')
    return value if len(compact) == 32 and all(c in '0123456789abcdef' for c in compact) else ''

def insert(db, actor, operation, status, *, request_id='', case_id='', record_id='', error='none', elapsed_ms=0):
    db.execute('CREATE TABLE IF NOT EXISTS activity_events (seq INTEGER PRIMARY KEY, created_at TEXT NOT NULL, payload TEXT NOT NULL)')
    event = {'event_id': uuid4().hex, 'created_at': datetime.now(timezone.utc).isoformat(),
        'actor': actor if actor in ACTORS else 'worker',
        'operation': operation if operation in OPERATIONS else 'unknown',
        'status': status if status in STATUSES else 'recorded',
        'request_id': safe_id(request_id or correlation.get()), 'case_id': safe_id(case_id),
        'record_id': safe_id(record_id), 'error': error if error in ERRORS else 'Exception',
        'elapsed_ms': max(0, min(int(elapsed_ms), 86400000))}
    db.execute('INSERT INTO activity_events(created_at,payload) VALUES (?,?)', (event['created_at'], json.dumps(event)))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    db.execute('DELETE FROM activity_events WHERE created_at < ?', (cutoff,))
    db.execute('DELETE FROM activity_events WHERE seq <= (SELECT MAX(seq)-10000 FROM activity_events)')
    return event

@contextmanager
def connection(database, timeout=1):
    db = sqlite3.connect(database, timeout=timeout)
    try:
        with db:
            yield db
    finally:
        db.close()

def emit(database, actor, operation, status, **fields):
    # Diagnostic logging never retries an operation or converts its success to failure.
    try:
        path = Path(database)
        path.parent.mkdir(parents=True, exist_ok=True)
        with connection(path) as db:
            insert(db, actor, operation, status, **fields)
        return True
    except (OSError, sqlite3.Error):
        return False

def trace(database, actor, operation, function, request_id='', case_id=''):
    request_id = safe_id(request_id) or uuid4().hex
    token = correlation.set(request_id)
    started = time.monotonic()
    logged_start = emit(database, actor, operation, 'started', case_id=case_id)
    try:
        result = function()
    except Exception as error:
        emit(database, actor, operation, 'rejected' if isinstance(error, (ValueError, KeyError, TypeError)) else 'failed',
             case_id=case_id, error=type(error).__name__, elapsed_ms=(time.monotonic()-started)*1000)
        raise
    else:
        # Some worker actions return a failed run as data rather than raising.
        failed = isinstance(result, dict) and (result.get('result', {}).get('status') == 'failed' or (result.get('workflow', {}).get('diagnostic') or {}).get('status') == 'failed')
        logged_finish = emit(database, actor, operation, 'failed' if failed else 'succeeded', case_id=case_id,
             elapsed_ms=(time.monotonic()-started)*1000)
        if isinstance(result, dict) and (not logged_start or not logged_finish):
            result['activity_warning'] = 'Activity could not be fully saved. The operation was not retried.'
        return result
    finally:
        correlation.reset(token)

def timeline(database, limit=200):
    events = []
    problems = []
    try:
        with connection(database) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE name='activity_events'").fetchone():
                events = [json.loads(row[0]) for row in db.execute('SELECT payload FROM activity_events ORDER BY seq DESC LIMIT ?', (limit,))]
    except (OSError, sqlite3.Error, ValueError):
        problems.append('Worker activity could not be read.')
    root = Path(database).parent
    for path in [root / 'desktop-activity.jsonl'] + [root / ('desktop-activity.jsonl.' + str(i)) for i in range(1, 5)]:
        try:
            if not path.exists():
                continue
            with path.open('rb') as stream:
                raw = stream.read(1048576 + 4096)
            for line in raw.splitlines():
                try:
                    event = json.loads(line)
                    if isinstance(event, dict):
                        events.append(event)
                except (ValueError, UnicodeError):
                    problems.append('An incomplete desktop event was skipped.')
        except OSError:
            problems.append('Desktop activity could not be read.')
    # Whitelist every export field, including native events, rather than copying log text.
    cleaned = []
    for event in events:
        if event.get('operation') not in OPERATIONS or event.get('actor') not in ACTORS or event.get('status') not in STATUSES:
            continue
        try:
            timestamp = datetime.fromisoformat(event['created_at'].replace('Z', '+00:00'))
            if timestamp.tzinfo is None or timestamp < datetime.now(timezone.utc) - timedelta(days=30):
                continue
        except (KeyError, ValueError, TypeError):
            continue
        item = {key: event[key] for key in ('actor', 'operation', 'status')}
        item['created_at'] = timestamp.isoformat()
        for key in ('event_id', 'request_id', 'case_id', 'record_id'):
            item[key] = safe_id(event.get(key, ''))
        item['error'] = event.get('error') if event.get('error') in ERRORS else 'none'
        item['elapsed_ms'] = event.get('elapsed_ms', 0) if type(event.get('elapsed_ms', 0)) is int else 0
        cleaned.append(item)
    cleaned.sort(key=lambda x: x['created_at'], reverse=True)
    return {'events': cleaned[:limit], 'warnings': list(dict.fromkeys(problems)),
            'retention': 'Metadata only: 30 days / 10,000 worker events; desktop logs rotate at 1 MB across 5 files. Case and run records have separate retention.'}

def export(database):
    from .case_store import atomic_text, json_text
    report = {'schema_version': 1, **timeline(database, 10000)}
    target = Path(database).parent / 'diagnostics' / ('activity-' + uuid4().hex[:12] + '.json')
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_text(target, json_text(report))
    return str(target)
