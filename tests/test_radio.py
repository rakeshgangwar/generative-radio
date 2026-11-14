import tempfile
import time
import unittest
from pathlib import Path

from radio.compose import compose, midi
from radio.config import Config
from radio.store import Store


class CompositionTests(unittest.TestCase):
    def test_reproducible_and_varied(self):
        self.assertEqual(compose(42, 120), compose(42, 120))
        self.assertNotEqual(compose(42, 120), compose(43, 120))

    def test_notes_are_bounded_and_in_key(self):
        for seed in range(50):
            notes = compose(seed, 120, 60)
            self.assertTrue(notes)
            for n in notes:
                self.assertIn(n.pitch % 12, {0, 2, 4, 5, 7, 9, 11})
                self.assertTrue(0 <= n.start < n.start + n.duration <= 120)
                self.assertTrue(1 <= n.velocity <= 60)
                self.assertTrue(36 <= n.pitch <= 84)
        data = midi(compose(42, 120), 120, 60)
        self.assertEqual(data[:4], b"MThd")
        self.assertEqual(data[-3:], b"\xff\x2f\x00")


class QueueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.data = Path(self.temp.name)
        self.config = Config(self.data, 120, 600, 60, 100, "unused")
        self.store = Store(self.data)

    def tearDown(self):
        self.store.db.close()
        self.temp.cleanup()

    def test_buffer_is_bounded(self):
        for _ in range(30):
            self.store.enqueue(self.config)
        self.assertEqual(self.store.status()["queue"]["pending"]["count"], 6)

    def test_claim_excludes_second_worker_and_stale_claim_recovers(self):
        self.store.enqueue(self.config)
        job = self.store.claim()
        second = Store(self.data)
        self.assertIsNone(second.claim())
        with self.store.db:
            self.store.db.execute("UPDATE jobs SET updated=?", (time.time()-601,))
        self.assertEqual(second.claim()["id"], job["id"])
        second.db.close()

    def test_only_completed_audio_can_be_dispatched(self):
        self.store.enqueue(self.config)
        job = self.store.claim()
        self.assertEqual(self.store.next_track(), "")
        path = self.data / "audio" / f"{job['id']}.wav"
        path.parent.mkdir()
        path.write_bytes(b"fixture")
        self.store.finish(job, path, {})
        self.assertEqual(self.store.next_track(), str(path.resolve()))
        self.assertEqual(self.store.next_track(), "")

    def test_retry_limit(self):
        self.store.enqueue(self.config)
        for _ in range(3):
            job = self.store.claim()
            self.store.fail(job, "broken render")
        self.assertIsNone(self.store.claim())
        self.assertEqual(self.store.status()["queue"]["failed"]["count"], 1)

    def test_cleanup_keeps_prefetched_files(self):
        self.store.enqueue(self.config)
        job = self.store.claim()
        path = self.data / "audio" / f"{job['id']}.wav"
        path.parent.mkdir()
        path.write_bytes(b"fixture")
        self.store.finish(job, path, {})
        self.store.next_track()
        self.store.cleanup()
        self.assertTrue(path.exists())
        with self.store.db:
            self.store.db.execute("UPDATE jobs SET updated=?", (time.time()-3601,))
        self.store.cleanup()
        self.assertFalse(path.exists())

    def test_seed_is_not_reused_after_cleanup(self):
        self.store.enqueue(self.config)
        job = self.store.claim()
        with self.store.db:
            self.store.db.execute("DELETE FROM jobs")
        self.store.enqueue(self.config)
        newer = self.store.claim()
        self.assertGreater(newer["id"], job["id"])
        self.assertNotEqual(newer["seed"], job["seed"])
        self.assertEqual(newer["bpm"], self.config.bpm)


if __name__ == "__main__":
    unittest.main()
