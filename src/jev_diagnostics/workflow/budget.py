"""User-enabled, consumed-before-request Jev allowance per shared snapshot."""
def configure(store, db, case, limit):
    if type(limit) is not int or not 0 <= limit <= 3:
        raise ValueError('Jev allowance must be between zero and three calls.')
    case['evaluation_limit'] = case['evaluations_used'] + limit
    store.advance(db, case)
    from ..activity import insert
    insert(db, 'desktop', 'budget', 'recorded', case_id=case['case_id'], record_id=case['revision'])

def reserve(store, db, case):
    if case['evaluations_used'] >= case['evaluation_limit']:
        raise ValueError('Jev budget is disabled or exhausted. Enable an allowance in Workbench Connections.')
    case['evaluations_used'] += 1
    store.put_case(db, case)
    from ..activity import insert
    insert(db, 'worker', 'allowance_consumed', 'recorded', case_id=case['case_id'])
