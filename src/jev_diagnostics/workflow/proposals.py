"""Validate concrete proposals without executing or granting approval."""
from .state_service import evidence_references
from .storage import bounded_text, digest
from .story_worlds import is_registered, scope, validate_proposal_inputs

def submit(store, db, case, host, summary, evidence_ids, check_id, expected_result,
           decisions=None, rationale=None):
    bounded_text(summary, 'Proposal summary', 4000)
    bounded_text(expected_result, 'Expected result', 4000)
    if not is_registered(check_id):
        raise ValueError('Only registered synthetic fixtures are runnable. Arbitrary commands and patches are not executed.')
    if not evidence_ids:
        raise ValueError('Attach evidence before proposing a check.')
    evidence_references(store, db, case['case_id'], evidence_ids)
    inputs = validate_proposal_inputs(case['snapshot'], check_id, decisions, rationale)
    based_on_revision = case["revision"]
    store.advance(db, case)
    values = {
        'summary': summary, 'submitted_by': host, 'evidence_ids': evidence_ids,
        'based_on_revision': based_on_revision, 'review_revision': case['revision'], 'check_id': check_id,
        'expected_result': expected_result, 'approval_required': True,
        'scope': scope(check_id), 'verification': 'Not performed'}
    if inputs is not None:
        values['inputs'] = inputs
    proposal = store.add(db, case['case_id'], 'proposal', values)
    return {'proposal': proposal, 'proposal_hash': digest(proposal), 'revision': case['revision']}
