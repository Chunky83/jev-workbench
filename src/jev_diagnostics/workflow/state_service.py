"""Explicit saved snapshots and immutable assistant-attributed evidence."""
import json
from pathlib import Path
from uuid import uuid4
from ..case_store import load_case, validate_case
from .storage import HOSTS, bounded_text, digest, encode

def share(store, folder, hosts):
    if not isinstance(hosts, list) or any(host not in HOSTS for host in hosts):
        raise ValueError('Choose supported connections.')
    source = str(Path(folder).resolve())
    snapshot = load_case(source)
    if len(encode(snapshot).encode('utf-8')) > 200000:
        raise ValueError('Shared snapshots must be below 200 KB.')
    from .library import register, metadata
    register(store, folder, snapshot)
    with store.transaction() as db:
        row = db.execute('SELECT payload FROM cases WHERE source=?', (source,)).fetchone()
        if row:
            case = json.loads(row['payload'])
            if metadata(db, case['case_id']).get('archived'):
                raise ValueError('Restore this case before sharing it again.')
            case.update(snapshot=snapshot, shared_with=hosts, evaluation_limit=0, evaluations_used=0)
            store.advance(db, case)
        else:
            case = {'workflow_schema_version': 1, 'case_id': 'case-' + uuid4().hex,
                    'revision': 'rev-' + uuid4().hex, 'snapshot': snapshot, 'shared_with': hosts,
                    'evaluation_limit': 0, 'evaluations_used': 0}
            db.execute('INSERT INTO cases VALUES (?,?,?)', (case['case_id'], source, encode(case)))
        from ..activity import insert
        insert(db, 'desktop', 'share', 'recorded', case_id=case['case_id'], record_id=case['revision'])
        return case

def evidence_references(store, db, case_id, ids):
    if not isinstance(ids, list) or len(ids) > 30 or any(not isinstance(item, str) for item in ids):
        raise ValueError('Supply at most 30 evidence identifiers.')
    return [store.record(db, case_id, 'evidence', item) for item in ids]

def submit_evidence(store, db, case, host, content, origin):
    bounded_text(content, 'Evidence excerpt')
    bounded_text(origin, 'Evidence origin', 500)
    record = store.add(db, case['case_id'], 'evidence', {
        'content': content, 'origin': origin, 'submitted_by': host,
        'classification': 'assistant_observation', 'verification': 'Not independently verified',
        'content_hash': digest(content), 'based_on_revision': case['revision']})
    store.advance(db, case)
    return {'evidence': record, 'revision': case['revision']}

def propose_state(store, db, case, host, state, evidence_ids):
    evidence_references(store, db, case['case_id'], evidence_ids)
    if not isinstance(state, dict) or len(encode(state).encode('utf-8')) > 32000:
        raise ValueError('Proposed state must be an object below 32 KB.')
    validate_case(dict(case['snapshot'], state=state))
    record = store.add(db, case['case_id'], 'state', {'state': state, 'evidence_ids': evidence_ids,
        'submitted_by': host, 'based_on_revision': case['revision'], 'status': 'pending_desktop_review'})
    store.advance(db, case)
    return {'proposal': record, 'revision': case['revision']}
