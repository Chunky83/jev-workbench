"""Desktop-only approval bound to the reviewed record and current revision."""
from ..case_store import load_case
from .storage import digest
from .runner import execute

def approve_and_run(store, case_id, revision, proposal_id, proposal_hash):
    with store.transaction() as db:
        store.ensure_idle(db)
        case = store.get_case(db, case_id, expected=revision)
        source = db.execute('SELECT source FROM cases WHERE id=?', (case_id,)).fetchone()['source']
        if digest(load_case(source)) != digest(case['snapshot']):
            raise ValueError('The saved case changed. Share the new snapshot and request a new proposal.')
        proposal = store.record(db, case_id, 'proposal', proposal_id)
        if proposal["review_revision"] != revision:
            raise ValueError("New evidence or sharing changes require a new proposal.")
        if digest(proposal) != proposal_hash:
            raise ValueError('Proposal changed since review. Refresh before approving.')
        approvals = store.records(db, case_id, 'approval')
        if any(item['proposal_id'] == proposal_id for item in approvals):
            raise ValueError('This proposal was already approved. Submit a new proposal to repeat it.')
        if proposal['submitted_by'] not in case['shared_with']:
            raise ValueError('This connection has been revoked.')
        approval = store.add(db, case_id, 'approval', {'proposal_id': proposal_id,
            'proposal_hash': proposal_hash, 'revision': revision, 'approved_by': 'desktop_user'})
        run = store.add(db, case_id, 'run', {'proposal_id': proposal_id, 'approval_id': approval['id'],
            'revision': revision, 'status': 'running', 'verification': 'Not performed'})
    try:
        outcome = execute(proposal['check_id'])
        result = {'run_id': run['id'], 'status': 'completed', **outcome}
    except Exception:
        result = {'run_id': run['id'], 'status': 'failed', 'verification': 'Not performed',
                  'error': 'Registered check failed. No automatic retry.'}
    with store.transaction() as db:
        store.add(db, case_id, 'outcome', result)
    return result

def interrupt(store, case_id):
    with store.transaction() as db:
        completed = {item['run_id'] for item in store.records(db, case_id, 'outcome')}
        for run in store.records(db, case_id, 'run'):
            if run.get('approval_id') and run['id'] not in completed:
                store.add(db, case_id, 'outcome', {'run_id': run['id'], 'status': 'interrupted',
                    'verification': 'Not performed', 'summary': 'Desktop stopped the worker.'})
