"""Desktop commands, deliberately separate from MCP's tool registry."""
import json
from pathlib import Path
from .storage import Store, digest
from .state_service import share
from .budget import configure
from .approvals import approve_and_run, interrupt

def dispatch(message):
    store = Store(message['database'])
    operation = message.get('operation', 'status')
    folder = message.get('folder', '')
    if operation in ('case_list', 'case_history', 'open_case', 'archive_case', 'restore_case'):
        from . import library
        if operation == 'open_case':
            return {'opened_case': library.open_case(store, message['case_id'])}
        if operation == 'case_history':
            return {'case_history': library.timeline(store, message.get('case_id', ''))}
        if operation in ('archive_case', 'restore_case'):
            library.set_archived(store, message['case_id'], operation == 'archive_case')
        return {'case_list': library.list_cases(store, message.get('archived', False))}
    from .inbox import snapshot, review
    if operation == 'inbox':
        return {'inbox': snapshot(store)}
    if operation == 'review_proposal':
        return {'review': review(store, message['case_id'], message['proposal_id'])}
    from ..integrations import claude
    notice = ''
    diagnostic = None
    export_path = None
    from ..activity import timeline, export
    if operation == 'diagnostics':
        from ..integrations.diagnostics import run
        diagnostic = run(message['launcher'])
        notice = diagnostic['summary']
    if operation == 'activity_export':
        export_path = export(store.path)
        notice = 'Metadata-only activity report saved. No case contents, credentials or configuration backups are included.'
    if operation == 'setup_review':
        notice = claude.prepare(store, message['profile_id'], message['launcher'])
    elif operation == 'setup_cancel':
        claude.initialize(store)
        with store.transaction() as db:
            db.execute("DELETE FROM integration_plans WHERE id=? AND json_extract(payload, '$.state')='review'", (message['plan_id'],))
        notice = 'Setup review cancelled. Claude settings were not changed by cancellation.'
    elif operation == 'setup_apply':
        notice = claude.apply(store, message['plan_id'])
    elif operation == 'setup_undo':
        notice = claude.restore(store, message['plan_id'])
    integration = claude.status(store, message.get('launcher'))
    if operation == 'connection_check':
        activity = next((item for item in integration['activity'] if item['host'] == 'claude'), None)
        notice = ('Last successful local Claude tool request: ' + activity['tool'] + ' at ' + activity['seen'] + '. This is historical activity, not a live account login check.') if activity else 'No Claude tool request received yet. After approving setup, quit and reopen Claude, then ask it to list your Jev Workbench cases.'
    if operation == 'demo':
        from .demo import create
        folder = create(store, message['sample'], fresh=message.get('fresh', True))
    if operation == 'share':
        share(store, folder, message['hosts'])
    if operation in ('approve', 'interrupt'):
        if operation == 'approve':
            approve_and_run(store, message['case_id'], message['revision'],
                            message['proposal_id'], message['proposal_hash'])
        else:
            interrupt(store, message['case_id'])
    with store.transaction() as db:
        row = db.execute('SELECT payload FROM cases WHERE source=?',
                         (str(Path(folder).resolve()),)).fetchone() if folder else None
        case = json.loads(row['payload']) if row else None
        if operation in ('budget', 'revoke'):
            if not case:
                raise ValueError('Share a saved case first.')
            if operation == 'budget':
                configure(store, db, case, message['limit'])
            else:
                case['shared_with'] = []
                case['evaluation_limit'] = case['evaluations_used']
                store.advance(db, case)
                from ..activity import insert
                insert(db, 'desktop', 'revoke', 'recorded', case_id=case['case_id'], record_id=case['revision'])
        records = {}
        if case:
            for kind in ('evidence', 'state', 'proposal', 'run', 'outcome', 'approval'):
                records[kind] = store.records(db, case['case_id'], kind)
            for proposal in records['proposal']:
                proposal['review_hash'] = digest(proposal)
        if operation == 'share':
            notice = 'Saved snapshot shared with ' + ', '.join(case['shared_with']) + '. Copy the case request and send it to your assistant.'
        elif operation == 'demo':
            notice = 'Sample saved. Review its check here, or choose Share case in the workspace to involve an assistant.'
    activity = timeline(store.path) if operation in ('activity', 'activity_export', 'diagnostics') else None
    from ..case_store import load_case
    from .library import metadata
    saved_snapshot_current = None
    archived = False
    if case:
        with store.transaction() as db:
            archived = bool(metadata(db, case['case_id']).get('archived', False))
        try:
            saved_snapshot_current = digest(load_case(folder)) == digest(case['snapshot'])
        except (OSError, ValueError, KeyError, TypeError):
            saved_snapshot_current = False
    response = {'workflow': {'case': case, 'records': records, 'saved_snapshot_current': saved_snapshot_current, 'archived': archived, 'integration': integration,
            'notice': notice, 'database': str(store.path), 'activity': activity, 'diagnostic': diagnostic, 'export_path': export_path,
            **({'demo_folder': folder, 'demo_case': load_case(folder)} if operation == 'demo' else {})}}
    if operation == 'approve' and message.get('incoming_review'):
        response['review'] = review(store, message['case_id'], message['proposal_id'])
    return response
