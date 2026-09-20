"""Explicit synthetic preview fixture. Never impersonates a connected assistant."""
from uuid import uuid4
from ..case_store import save_case
from ..connectors.tool_handlers import Tools
from .state_service import share

def create(store, sample):
    folder = store.path.parent / 'preview-fixtures' / uuid4().hex
    sample = dict(sample, title='Synthetic connector walkthrough')
    save_case(folder, sample)
    case = share(store, folder, ['preview'])
    tools = Tools(store.path, 'preview')
    evidence = tools.call('submit_evidence', {'case_id': case['case_id'], 'expected_revision': case['revision'],
        'content': 'Synthetic reported symptom: guest requests should be denied while owner requests succeed. This excerpt is not a test result.',
        'origin': 'Built-in preview fixture; no Claude or ChatGPT connection'})
    tools.call('submit_proposal', {'case_id': case['case_id'], 'expected_revision': evidence['revision'],
        'summary': 'Synthetic walkthrough: verify guest denial and owner access in the localhost fixture.',
        'evidence_ids': [evidence['evidence']['id']], 'check_id': 'guest_access_fixture',
        'expected_result': 'Two observed assertions: guest HTTP 401 without protected content; owner HTTP 200 with synthetic content.'})
    return str(folder)
