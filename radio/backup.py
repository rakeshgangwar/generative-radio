"""Verified directory backups for one local-disk station; restore only while offline."""
import argparse
from contextlib import closing
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import tempfile
import time


JOB_COLUMNS = {'id', 'seed', 'seconds', 'bpm', 'status', 'attempts', 'updated',
               'path', 'error', 'analysis'}
STATUSES = {'pending', 'rendering', 'ready', 'served', 'failed'}


def _regular(root, name):
    path = root / name
    for part in [path, *path.parents]:
        if part == root.parent:
            break
        if part.is_symlink():
            raise ValueError(f'Symlink is not permitted: {name}')
    if not path.is_file():
        raise FileNotFoundError(f'Missing regular file: {name}')
    return path


def _digest(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def _read_db(path):
    db = sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=5)
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA trusted_schema=OFF')
    return db


def _jobs(path):
    with closing(_read_db(path)) as db:
        if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('SQLite quick_check failed')
        columns = {r[1] for r in db.execute('PRAGMA table_info(jobs)')}
        heartbeats = {r[1] for r in db.execute('PRAGMA table_info(heartbeats)')}
        if columns != JOB_COLUMNS or heartbeats != {'role', 'at'}:
            raise ValueError('Unsupported station database schema')
        rows = db.execute('SELECT id,status FROM jobs ORDER BY id').fetchall()
        if any(type(job_id) is not int or job_id <= 0 or status not in STATUSES
               for job_id, status in rows):
            raise ValueError('Invalid job identity or status')
        sequence = db.execute("SELECT seq FROM sqlite_sequence WHERE name='jobs'").fetchone()
        if rows and (not sequence or type(sequence[0]) is not int or sequence[0] < rows[-1][0]):
            raise ValueError('Invalid job allocation sequence')
        return rows


def _names(rows):
    required = {'radio.sqlite', 'audio/fallback.wav'}
    optional = {'midi/fallback.mid'}
    for job_id, status in rows:
        if status in {'ready', 'served'}:
            required.add(f'audio/{job_id}.wav')
        optional.add(f'midi/{job_id}.mid')
    return required, optional


def _copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    destination.chmod(0o600)


def verify_backup(backup: Path) -> dict:
    """Validate every byte and required queue file without modifying the bundle."""
    backup = Path(backup).absolute()
    manifest_path = _regular(backup, 'manifest.json')
    manifest = json.loads(manifest_path.read_text())
    if not isinstance(manifest, dict) or type(manifest.get('version')) is not int or manifest['version'] != 1:
        raise ValueError('Unsupported backup manifest version')
    files = manifest.get('files')
    if not isinstance(files, dict) or not files:
        raise ValueError('Manifest files must be a nonempty object')
    for name, entry in files.items():
        if not isinstance(name, str) or not re.fullmatch(r'radio\.sqlite|(?:audio/(?:fallback|[1-9][0-9]*)\.wav)|(?:midi/(?:fallback|[1-9][0-9]*)\.mid)', name):
            raise ValueError(f'Invalid backup path: {name!r}')
        if (not isinstance(entry, dict) or set(entry) != {'size', 'sha256'}
                or type(entry['size']) is not int or entry['size'] <= 0
                or not isinstance(entry['sha256'], str)
                or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])):
            raise ValueError(f'Invalid file metadata: {name}')
        path = _regular(backup, name)
        if path.stat().st_size != entry['size'] or _digest(path) != entry['sha256']:
            raise ValueError(f'Checksum or size mismatch: {name}')
    actual = set()
    for path in backup.rglob('*'):
        if path.is_symlink():
            raise ValueError('Backup contains a symlink')
        name = path.relative_to(backup).as_posix()
        if path.is_dir():
            if name not in {'audio', 'midi'}:
                raise ValueError(f'Unexpected backup directory: {name}')
        elif path.is_file():
            actual.add(name)
        else:
            raise ValueError(f'Non-regular backup entry: {name}')
    if actual != set(files) | {'manifest.json'}:
        raise ValueError('Backup contains missing or unlisted files')
    if 'radio.sqlite' not in files:
        raise ValueError('Database missing from manifest')
    rows = _jobs(backup / 'radio.sqlite')
    if (type(manifest.get('jobs')) is not int or manifest['jobs'] != len(rows)
            or type(manifest.get('created_at')) not in (int, float)
            or not math.isfinite(manifest['created_at']) or manifest['created_at'] <= 0):
        raise ValueError('Invalid backup summary')
    required, optional = _names(rows)
    if not required <= set(files) or not set(files) <= required | optional:
        raise ValueError('Manifest does not match the snapshot queue')
    return manifest


def _snapshot(data, staging):
    source = _regular(data, 'radio.sqlite')
    destination = staging / 'radio.sqlite'
    deadline = time.monotonic() + 30
    def progress(*_):
        if time.monotonic() > deadline:
            raise TimeoutError('SQLite backup exceeded 30 seconds')
    db = _read_db(source)
    target = sqlite3.connect(destination)
    try:
        db.backup(target, pages=256, progress=progress, sleep=.05)
        target.execute('PRAGMA journal_mode=DELETE')
    finally:
        db.close()
        target.close()
    destination.chmod(0o600)
    rows = _jobs(destination)
    required, optional = _names(rows)
    for name in sorted((required - {'radio.sqlite'}) | optional):
        try:
            source = _regular(data, name)
        except FileNotFoundError:
            if name in optional:
                continue
            raise
        _copy(source, staging / name)
    files = {name: {'size': path.stat().st_size, 'sha256': _digest(path)}
             for path in staging.rglob('*') if path.is_file()
             for name in [path.relative_to(staging).as_posix()]}
    manifest = {'version': 1, 'created_at': time.time(), 'jobs': len(rows), 'files': files}
    (staging / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (staging / 'manifest.json').chmod(0o600)
    verify_backup(staging)
    return manifest


def create_backup(data: Path, destination: Path) -> dict:
    """Read a live WAL database; never overwrite an existing destination."""
    data, destination = Path(data).absolute(), Path(destination).absolute()
    if destination.resolve().is_relative_to(data.resolve()):
        raise ValueError('Backup destination must be outside station data')
    _regular(data, 'radio.sqlite')
    destination.mkdir(mode=0o700)  # exclusive reservation; final manifest is the commit marker
    try:
        for attempt in range(3):
            with tempfile.TemporaryDirectory(prefix='.snapshot-', dir=destination) as temp:
                staging = Path(temp)
                try:
                    manifest = _snapshot(data, staging)
                except FileNotFoundError:
                    if attempt == 2:
                        raise
                    time.sleep(.1)
                    continue
                # Publish manifest last. An interrupted incomplete bundle fails verify.
                for path in list(staging.iterdir()):
                    if path.name != 'manifest.json':
                        path.rename(destination / path.name)
                (staging / 'manifest.json').rename(destination / 'manifest.json')
                return manifest
    except BaseException:
        shutil.rmtree(destination)
        raise


def restore_backup(backup: Path, data: Path) -> dict:
    """Verify, stage and restore offline into a nonexistent or empty data root."""
    backup, data = Path(backup).absolute(), Path(data).absolute()
    manifest = verify_backup(backup)
    if data.is_symlink() or backup.resolve().is_relative_to(data.resolve()) or data.resolve().is_relative_to(backup.resolve()):
        raise ValueError('Restore and backup paths must be separate non-symlink directories')
    if data.exists() and (not data.is_dir() or any(data.iterdir())):
        raise ValueError('Restore destination must be empty; existing data is never overwritten')
    existed = data.exists()
    if not existed:
        data.mkdir(mode=0o700)
    published = []
    try:
        with tempfile.TemporaryDirectory(prefix='.restore-', dir=data) as temp:
            staging = Path(temp)
            for name in [*manifest['files'], 'manifest.json']:
                _copy(_regular(backup, name), staging / name)
            verify_backup(staging)  # detect changes to source bundle during copying
            with closing(sqlite3.connect(staging / 'radio.sqlite')) as db, db:
                db.execute('PRAGMA journal_mode=DELETE')
                db.execute("UPDATE jobs SET status='pending',attempts=0,error=NULL,updated=? WHERE status='rendering'", (time.time(),))
                db.execute('DELETE FROM heartbeats')
                for job_id, in db.execute('SELECT id FROM jobs WHERE path IS NOT NULL').fetchall():
                    db.execute('UPDATE jobs SET path=? WHERE id=?', (str(data / f'audio/{job_id}.wav'), job_id))
            # Bundle metadata is not station state.
            (staging / 'manifest.json').unlink()
            for path in list(staging.iterdir()):
                target = data / path.name
                path.rename(target)
                published.append(target)
        return {'jobs': manifest['jobs'], 'data': str(data), 'verified_files': len(manifest['files'])}
    except BaseException:
        for path in published:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink(missing_ok=True)
        if not existed:
            data.rmdir()
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ['create', 'verify', 'restore']:
        child = sub.add_parser(command)
        child.add_argument('backup', type=Path)
        if command != 'verify':
            child.add_argument('--data', type=Path, default=Path(os.getenv('RADIO_DATA', '/data')))
    args = parser.parse_args()
    try:
        if args.command == 'create':
            result = create_backup(args.data, args.backup)
        elif args.command == 'restore':
            result = restore_backup(args.backup, args.data)
        else:
            result = verify_backup(args.backup)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f'{args.command}: {exc}\n')


if __name__ == '__main__':
    main()
