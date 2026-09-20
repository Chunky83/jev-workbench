"""Bounded profile discovery and transactional setup; never a callable MCP tool."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from uuid import uuid4
from ..workflow.storage import now

SERVER = 'jev-workbench'
MAX_CONFIG = 2 * 1024 * 1024

def fingerprint(raw):
    return hashlib.sha256(raw).hexdigest() if raw is not None else 'absent'

def unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Claude settings contain duplicate keys. Resolve them in Claude before setup.')
        value[key] = item
    return value

def read_config(path):
    if path.is_symlink():
        raise ValueError('This settings file is a link. Automatic setup is unavailable for linked files.')
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_CONFIG + 1)
    except FileNotFoundError:
        return None, {}
    if len(raw) > MAX_CONFIG:
        raise ValueError('Claude settings are too large for automatic setup.')
    try:
        value = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=unique_object)
    except (UnicodeError, json.JSONDecodeError):
        raise ValueError('Claude settings could not be read as JSON. Your file has not been changed.') from None
    if not isinstance(value, dict) or not isinstance(value.get('mcpServers', {}), dict):
        raise ValueError('Claude settings have an unsupported structure. Your file has not been changed.')
    return raw, value

def candidates(env=None, platform=None):
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    if platform != 'win32':
        return [], ['Automatic setup is currently available on Windows.']
    found, warnings = [], []
    if env.get('APPDATA'):
        folder = Path(env['APPDATA']) / 'Claude'
        if folder.is_dir():
            found.append(('Claude Desktop', folder / 'claude_desktop_config.json'))
    if env.get('LOCALAPPDATA'):
        packages = Path(env['LOCALAPPDATA']) / 'Packages'
        try:
            for package in sorted(packages.glob('Claude_*')):
                folder = package / 'LocalCache' / 'Roaming' / 'Claude'
                if folder.is_dir():
                    found.append(('Claude Desktop (Microsoft Store)', folder / 'claude_desktop_config.json'))
        except OSError:
            warnings.append('Windows did not allow access to Microsoft Store profiles.')
    result = []
    for label, path in found:
        item = {'id': fingerprint(str(path.resolve()).encode()), 'label': label,
                'path': str(path), 'available': True}
        try:
            _, config = read_config(path)
            item['server_count'] = len(config.get('mcpServers', {}))
            item['has_jev'] = SERVER in config.get('mcpServers', {})
        except (OSError, ValueError) as error:
            item.update(available=False, problem=str(error) if isinstance(error, ValueError)
                        else 'Windows did not allow access to these settings.')
        result.append(item)
    return result, warnings

def initialize(store):
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS integration_plans (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS integration_activity (host TEXT PRIMARY KEY, seen TEXT NOT NULL, tool TEXT NOT NULL)')

def observed_call(store, host, tool):
    initialize(store)
    with store.transaction() as db:
        db.execute('INSERT OR REPLACE INTO integration_activity VALUES (?, ?, ?)', (host, now(), tool))

def status(store, launcher=None):
    initialize(store)
    profiles, warnings = candidates()
    for profile in profiles:
        profile['configured'] = False
        if profile['available'] and launcher:
            _, config = read_config(Path(profile['path']))
            profile['configured'] = config.get('mcpServers', {}).get(SERVER) == launcher
    with store.transaction() as db:
        activity = [dict(row) for row in db.execute('SELECT * FROM integration_activity')]
        row = db.execute('SELECT payload FROM integration_plans ORDER BY rowid DESC LIMIT 1').fetchone()
        plan = json.loads(row['payload']) if row else None
        if plan and plan['state'] == 'review' and plan.get('after'):
            # Reconcile a process exit between file replacement and receipt commit.
            # Exact bytes and the original backup must match before offering undo.
            try:
                current, _ = read_config(Path(plan['path']))
                backup_valid = plan.get('backup') is None or fingerprint(Path(plan['backup']).read_bytes()) == plan['before']
                if fingerprint(current) == plan['after'] and backup_valid:
                    plan.update(state='applied', applied=now())
                    db.execute('UPDATE integration_plans SET payload=? WHERE id=?', (json.dumps(plan), plan['id']))
            except (OSError, ValueError):
                pass
    # Only safe summary fields enter the UI; never other servers, environment values or backups.
    return {'profiles': profiles, 'warnings': warnings, 'activity': activity,
            'plan': public_plan(plan) if plan else None,
            'supported': sys.platform == 'win32'}

def public_plan(plan):
    return {key: plan[key] for key in ('id', 'kind', 'label', 'path', 'state', 'summary')}

def validate_launcher(launcher):
    if not isinstance(launcher, dict) or not Path(launcher.get('command', '')).is_file():
        raise ValueError('The bundled connection runtime is missing. Reopen Workbench from its complete package.')
    if not isinstance(launcher.get('args'), list) or 'jev_diagnostics.connectors.mcp_server' not in launcher['args']:
        raise ValueError('The connection launch settings are incomplete.')

def prepare(store, profile_id, launcher):
    initialize(store)
    validate_launcher(launcher)
    profiles, _ = candidates()
    profile = next((p for p in profiles if p['id'] == profile_id and p['available']), None)
    if not profile:
        raise ValueError('This Claude profile is unavailable. Scan again and select an available profile.')
    raw, config = read_config(Path(profile['path']))
    existing = config.get('mcpServers', {})
    if existing.get(SERVER) == launcher:
        raise ValueError('This profile is already configured. Restart Claude and ask it to list your Jev cases.')
    replacing = SERVER in existing
    plan = {'id': uuid4().hex, 'kind': 'setup', 'label': profile['label'], 'path': profile['path'],
            'before': fingerprint(raw), 'launcher': launcher, 'state': 'review',
            'created': now(), 'summary': ('Update' if replacing else 'Add') +
            ' the Jev Workbench connection. Preserve all other Claude settings and ' +
            str(len(existing) - int(replacing)) + ' other connections. Save a local backup first. '
            'No cases are shared by this action. Restart Claude yourself after setup.'}
    updated = dict(config)
    updated['mcpServers'] = dict(existing, **{SERVER: launcher})
    plan['after'] = fingerprint((json.dumps(updated, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8'))
    plan['backup'] = str(Path(profile['path']).with_name(Path(profile['path']).name + '.jev-backup-' + plan['id'])) if raw is not None else None
    with store.transaction() as db:
        db.execute("DELETE FROM integration_plans WHERE json_extract(payload, '$.state') = 'review'")
        db.execute('INSERT INTO integration_plans VALUES (?, ?)', (plan['id'], json.dumps(plan)))
    return 'Review the detected profile and change below, then approve setup.'

def windows_copy(source, destination, fail_if_exists=True):
    import ctypes
    from ctypes import wintypes
    library = ctypes.WinDLL('kernel32', use_last_error=True)
    function = library.CopyFileW
    function.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.BOOL]
    function.restype = wintypes.BOOL
    if not function(str(source), str(destination), fail_if_exists):
        raise ctypes.WinError(ctypes.get_last_error())

def windows_replace(source, destination):
    import ctypes
    from ctypes import wintypes
    library = ctypes.WinDLL('kernel32', use_last_error=True)
    function = library.ReplaceFileW
    function.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR,
                        wintypes.DWORD, wintypes.LPVOID, wintypes.LPVOID]
    function.restype = wintypes.BOOL
    # Do not ignore ACL merge failures. Retain the original Windows permissions.
    if not function(str(destination), str(source), None, 0, None, None):
        raise ctypes.WinError(ctypes.get_last_error())

def atomic_write(path, raw, mode=None):
    descriptor, temporary = tempfile.mkstemp(prefix='.jev-setup-', dir=path.parent)
    os.close(descriptor)
    try:
        if os.name == 'nt' and path.exists():
            windows_copy(path, temporary, False)
        with open(temporary, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if mode is not None:
            os.chmod(temporary, mode)
        if os.name == 'nt' and path.exists():
            windows_replace(temporary, path)
        else:
            os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)

def apply(store, plan_id):
    initialize(store)
    with store.transaction() as db:
        row = db.execute('SELECT payload FROM integration_plans WHERE id=?', (plan_id,)).fetchone()
        if not row:
            raise ValueError('Setup review expired. Review setup again.')
        plan = json.loads(row['payload'])
        if plan['state'] != 'review':
            raise ValueError('This setup was already applied. Check the connection next.')
        if datetime.now(timezone.utc) - datetime.fromisoformat(plan['created']) > timedelta(minutes=15):
            raise ValueError('Setup review expired. Review setup again.')
        path = Path(plan['path'])
        raw, config = read_config(path)
        if fingerprint(raw) != plan['before']:
            raise ValueError('Claude settings changed after review. Nothing was replaced. Review setup again.')
        mode = stat.S_IMODE(path.stat().st_mode) if raw is not None else None
        backup = path.with_name(path.name + '.jev-backup-' + plan['id'])
        if raw is not None:
            if os.name == 'nt':
                windows_copy(path, backup)
            else:
                with backup.open('xb') as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.chmod(backup, mode)
            if fingerprint(backup.read_bytes()) != plan['before']:
                raise ValueError('Claude settings changed while creating the backup. Review setup again.')
        config.setdefault('mcpServers', {})[SERVER] = plan['launcher']
        updated = (json.dumps(config, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')
        # Detect intervening external edits immediately before replacement.
        latest, _ = read_config(path)
        if fingerprint(latest) != plan['before']:
            raise ValueError('Claude settings changed during setup. Nothing was replaced. Review setup again.')
        atomic_write(path, updated, mode)
        plan.update(state='applied', backup=str(backup) if raw is not None else None,
                    after=fingerprint(updated), applied=now())
        db.execute('UPDATE integration_plans SET payload=? WHERE id=?', (json.dumps(plan), plan_id))
    return 'Setup saved. Quit and reopen Claude when you are ready, then ask: “List my Jev Workbench cases.” Return here and select Check for Claude request.'

def restore(store, plan_id):
    """Explicit desktop undo; refuse to overwrite later edits by another program."""
    initialize(store)
    with store.transaction() as db:
        row = db.execute('SELECT payload FROM integration_plans WHERE id=?', (plan_id,)).fetchone()
        if not row:
            raise ValueError('No setup to undo.')
        plan = json.loads(row['payload'])
        if plan['state'] != 'applied':
            raise ValueError('This setup cannot be undone again.')
        path = Path(plan['path'])
        current, _ = read_config(path)
        if fingerprint(current) != plan['after']:
            raise ValueError('Claude settings changed since setup. Automatic undo stopped to preserve those edits.')
        if plan['backup']:
            backup = Path(plan['backup']).read_bytes()
            if fingerprint(backup) != plan['before']:
                raise ValueError('The setup backup changed. Automatic undo stopped.')
            atomic_write(path, backup, stat.S_IMODE(path.stat().st_mode))
        else:
            path.unlink()
        plan['state'] = 'undone'
        db.execute('UPDATE integration_plans SET payload=? WHERE id=?', (json.dumps(plan), plan_id))
    return 'Previous Claude settings restored. Restart Claude when ready. Case sharing is unchanged.'
