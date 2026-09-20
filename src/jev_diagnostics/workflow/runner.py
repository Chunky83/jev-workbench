"""Fixed local registry: no shell strings, paths, patches, or dynamic imports."""
from ..local_checks import run_guest_fixture
from .story_worlds import run_fixture
from .verification import classify

def execute(check_id, inputs=None):
    if check_id == 'guest_access_fixture':
        if inputs is not None:
            raise ValueError('The guest-access fixture does not accept additional inputs.')
        checks = run_guest_fixture()
    else:
        checks = run_fixture(check_id, inputs)
    return {'checks': checks, 'verification': classify(checks)}
