"""Validate concrete proposals without executing or granting approval."""
from .state_service import evidence_references
from .storage import bounded_text, digest

def submit(store, db, case, host, summary, evidence_ids, check_id, expected_result):
    bounded_text(summary, 'Proposal summary', 4000)
    bounded_text(expected_result, 'Expected result', 4000)
    if check_id != 'guest_access_fixture':
        raise ValueError('Only the registered synthetic guest_access_fixture is runnable in this preview. Arbitrary commands and patches are not executed.')
    if not evidence_ids:
        raise ValueError('Attach evidence before proposing a check.')
    evidence_references(store, db, case['case_id'], evidence_ids)
    based_on_revision = case["revision"]
    store.advance(db, case)
    proposal = store.add(db, case['case_id'], 'proposal', {
        'summary': summary, 'submitted_by': host, 'evidence_ids': evidence_ids,
        'based_on_revision': based_on_revision, 'review_revision': case['revision'], 'check_id': check_id,
        'expected_result': expected_result, 'approval_required': True,
        'scope': 'Synthetic localhost fixture only; no project files or external hosts',
        'verification': 'Not performed'})
    return {'proposal': proposal, 'proposal_hash': digest(proposal), 'revision': case['revision']}
