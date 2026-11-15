"""Local-disk SQLite queue. One composer and one renderer per station."""
import json
import sqlite3
import time
from contextlib import contextmanager


class Store:
    def __init__(self, data):
        self.data = data
        self.db = sqlite3.connect(data / "radio.sqlite", timeout=30)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
          id INTEGER PRIMARY KEY AUTOINCREMENT, seed INTEGER NOT NULL,
          seconds REAL NOT NULL, bpm INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
          attempts INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL,
          path TEXT, error TEXT, analysis TEXT);
        CREATE TABLE IF NOT EXISTS heartbeats (role TEXT PRIMARY KEY, at REAL);
        """)

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield self.db
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def heartbeat(self, role):
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO heartbeats VALUES (?, ?)", (role, time.time()))

    def enqueue(self, config):
        # Account for overlap so the playable buffer reaches its target.
        with self.transaction() as db:
            buffered = db.execute("SELECT coalesce(sum(seconds-5),0) FROM jobs WHERE status IN ('pending','rendering','ready')").fetchone()[0]
            if buffered >= config.buffer_seconds:
                return False
            seq = db.execute("SELECT coalesce((SELECT seq FROM sqlite_sequence WHERE name='jobs'),0)+1").fetchone()[0]
            db.execute("INSERT INTO jobs(seed,seconds,bpm,updated) VALUES (?,?,?,?)",
                       (config.seed + seq, config.segment_seconds, config.bpm, time.time()))
        return True

    def claim(self):
        now = time.time()
        with self.transaction() as db:
            # Render subprocesses time out well before this lease expires.
            db.execute("UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'pending' END, updated=? WHERE status='rendering' AND updated<?", (now, now - 600))
            row = db.execute("SELECT * FROM jobs WHERE status='pending' ORDER BY id LIMIT 1").fetchone()
            if row:
                db.execute("UPDATE jobs SET status='rendering', attempts=attempts+1, updated=? WHERE id=?", (now, row["id"]))
                return dict(row)

    def finish(self, job, path, analysis):
        with self.db:
            self.db.execute("UPDATE jobs SET status='ready',path=?,analysis=?,error=NULL,updated=? WHERE id=?",
                            (str(path.resolve()), json.dumps(analysis), time.time(), job["id"]))

    def fail(self, job, error):
        with self.db:
            self.db.execute("UPDATE jobs SET status=CASE WHEN attempts>=3 THEN 'failed' ELSE 'pending' END,error=?,updated=? WHERE id=?",
                            (str(error)[-2000:], time.time(), job["id"]))

    def next_track(self):
        info = self.next_track_info()
        return info['path'] if info else ''

    def next_track_info(self):
        """Dispatch one file plus its saved analysis; this is not on-air history."""
        with self.transaction() as db:
            while True:
                row = db.execute("SELECT * FROM jobs WHERE status='ready' ORDER BY id LIMIT 1").fetchone()
                if not row:
                    return None
                path = self.data / "audio" / f"{row['id']}.wav"
                if not path.is_file():
                    db.execute("UPDATE jobs SET status='failed',error='audio missing' WHERE id=?", (row["id"],))
                    continue
                # Liquidsoap prefetches; 'served' means dispatched, not confirmed on-air.
                db.execute("UPDATE jobs SET status='served',updated=? WHERE id=?", (time.time(), row["id"]))
                return {'path': str(path.resolve()), 'analysis': row['analysis']}

    def cleanup(self):
        # Retain dispatched files for an hour: exceeds maximum segment + prefetch.
        rows = self.db.execute("SELECT id FROM jobs WHERE status IN ('served','failed') AND updated<?", (time.time() - 3600,)).fetchall()
        for row in rows:
            for directory, extension in [("audio", "wav"), ("midi", "mid"),
                                         ("work", "raw.wav"), ("work", "wav")]:
                (self.data / directory / f"{row['id']}.{extension}").unlink(missing_ok=True)
        with self.db:
            # Preserve IDs/seeds via AUTOINCREMENT even after history expires.
            self.db.executemany("DELETE FROM jobs WHERE id=?", [(r["id"],) for r in rows])

    def status(self):
        rows = self.db.execute("SELECT status,count(*) AS count,sum(seconds-5) AS seconds FROM jobs GROUP BY status").fetchall()
        return {"queue": {r["status"]: {"count": r["count"], "seconds": r["seconds"]} for r in rows},
                "heartbeats": {r["role"]: round(time.time()-r["at"], 1) for r in self.db.execute("SELECT * FROM heartbeats")},
                "recent_errors": [dict(r) for r in self.db.execute("SELECT id,error FROM jobs WHERE error IS NOT NULL ORDER BY id DESC LIMIT 5")]}
