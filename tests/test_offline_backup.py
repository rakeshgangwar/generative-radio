import hashlib
import inspect
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from radio.backup import create_backup, restore_backup, verify_backup
from radio.config import Config
from radio.store import Store


class OfflineBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root/'station'
        self.data.mkdir()
        (self.data/'audio').mkdir()
        (self.data/'audio/fallback.wav').write_bytes(b'isolated fallback')
        self.config = Config(self.data,20,20,60,90,'unused')
        store = Store(self.data)
        store.enqueue(self.config)
        store.enqueue(self.config)
        store.db.close()
        self.backup = self.root/'backup'
        self.assertFalse((self.data/'radio.sqlite-shm').exists())

    def fingerprint(self, data):
        return {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in data.rglob('*') if p.is_file()}

    def offline(self, data=None):
        self.assertIn('offline', inspect.signature(create_backup).parameters,
                      'create_backup needs explicit offline mode')
        return create_backup(data or self.data,self.backup,offline=True)

    def test_closed_wal_source_is_unchanged_and_private_sidecars_do_not_leak(self):
        before = self.fingerprint(self.data)
        result = self.offline()
        self.assertEqual(result['version'],1)
        self.assertEqual(result['jobs'],2)
        self.assertEqual(set(result['files']),{'radio.sqlite','audio/fallback.wav'})
        self.assertEqual(self.fingerprint(self.data),before)
        self.assertFalse((self.data/'radio.sqlite-shm').exists())
        self.assertEqual(verify_backup(self.backup),result)
        restore_backup(self.backup,self.root/'restored')
        with sqlite3.connect(self.root/'restored/radio.sqlite') as db:
            self.assertEqual(db.execute('SELECT id,seed FROM jobs ORDER BY id').fetchall(),[(1,91),(2,92)])
        self.assertEqual({p.name for p in self.backup.iterdir()},{'radio.sqlite','audio','manifest.json'})

    def test_committed_wal_frames_survive_without_source_shm(self):
        store = Store(self.data)
        with store.db:
            store.db.execute("UPDATE jobs SET seed=123456 WHERE id=2")
            store.db.execute("INSERT INTO jobs(seed,seconds,bpm,status,updated) VALUES (777,20,60,'pending',1)")
        crashed = self.root/'crashed'
        (crashed/'audio').mkdir(parents=True)
        shutil.copyfile(self.data/'audio/fallback.wav',crashed/'audio/fallback.wav')
        for name in ['radio.sqlite','radio.sqlite-wal']:
            shutil.copyfile(self.data/name,crashed/name)
        store.db.close()
        with sqlite3.connect((crashed/'radio.sqlite').as_uri()+'?immutable=1',uri=True) as db:
            self.assertEqual(db.execute('SELECT seed FROM jobs WHERE id=2').fetchone()[0],92)
            self.assertEqual(db.execute('SELECT count(*) FROM jobs').fetchone()[0],2)
        before = self.fingerprint(crashed)
        self.assertEqual(self.offline(crashed)['jobs'],3)
        self.assertEqual(self.fingerprint(crashed),before)
        self.assertFalse((crashed/'radio.sqlite-shm').exists())
        with sqlite3.connect(self.backup/'radio.sqlite') as db:
            self.assertEqual(db.execute('SELECT id,seed FROM jobs ORDER BY id').fetchall(),[(1,91),(2,123456),(3,777)])
            self.assertEqual(db.execute("SELECT seq FROM sqlite_sequence WHERE name='jobs'").fetchone()[0],3)

    def test_hot_rollback_journal_is_recovered_only_in_private_copy(self):
        code = '''import sqlite3,os,sys
p=sys.argv[1];d=sqlite3.connect(p);d.execute('PRAGMA journal_mode=DELETE');d.execute('PRAGMA cache_size=1');d.execute('BEGIN IMMEDIATE');d.execute('UPDATE jobs SET seed=999999');d.execute('CREATE TABLE spill(payload BLOB)')
for _ in range(40):d.execute('INSERT INTO spill VALUES (zeroblob(10000))')
os._exit(0)
'''
        subprocess.run([sys.executable,'-c',code,str(self.data/'radio.sqlite')],check=True)
        self.assertTrue((self.data/'radio.sqlite-journal').exists())
        before = self.fingerprint(self.data)
        self.offline()
        self.assertEqual(self.fingerprint(self.data),before)
        with sqlite3.connect(self.backup/'radio.sqlite') as db:
            self.assertEqual(db.execute('SELECT seed FROM jobs ORDER BY id').fetchall(),[(91,),(92,)])
            self.assertFalse(db.execute("SELECT name FROM sqlite_master WHERE name='spill'").fetchall())

    def test_symlink_or_directory_sidecars_fail_without_partial_bundle(self):
        self.assertIn('offline',inspect.signature(create_backup).parameters)
        for suffix in ['-wal','-journal']:
            for kind in ['symlink','directory']:
                sidecar=self.data/('radio.sqlite'+suffix)
                if kind=='symlink':sidecar.symlink_to(self.data/'radio.sqlite')
                else:sidecar.mkdir()
                with self.subTest(suffix=suffix,kind=kind),self.assertRaises(ValueError):
                    create_backup(self.data,self.backup,offline=True)
                self.assertFalse(self.backup.exists())
                if kind=='directory':sidecar.rmdir()
                else:sidecar.unlink()

    def test_observed_source_changes_abort_instead_of_retrying_a_different_state(self):
        self.assertIn('offline',inspect.signature(create_backup).parameters)
        original=shutil.copyfile
        for change in ['database','sidecar_appears']:
            touched=[]
            def copy(source,target):
                result=original(source,target)
                if Path(source)==self.data/'radio.sqlite' and not touched:
                    touched.append(True)
                    if change=='database':
                        with (self.data/'radio.sqlite').open('ab') as f:f.write(b'x')
                    else:(self.data/'radio.sqlite-wal').write_bytes(b'concurrent WAL')
                return result
            with self.subTest(change=change),patch('radio.backup.shutil.copyfile',side_effect=copy):
                with self.assertRaisesRegex(ValueError,'changed'):
                    create_backup(self.data,self.backup,offline=True)
            self.assertTrue(touched)
            self.assertFalse(self.backup.exists())

    def test_disappearing_wal_is_not_silently_retried_without_its_commits(self):
        self.assertIn('offline',inspect.signature(create_backup).parameters)
        wal=self.data/'radio.sqlite-wal';wal.write_bytes(b'fixture WAL')
        original=shutil.copyfile
        def copy(source,target):
            if Path(source)==wal:
                wal.unlink()
                raise FileNotFoundError('writer removed WAL')
            return original(source,target)
        with patch('radio.backup.shutil.copyfile',side_effect=copy):
            with self.assertRaisesRegex(ValueError,'changed'):
                create_backup(self.data,self.backup,offline=True)
        self.assertFalse(self.backup.exists())

    def test_offline_option_requires_an_actual_boolean(self):
        self.assertIn('offline',inspect.signature(create_backup).parameters)
        for value in [None,0,1,'false']:
            with self.subTest(value=value),self.assertRaises(ValueError):
                create_backup(self.data,self.backup,offline=value)
        self.assertFalse(self.backup.exists())

    @unittest.skipIf(os.name != 'posix' or getattr(os, 'geteuid', lambda: 0)() == 0,
                     'requires actual non-root directory permissions')
    def test_deferred_readonly_wal_error_has_actionable_guidance(self):
        self.data.chmod(0o555)
        observed = None
        try:
            try:
                create_backup(self.data, self.backup)
            except Exception as exc:
                observed = exc
        finally:
            self.data.chmod(0o755)
        self.assertIsInstance(observed, ValueError)
        self.assertIn('--offline', str(observed))
        self.assertFalse(self.backup.exists())

    def test_cli_offline_is_create_only_and_help_requires_stopped_writers(self):
        command=[sys.executable,'-m','radio.backup']
        result=subprocess.run(command+['create',str(self.backup),'--data',str(self.data),'--offline'],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['jobs'],2)
        for verb in ['verify','restore']:
            r=subprocess.run(command+[verb,str(self.backup),'--offline'],capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
        help_result=subprocess.run(command+['create','--help'],capture_output=True,text=True)
        self.assertIn('broadcaster',help_result.stdout.lower())
        self.assertIn('stopped',help_result.stdout.lower())
