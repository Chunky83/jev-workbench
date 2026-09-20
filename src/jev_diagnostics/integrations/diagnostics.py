"""A real SDK transport check, explicitly separate from signed-in Claude activity."""
import asyncio
import os
from pathlib import Path
import sqlite3
from .claude import validate_launcher


def physical_database_path(database):
    """Resolve an opened local file, including Windows AppData redirection.

    This diagnostic opens an existing file read-only. The path stays in the
    local desktop diagnostic result; it is not sent to assistant tools or logs.
    """
    path = Path(database)
    with path.open('rb') as stream:
        if os.name != 'nt':
            return str(path.resolve())
        import ctypes
        from ctypes import wintypes
        import msvcrt
        library = ctypes.WinDLL('kernel32', use_last_error=True)
        resolve = library.GetFinalPathNameByHandleW
        resolve.argtypes = [wintypes.HANDLE, wintypes.LPWSTR, wintypes.DWORD, wintypes.DWORD]
        resolve.restype = wintypes.DWORD
        result = ctypes.create_unicode_buffer(32768)
        size = resolve(msvcrt.get_osfhandle(stream.fileno()), result, len(result), 0)
        if not size:
            raise ctypes.WinError(ctypes.get_last_error())
        if size >= len(result):
            raise OSError('Physical database path exceeds the diagnostic limit.')
        return result.value


def database_identity(database, db):
    """Read existing identity; never initialize or migrate a database here."""
    identity = {'workspace_id': None, 'physical_database_path': None}
    try:
        row = db.execute("SELECT value FROM workflow_meta WHERE name='workspace_id'").fetchone()
    except sqlite3.OperationalError:
        # An older preview may not have workspace metadata yet.
        row = None
    if row and isinstance(row[0], str):
        value = row[0]
        if len(value) == 42 and value.startswith('workspace-') and all(
                character in '0123456789abcdef' for character in value[10:]):
            identity['workspace_id'] = value
    try:
        identity['physical_database_path'] = physical_database_path(database)
    except (OSError, ValueError) as error:
        # A failed identity lookup must not erase independently checked results.
        identity['identity_error'] = type(error).__name__
    return identity


async def protocol(launcher):
    # Initialize the embedded Windows dependencies before importing the SDK client.
    from ..connectors import mcp_server
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    import tempfile
    expected = {'list_cases', 'read_case', 'submit_evidence', 'propose_state', 'evaluate_case', 'submit_proposal', 'read_run'}
    settings = StdioServerParameters(command=launcher['command'],
        args=launcher['args'] + ['--diagnostic'], env={**os.environ, **launcher.get('env', {})})
    # Library stderr is transient, never included in exported diagnostics.
    with tempfile.TemporaryFile(mode='w+') as errors:
        async with stdio_client(settings, errlog=errors) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                available = await session.list_tools()
                if {tool.name for tool in available.tools} != expected:
                    raise ValueError('Unexpected tool registry.')
                result = await session.call_tool('list_cases', {})
                if result.isError:
                    raise ValueError('Case listing failed.')
    return {'status': 'passed', 'summary': 'Local connector started, completed its handshake, exposed all 7 expected tools and answered a read-only request. Claude itself has not been tested by this check.'}

def run(launcher):
    checks = []
    identity = {'workspace_id': None, 'physical_database_path': None}
    try:
        validate_launcher(launcher)
        checks.append({'name': 'Bundled runtime', 'status': 'passed'})
        from ..activity import connection, emit
        args = launcher['args']
        database = args[args.index('--database') + 1]
        with connection(database) as db:
            identity = database_identity(database, db)
            if db.execute('PRAGMA quick_check').fetchone()[0] != 'ok':
                raise RuntimeError('Database integrity check failed.')
        checks.append({'name': 'Workflow database integrity', 'status': 'passed'})
        if not emit(database, 'diagnostic', 'diagnostics', 'recorded'):
            raise RuntimeError('Activity could not be written.')
        checks.append({'name': 'Activity storage', 'status': 'passed'})
        result = asyncio.run(asyncio.wait_for(protocol(launcher), timeout=12))
        checks.append({'name': 'MCP handshake, 7 tools and read-only request', 'status': 'passed'})
        result['checks'] = checks
        result.update(identity)
        result['summary'] = 'Local diagnostics passed: runtime, database integrity, activity storage, connector handshake and all 7 tools. Next: approve setup if needed, restart Claude, and send the copied test request. This test does not prove Claude has connected.'
        return result
    except Exception as error:
        return {'status': 'failed', 'error': type(error).__name__, 'checks': checks, **identity,
                'summary': 'Local diagnostics failed. Keep Workbench in its complete package and inspect Activity. No Claude connection is claimed.'}
