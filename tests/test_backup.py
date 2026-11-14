import json
import sqlite3
import tempfile
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import unittest
from pathlib import Path
from unittest.mock import patch

from radio.backup import create_backup, restore_backup, verify_backup
from radio.config import Config
from radio.store import Store


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'station'
        self.data.mkdir()
        self.config = Config(self.data, 20, 20, 60, 90, 'unused')
        for name in ['audio', 'midi', 'work']:
            (self.data / name).mkdir()
        (self.data / 'audio/fallback.wav').write_bytes(b'cached fallback')
        self.store = Store(self.data)
        self.addCleanup(self.store.db.close)
        for _ in range(2):
            self.store.enqueue(self.config)
            job = self.store.claim()
            audio = self.data / 'audio' / f'{job["id"]}.wav'
            audio.write_bytes(b'completed audio' + bytes([job['id']]))
            self.store.finish(job, audio, {'duration': 20})
        self.store.next_track()  # one served and one ready
        self.store.enqueue(self.config)
        self.store.claim()  # interrupted render must become pending on restore
        self.store.heartbeat('renderer')
        (self.data / 'work/private.raw.wav').write_bytes(b'incomplete')
        (self.data / 'broadcaster-health.json').write_text('stale')
        self.backup = self.root / 'backup'

    def test_live_wal_round_trip_preserves_queue_and_sequence(self):
        before = self.store.db.execute('SELECT * FROM jobs').fetchall()
        result = create_backup(self.data, self.backup)
        self.assertEqual(result['version'], 1)
        self.assertTrue((self.data / 'radio.sqlite-wal').exists())
        self.assertFalse((self.backup / 'work').exists())
        self.assertFalse((self.backup / 'broadcaster-health.json').exists())
        self.assertEqual(verify_backup(self.backup), result)
        target = self.root / 'restored'
        restore_backup(self.backup, target)
        restored = Store(target)
        self.addCleanup(restored.db.close)
        rows = restored.db.execute('SELECT * FROM jobs ORDER BY id').fetchall()
        self.assertEqual([r['seed'] for r in rows], [r['seed'] for r in before])
        self.assertEqual([r['status'] for r in rows], ['served', 'ready', 'pending'])
        self.assertEqual(rows[2]['attempts'], 0)
        self.assertEqual(restored.status()['heartbeats'], {})
        self.assertEqual(restored.next_track(), str(target / 'audio/2.wav'))
        self.assertTrue(restored.enqueue(self.config))
        newest = restored.db.execute('SELECT id,seed FROM jobs ORDER BY id DESC LIMIT 1').fetchone()
        self.assertEqual(tuple(newest), (4, 94))
        self.assertEqual(rows[1]['path'], str(target / 'audio/2.wav'))
        self.assertEqual(verify_backup(self.backup), result)  # restore never edits backup

    def test_empty_existing_restore_destination_is_supported(self):
        create_backup(self.data, self.backup)
        target = self.root / 'empty-volume'
        target.mkdir()
        restore_backup(self.backup, target)
        self.assertTrue((target / 'radio.sqlite').is_file())

    def test_optional_midi_is_included(self):
        (self.data / 'midi/2.mid').write_bytes(b'midi')
        result = create_backup(self.data, self.backup)
        self.assertIn('midi/2.mid', result['files'])
        verify_backup(self.backup)

    def test_existing_destinations_are_never_overwritten(self):
        self.backup.mkdir()
        with self.assertRaises((ValueError, FileExistsError)):
            create_backup(self.data, self.backup)
        self.assertEqual(list(self.backup.iterdir()), [])
        self.backup.rmdir()
        create_backup(self.data, self.backup)
        target = self.root / 'not-empty'
        target.mkdir()
        (target / 'keep').write_text('existing data')
        with self.assertRaises(ValueError):
            restore_backup(self.backup, target)
        self.assertEqual((target / 'keep').read_text(), 'existing data')
        self.assertEqual(len(list(target.iterdir())), 1)

    def test_corrupt_or_missing_audio_fails_before_restore_writes(self):
        create_backup(self.data, self.backup)
        (self.backup / 'audio/2.wav').write_bytes(b'corrupted')
        target = self.root / 'untouched'
        with self.assertRaises(ValueError):
            restore_backup(self.backup, target)
        self.assertFalse(target.exists())
        (self.backup / 'audio/2.wav').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            verify_backup(self.backup)

    def test_omitting_required_audio_from_manifest_is_rejected(self):
        create_backup(self.data, self.backup)
        manifest = json.loads((self.backup / 'manifest.json').read_text())
        del manifest['files']['audio/2.wav']
        (self.backup / 'audio/2.wav').unlink()
        (self.backup / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            verify_backup(self.backup)

    def test_traversal_symlinks_and_extra_files_are_rejected(self):
        create_backup(self.data, self.backup)
        manifest = json.loads((self.backup / 'manifest.json').read_text())
        original = json.dumps(manifest)
        manifest['files']['../outside'] = manifest['files']['audio/2.wav']
        (self.backup / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            verify_backup(self.backup)
        (self.backup / 'manifest.json').write_text(original)
        audio = self.backup / 'audio/2.wav'
        audio.unlink()
        audio.symlink_to(self.data / 'audio/2.wav')
        with self.assertRaises(ValueError):
            verify_backup(self.backup)
        audio.unlink()
        audio.write_bytes((self.data / 'audio/2.wav').read_bytes())
        (self.backup / 'unexpected').write_text('not in manifest')
        with self.assertRaises(ValueError):
            verify_backup(self.backup)

    def test_missing_source_db_does_not_create_a_station(self):
        empty = self.root / 'missing-source'
        empty.mkdir()
        with self.assertRaises((ValueError, FileNotFoundError, sqlite3.Error)):
            create_backup(empty, self.backup)
        self.assertFalse((empty / 'radio.sqlite').exists())
        self.assertFalse(self.backup.exists())

    def test_missing_reference_retries_and_removes_incomplete_bundle(self):
        (self.data / 'audio/2.wav').unlink()
        with self.assertRaises((ValueError, FileNotFoundError)):
            create_backup(self.data, self.backup)
        self.assertFalse(self.backup.exists())

    def test_backup_copy_failure_leaves_no_complete_or_partial_bundle(self):
        with patch('radio.backup.shutil.copyfile', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                create_backup(self.data, self.backup)
        self.assertFalse(self.backup.exists())

    def test_restore_copy_failure_leaves_existing_empty_directory_empty(self):
        create_backup(self.data, self.backup)
        target = self.root / 'empty'
        target.mkdir()
        with patch('radio.backup.shutil.copyfile', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                restore_backup(self.backup, target)
        self.assertEqual(list(target.iterdir()), [])

    def test_retention_race_retries_a_fresh_snapshot(self):
        import shutil
        original = shutil.copyfile
        raced = []
        def copy(source, target):
            if Path(source).name == '1.wav' and not raced:
                raced.append(True)
                Path(source).unlink()
                with self.store.db:
                    self.store.db.execute('DELETE FROM jobs WHERE id=1')
                raise FileNotFoundError('retention removed the served track')
            return original(source, target)
        with patch('radio.backup.shutil.copyfile', side_effect=copy):
            result = create_backup(self.data, self.backup)
        self.assertTrue(raced)
        self.assertEqual(result['jobs'], 2)
        self.assertNotIn('audio/1.wav', result['files'])
        verify_backup(self.backup)

    def test_invalid_manifest_summary_is_rejected(self):
        create_backup(self.data, self.backup)
        manifest = json.loads((self.backup / 'manifest.json').read_text())
        manifest['jobs'] = 999
        (self.backup / 'manifest.json').write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            verify_backup(self.backup)

    def test_database_without_sequence_is_rejected(self):
        with self.store.db:
            self.store.db.execute("UPDATE sqlite_sequence SET seq=1 WHERE name='jobs'")
        with self.assertRaises(ValueError):
            create_backup(self.data, self.backup)
        self.assertFalse(self.backup.exists())

    def test_cli_reports_success_and_invalid_input_without_a_traceback(self):
        command = [sys.executable, '-m', 'radio.backup']
        created = subprocess.run(command + ['create', str(self.backup), '--data', str(self.data)], capture_output=True, text=True)
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertEqual(json.loads(created.stdout)['jobs'], 3)
        verified = subprocess.run(command + ['verify', str(self.backup)], capture_output=True, text=True)
        self.assertEqual(verified.returncode, 0, verified.stderr)
        restored = subprocess.run(command + ['restore', str(self.backup), '--data', str(self.root/'cli-restored')], capture_output=True, text=True)
        self.assertEqual(restored.returncode, 0, restored.stderr)
        invalid = subprocess.run(command + ['create', str(self.backup), '--data', str(self.data)], capture_output=True, text=True)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertNotIn('Traceback', invalid.stderr)

    def test_concurrent_restore_cannot_enter_the_same_empty_destination(self):
        create_backup(self.data, self.backup)
        target = self.root / 'concurrent'
        target.mkdir()
        entered, release = Event(), Event()
        original = tempfile.TemporaryDirectory
        calls = []
        def delayed(*args, **kwargs):
            calls.append(True)
            if len(calls) == 1:
                entered.set()
                if not release.wait(5):
                    raise RuntimeError('test restore was not released')
            return original(*args, **kwargs)
        with ThreadPoolExecutor(max_workers=1) as pool:
            with patch('radio.backup.tempfile.TemporaryDirectory', side_effect=delayed):
                first = pool.submit(restore_backup, self.backup, target)
                self.assertTrue(entered.wait(2))
                try:
                    with self.assertRaises(ValueError):
                        restore_backup(self.backup, target)
                finally:
                    release.set()
                first.result(timeout=3)
        self.assertEqual(len(calls), 1)
        self.assertTrue((target/'radio.sqlite').is_file())


if __name__ == '__main__':
    unittest.main()
