"""The only assistant-callable surface. No approval or execution route."""
import json
from ..workflow.storage import HOSTS, Store
from ..workflow.state_service import submit_evidence, propose_state
from ..workflow.proposals import submit
from ..workflow.budget import reserve
from ..workflow.run_views import current_run, recent_runs

class Tools:
    def __init__(self, database, host):
        if host not in HOSTS:
            raise ValueError('Unsupported connection identity.')
        self.store = Store(database)
        self.host = host

    def call(self, name, args):
        if name not in ('list_cases', 'read_case', 'submit_evidence', 'propose_state',
                        'evaluate_case', 'submit_proposal', 'read_run'):
            raise ValueError('Unsupported tool. Assistants cannot approve or execute actions.')
        if name == 'evaluate_case':
            return self.evaluate(**args)
        with self.store.transaction() as db:
            if name == 'list_cases':
                rows = db.execute('SELECT payload FROM cases').fetchall()
                cases = [json.loads(row['payload']) for row in rows]
                return {'workspace_id': db.execute("SELECT value FROM workflow_meta WHERE name='workspace_id'").fetchone()[0], 'cases': [{'case_id': case['case_id'], 'title': case['snapshot']['title'],
                                  'revision': case['revision']} for case in cases if self.host in case['shared_with']]}
            case = self.store.get_case(db, args['case_id'], self.host,
                args.get('expected_revision') if name not in ('read_case', 'read_run') else None)
            if name not in ('read_case', 'read_run') and not args.get('expected_revision'):
                raise ValueError('An expected_revision is required for writes.')
            if name == 'read_case':
                return {'workspace_id': db.execute("SELECT value FROM workflow_meta WHERE name='workspace_id'").fetchone()[0], 'case': case, 'evidence': self.store.records(db, case['case_id'], 'evidence')[:20],
                        'recent_runs': recent_runs(self.store, db, case['case_id']),
                        'next_step': 'After desktop approval, read this case again to find the proposal_id and run_id in recent_runs, then call read_run for the stored outcome.',
                        'warning': 'Assistant observations and Jev assessments are hypotheses, not verified outcomes.'}
            if name == 'submit_evidence':
                return submit_evidence(self.store, db, case, self.host, args['content'], args['origin'])
            if name == 'propose_state':
                return propose_state(self.store, db, case, self.host, args['state'], args['evidence_ids'])
            if name == 'submit_proposal':
                return submit(self.store, db, case, self.host, args['summary'], args['evidence_ids'],
                              args['check_id'], args['expected_result'],
                              args.get('decisions'), args.get('rationale'))
            run = self.store.record(db, case['case_id'], 'run', args['run_id'])
            outcomes = self.store.records(db, case['case_id'], 'outcome')
            outcome = next((item for item in outcomes if item['run_id'] == run['id']), None)
            return {'current': current_run(run, outcome), 'run': run,
                    'outcome': outcome or {'status': 'incomplete', 'verification': 'Not performed'},
                    'note': 'run is the immutable start record; current and outcome describe the latest stored result.'}

    def evaluate(self, case_id, expected_revision):
        from ..worker import run_case
        with self.store.transaction() as db:
            if not expected_revision:
                raise ValueError('An expected_revision is required.')
            case = self.store.get_case(db, case_id, self.host, expected_revision)
            self.store.ensure_idle(db)
            reserve(self.store, db, case)
            run = self.store.add(db, case_id, 'run', {'revision': expected_revision,
                'snapshot': case['snapshot'], 'kind': 'jev_assessment', 'status': 'running',
                'verification': 'Not performed'})
        result = run_case({'case': case['snapshot'], 'mode': 'live',
                          'runs_folder': str(self.store.path.parent / 'connector-runs')})
        # Do not expose local paths or arbitrary exception text to the assistant.
        outcome = {'run_id': run['id'], 'status': result['status'], 'verification': 'Not performed',
                   'response': result.get('response'), 'summary': 'Jev assessment; independent verification required.'}
        with self.store.transaction() as db:
            self.store.add(db, case_id, 'outcome', outcome)
            self.store.get_case(db, case_id, self.host)
        return outcome
