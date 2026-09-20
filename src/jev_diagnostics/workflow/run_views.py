"""Current run views derived from immutable starts and final outcomes."""

def current_run(run, outcome=None):
    # A start record stays immutable. Only a stored outcome establishes
    # completion or verification; elapsed time never implies success.
    return {
        'run_id': run['id'],
        'proposal_id': run.get('proposal_id'),
        'revision': run.get('revision'),
        'created_at': run['created_at'],
        'status': outcome['status'] if outcome else 'incomplete',
        'verification': outcome.get('verification', 'Not performed') if outcome else 'Not performed',
    }

def recent_runs(store, db, case_id):
    outcomes = {item['run_id']: item for item in store.records(db, case_id, 'outcome')}
    return [current_run(run, outcomes.get(run['id']))
            for run in store.records(db, case_id, 'run')[:20]]
