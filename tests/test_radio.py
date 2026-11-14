import tempfile
import time
import unittest
from pathlib import Path

from radio.compose import compose, midi
from radio.config import Config
from radio.store import Store


class CompositionTests(unittest.TestCase):
    def test_seeds_change_harmonic_path_and_chord_holds(self):
        # Velocity-only variation cannot satisfy musical variety.
        paths, holds = set(), set()
        for seed in range(16):
            notes = compose(seed, 120)
            bass = [n for n in notes if n.channel == 1]
            paths.add(tuple(n.pitch % 12 for n in bass))
            holds.add(tuple(round(b.start - a.start, 3) for a, b in zip(bass, bass[1:])))
        self.assertGreaterEqual(len(paths), 4)
        self.assertGreaterEqual(len(holds), 3)

    def test_melody_develops_rhythm_and_avoids_large_leaps(self):
        rhythms = set()
        for seed in range(12):
            melody = sorted((n for n in compose(seed, 120) if n.channel == 2),
                            key=lambda n: n.start)
            self.assertGreaterEqual(len(melody), 8)
            self.assertLessEqual(len(melody), 100)
            self.assertGreaterEqual(len({round(n.duration, 3) for n in melody}), 3)
            self.assertGreaterEqual(len({n.pitch for n in melody}), 4)
            for a, b in zip(melody, melody[1:]):
                self.assertLessEqual(abs(b.pitch - a.pitch), 7)
            rhythms.add(tuple(round(b.start - a.start, 3)
                              for a, b in zip(melody, melody[1:])))
        self.assertGreaterEqual(len(rhythms), 4)

    def test_opening_and_release_are_sparser_than_development(self):
        for seed in range(12):
            melody = [n for n in compose(seed, 120) if n.channel == 2]
            opening = sum(n.start < 24 for n in melody)
            middle = sum(24 <= n.start < 96 for n in melody)
            release = sum(n.start >= 96 for n in melody)
            self.assertGreater(middle / 72, opening / 24)
            self.assertGreater(middle / 72, release / 24)

    def test_seeded_profiles_change_overall_melodic_activity(self):
        # Merely rotating identical-density rhythms leaves tracks too similar.
        counts = [sum(n.channel == 2 for n in compose(seed, 120))
                  for seed in range(32)]
        self.assertGreaterEqual(max(counts) - min(counts), 10)

    def test_duration_tempo_boundaries_and_pad_note_lifetimes(self):
        for seconds in [20, 120, 600]:
            for bpm in [40, 60, 90]:
                for seed in range(12):
                    with self.subTest(seconds=seconds, bpm=bpm, seed=seed):
                        notes = compose(seed, seconds, bpm)
                        self.assertTrue(any(n.channel == 2 for n in notes))
                        self.assertLess(len(notes), seconds * 4)
                        self.assertEqual(notes, compose(seed, seconds, bpm))
                        self.assertEqual(midi(notes, seconds, bpm),
                                         midi(compose(seed, seconds, bpm), seconds, bpm))
                        ends = {}
                        for n in sorted(notes, key=lambda n: n.start):
                            self.assertTrue(0 <= n.start < n.start + n.duration <= seconds)
                            self.assertTrue(36 <= n.pitch <= 84)
                            self.assertTrue(1 <= n.velocity <= 60)
                            self.assertIn(n.pitch % 12, {0, 2, 4, 5, 7, 9, 11})
                            if n.channel == 0:
                                self.assertGreaterEqual(n.start + 1e-7, ends.get(n.pitch, 0))
                                ends[n.pitch] = n.start + n.duration

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

    def test_cleanup_removes_temporary_audio_after_final_abandoned_attempt(self):
        self.store.enqueue(self.config)
        for _ in range(3):
            job = self.store.claim()
            self.assertIsNotNone(job)
            with self.store.db:
                self.store.db.execute("UPDATE jobs SET updated=? WHERE id=?",
                                      (time.time() - 601, job["id"]))
        self.assertIsNone(self.store.claim())
        self.assertEqual(self.store.status()["queue"]["failed"]["count"], 1)
        leftovers = [self.data / "work" / f"{job['id']}.raw.wav",
                     self.data / "work" / f"{job['id']}.wav",
                     self.data / "audio" / f"{job['id']}.wav",
                     self.data / "midi" / f"{job['id']}.mid"]
        for path in leftovers:
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(b"interrupted render")
        with self.store.db:
            self.store.db.execute("UPDATE jobs SET updated=? WHERE id=?",
                                  (time.time() - 3601, job["id"]))
        self.store.cleanup()
        for path in leftovers:
            self.assertFalse(path.exists(), str(path))
        self.assertNotIn("failed", self.store.status()["queue"])

    def test_cleanup_preserves_active_and_recent_terminal_work(self):
        paths = []
        for status in ["pending", "rendering", "ready", "served", "failed"]:
            self.assertTrue(self.store.enqueue(self.config))
            job_id = self.store.db.execute("SELECT max(id) FROM jobs").fetchone()[0]
            age = 10 if status in {"served", "failed"} else 3700
            with self.store.db:
                self.store.db.execute("UPDATE jobs SET status=?,updated=? WHERE id=?",
                                      (status, time.time() - age, job_id))
            for suffix in ["wav", "raw.wav"]:
                path = self.data / "work" / f"{job_id}.{suffix}"
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(b"still needed")
                paths.append(path)
        self.store.cleanup()
        self.assertTrue(all(p.is_file() for p in paths))
        self.assertEqual(sum(v["count"] for v in self.store.status()["queue"].values()), 5)

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
