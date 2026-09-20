"""Fixed local registry: no shell strings, paths, patches, or dynamic imports."""
from ..local_checks import run_guest_fixture
from .verification import classify

def execute(check_id):
    if check_id != 'guest_access_fixture':
        raise ValueError('This check is not registered.')
    checks = run_guest_fixture()
    return {'checks': checks, 'verification': classify(checks)}
