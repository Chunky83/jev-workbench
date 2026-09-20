"""Desktop-wide incoming proposals, independent of the editor's selected folder."""
import json
from .storage import digest

def snapshot(store):
    with store.transaction() as db:
        workspace_id = db.execute("SELECT value FROM workflow_meta WHERE name='workspace_id'").fetchone()[0]
        # Newest submissions across all cases. Never depend on the selected editor folder.
        rows = db.execute("SELECT id,case_id FROM records WHERE kind='proposal' ORDER BY rowid DESC LIMIT 500").fetchall()
        approved = {json.loads(row['payload'])['proposal_id'] for row in db.execute("SELECT payload FROM records WHERE kind='approval'")}
        items = []
        from .library import metadata
        for row in rows:
            if metadata(db, row['case_id']).get('archived'):
                continue
            proposal = store.record(db, row['case_id'], 'proposal', row['id'])
            if proposal['submitted_by'] == 'preview' or proposal['id'] in approved:
                continue
            case = store.get_case(db, row['case_id'])
            status = 'ready'
            if proposal['submitted_by'] not in case['shared_with']:
                status = 'revoked'
            elif proposal['review_revision'] != case['revision']:
                status = 'stale'
            items.append({'case_id': case['case_id'], 'proposal_id': proposal['id'],
                'title': case['snapshot']['title'][:160], 'submitted_by': proposal['submitted_by'],
                'created_at': proposal['created_at'], 'summary': proposal['summary'][:400],
                'revision': case['revision'], 'status': status})
        # Desktop history refreshes only when authoritative case/record state changes.
        # Repeated polling must not disable the editors or reset a scrolled list.
        revisions = [(row['id'], json.loads(row['payload'])['revision'])
                     for row in db.execute('SELECT id,payload FROM cases ORDER BY id')]
        metadata_rows = [tuple(row) for row in db.execute('SELECT * FROM desktop_case_meta ORDER BY case_id')]
        newest_record = db.execute('SELECT MAX(rowid) FROM records').fetchone()[0]
        change_token = digest([revisions, metadata_rows, newest_record])
        return {'workspace_id': workspace_id, 'change_token': change_token, 'proposals': items,
                'limit': 500, 'notice': 'Showing the latest 500 submissions.' if len(rows) == 500 else ''}

def review(store, case_id, proposal_id):
    with store.transaction() as db:
        case = store.get_case(db, case_id)
        selected = store.record(db, case_id, 'proposal', proposal_id)
        records = {kind: store.records(db, case_id, kind) for kind in
                   ('evidence', 'state', 'proposal', 'approval', 'run', 'outcome')}
        # Always retain the explicitly selected record, even when it is stale.
        selected['review_hash'] = digest(selected)
        records['proposal'] = [selected]
        return {'case': case, 'records': records, 'proposal_id': proposal_id,
                'workspace_id': db.execute("SELECT value FROM workflow_meta WHERE name='workspace_id'").fetchone()[0]}
