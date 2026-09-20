"""Desktop-only case catalogue and derived history. Never grants assistant access."""
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from ..case_store import load_case
from .storage import encode, now, digest


def metadata(db, case_id):
    row = db.execute('SELECT payload FROM desktop_case_meta WHERE case_id=?', (case_id,)).fetchone()
    return json.loads(row['payload']) if row else {}


def local_run_change_state(store):
    """Return cheap file metadata that changes when visible desktop run results do."""
    paths = sorted((store.path.parent / 'runs').glob('*/result.json'), reverse=True)[:1000]
    state = []
    for path in paths:
        try:
            details = path.stat()
            state.append((path.parent.name, details.st_size, details.st_mtime_ns,
                          details.st_ctime_ns, details.st_ino))
        except OSError:
            state.append((path.parent.name, None))
    return state


def put_metadata(db, case_id, value):
    db.execute('INSERT OR REPLACE INTO desktop_case_meta VALUES (?,?)', (case_id, encode(value)))


def register(store, folder, snapshot=None, *, sample=False):
    source = str(Path(folder).resolve())
    saved = snapshot if snapshot is not None else load_case(source)
    with store.transaction() as db:
        row = db.execute('SELECT payload FROM cases WHERE source=?', (source,)).fetchone()
        if row:
            case = json.loads(row['payload'])
        else:
            case = {'workflow_schema_version': 1, 'case_id': 'case-' + uuid4().hex,
                    'revision': 'rev-' + uuid4().hex, 'snapshot': saved, 'shared_with': [],
                    'evaluation_limit': 0, 'evaluations_used': 0}
            db.execute('INSERT INTO cases VALUES (?,?,?)', (case['case_id'], source, encode(case)))
        meta = metadata(db, case['case_id'])
        stamp = now()
        meta.update(title=saved['title'], updated_at=stamp)
        meta.setdefault('created_at', stamp)
        meta.setdefault('archived', False)
        meta['sample'] = meta.get('sample', False) or sample
        put_metadata(db, case['case_id'], meta)
        return case['case_id']


def local_runs(store):
    """Read bounded local history; never infer ownership from names or input similarity."""
    values, warnings = [], []
    paths = sorted((store.path.parent / 'runs').glob('*/result.json'), reverse=True)
    if len(paths) > 1000:
        warnings.append('Showing the latest 1,000 desktop run files.')
    for path in paths[:1000]:
        try:
            if path.stat().st_size > 1_000_000:
                raise ValueError('Oversized run')
            item = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(item, dict) or not isinstance(item.get('run_id'), str):
                raise ValueError('Invalid run')
            item = dict(item)
            item.setdefault('created_at', datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat())
            values.append(item)
        except (OSError, ValueError, UnicodeError):
            warnings.append('An unreadable desktop run was skipped. Its file was kept.')
    return values, list(dict.fromkeys(warnings))


def verification_text(value):
    return value.get('status', 'Not performed') if isinstance(value, dict) else str(value or 'Not performed')


def approved_check_summary(run, outcome, proposals):
    checks = outcome.get('checks', {}) if outcome else {}
    source = checks.get('source') if isinstance(checks, dict) else None
    if isinstance(source, str) and source.strip():
        return source
    proposal = proposals.get(run.get('proposal_id'), {})
    check_id = proposal.get('check_id')
    if isinstance(check_id, str) and check_id:
        return 'Registered check ' + check_id + '; no real project was checked.'
    return 'Registered synthetic check; no real project was checked.'


def events_for(store, db, case_id, runs):
    events = []
    if case_id:
        records = {kind: store.records(db, case_id, kind) for kind in
                   ('evidence', 'state', 'proposal', 'approval', 'run', 'outcome')}
        labels = {'evidence': 'Assistant evidence', 'state': 'Suggested state',
                  'proposal': 'Check proposal', 'approval': 'Check approved'}
        for kind, label in labels.items():
            for item in records[kind]:
                events.append({'id': item['id'], 'created_at': item['created_at'], 'kind': kind,
                    'label': label, 'actor': 'built-in sample' if item.get('submitted_by') == 'preview' else item.get('submitted_by', 'desktop'),
                    'status': 'recorded', 'verification': 'Not performed',
                    'summary': item.get('summary') or item.get('origin') or label,
                    'proposal_id': item['id'] if kind == 'proposal' else item.get('proposal_id', ''),
                    'details': item})
        outcomes = {x['run_id']: x for x in records['outcome']}
        proposals = {x['id']: x for x in records['proposal']}
        for run in records['run']:
            outcome = outcomes.get(run['id'])
            assessment = run.get('kind') == 'jev_assessment'
            events.append({'id': run['id'], 'created_at': run['created_at'],
                'kind': 'jev_assessment' if assessment else 'assistant_check',
                'label': 'Jev assessment' if assessment else 'Approved sample check',
                'actor': 'assistant workflow', 'status': outcome['status'] if outcome else 'incomplete',
                'verification': verification_text(outcome.get('verification')) if outcome else 'Not performed',
                'summary': ('Model judgment; independent verification required.' if assessment
                            else approved_check_summary(run, outcome, proposals)),
                'proposal_id': run.get('proposal_id', ''),
                'details': {'run': run, 'outcome': outcome}})
    for result in runs:
        if (result.get('case_id') or '') != case_id:
            continue
        assessment = result.get('mode') == 'live'
        events.append({'id': result['run_id'], 'created_at': result['created_at'],
            'kind': 'jev_assessment' if assessment else 'local_check',
            'label': 'Jev assessment' if assessment else 'Sample check', 'actor': 'desktop',
            'status': 'incomplete' if result.get('status') == 'running' else result.get('status', 'incomplete'),
            'verification': verification_text(result.get('verification')),
            'summary': result.get('summary', 'No completed result recorded.'),
            'proposal_id': '', 'details': {'result': result}})
    return sorted(events, key=lambda x: (x['created_at'], x['id']), reverse=True)


def case_summary(store, db, row, runs):
    case = json.loads(row['payload'])
    meta = metadata(db, case['case_id'])
    manifest = Path(row['source']) / 'test.json'
    available = manifest.is_file()
    stamp = ''
    if available:
        try:
            stamp = datetime.fromtimestamp(manifest.stat().st_mtime, timezone.utc).isoformat()
        except OSError:
            available = False
    events = events_for(store, db, case['case_id'], runs)
    last = next((x for x in events if x['kind'] in ('local_check', 'assistant_check', 'jev_assessment')), None)
    return {'case_id': case['case_id'], 'title': meta.get('title', case['snapshot']['title']),
            'created_at': meta.get('created_at', stamp),
            'updated_at': max(meta.get('updated_at', stamp), events[0]['created_at'] if events else ''),
            'shared_with': [host for host in case['shared_with'] if host != 'preview'],
            'archived': meta.get('archived', False), 'available': available,
            'last_result': (last['label'] + ': ' + last['status'] + ' / ' + last['verification']) if last else 'No runs recorded'}


def list_cases(store, archived=False):
    runs, warnings = local_runs(store)
    with store.transaction() as db:
        rows = db.execute('SELECT * FROM cases').fetchall()
        items = [case_summary(store, db, row, runs) for row in rows
                 if bool(metadata(db, row['id']).get('archived', False)) == bool(archived)]
    items.sort(key=lambda x: (x['updated_at'], x['case_id']), reverse=True)
    return {'cases': items, 'archived': bool(archived), 'warnings': warnings,
            'unlinked_count': sum(1 for x in runs if not x.get('case_id'))}


def timeline(store, case_id):
    runs, warnings = local_runs(store)
    with store.transaction() as db:
        case = None
        if case_id:
            store.get_case(db, case_id)
            row = db.execute('SELECT * FROM cases WHERE id=?', (case_id,)).fetchone()
            case = case_summary(store, db, row, runs)
        events = events_for(store, db, case_id, runs)
    shown, size = [], 0
    for event in events:
        if len(encode(event['details']).encode('utf-8')) > 64000:
            event['details'] = {'notice': 'Large record details omitted from this view; original files are retained.'}
        count = len(encode(event).encode('utf-8'))
        if size + count > 2_000_000 or len(shown) >= 300:
            warnings.append('This view is limited to 300 events and 2 MB. Older records are retained.')
            break
        shown.append(event)
        size += count
    events = shown
    return {'case': case, 'events': events, 'warnings': warnings,
            'notice': 'Latest 100 records per assistant record type; up to 1,000 desktop run files. Reading history does not run a check.' if case_id else 'These runs have no saved-case link. Names alone cannot identify a case.'}


def open_case(store, case_id):
    with store.transaction() as db:
        store.get_case(db, case_id)
        if metadata(db, case_id).get('archived'):
            raise ValueError('Restore this case before opening it. Sharing stays off until you choose it.')
        source = db.execute('SELECT source FROM cases WHERE id=?', (case_id,)).fetchone()['source']
    try:
        saved = load_case(source)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ValueError('The saved files are unavailable or invalid. Use Open from folder to locate a valid saved case.') from error
    register(store, source, saved)
    return {'case': saved, 'folder': source}


def set_archived(store, case_id, archived):
    if type(archived) is not bool:
        raise ValueError('Choose archive or restore.')
    runs, _ = local_runs(store)
    with store.transaction() as db:
        case = store.get_case(db, case_id)
        if archived:
            if any(x['status'] == 'incomplete' for x in events_for(store, db, case_id, runs)):
                raise ValueError('This case has an incomplete run. Resolve it in its owning client before archiving.')
            case['shared_with'] = []
            case['evaluation_limit'] = case['evaluations_used']
            store.advance(db, case)
        meta = metadata(db, case_id)
        meta.update(archived=archived, updated_at=now())
        put_metadata(db, case_id, meta)
        from ..activity import insert
        insert(db, 'desktop', 'archive_case' if archived else 'restore_case', 'recorded', case_id=case_id)


def reusable_sample(store):
    with store.transaction() as db:
        for row in db.execute('SELECT * FROM cases ORDER BY rowid DESC').fetchall():
            meta = metadata(db, row['id'])
            if meta.get('archived'):
                continue
            legacy_sample = (Path(row['source']).parent == store.path.parent / 'preview-fixtures'
                and any(x.get('submitted_by') == 'preview' for x in store.records(db, row['id'], 'proposal')))
            if (meta.get('sample') or legacy_sample) and (Path(row['source']) / 'test.json').is_file():
                return row['source']
    return None
