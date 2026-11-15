import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from radio.station_vitals import collect, run_command, parse_memory, parse_watchdog
from radio.observer import record

ROLES = ["composer", "renderer", "broadcaster", "icecast", "web"]
IDS = {role: str(i + 1) * 64 for i, role in enumerate(ROLES)}
SECRET = "must-never-appear-secret"


def archive(body, name="broadcaster-health.json"):
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as tar:
        item = tarfile.TarInfo(name)
        item.size = len(body)
        tar.addfile(item, io.BytesIO(body))
    return stream.getvalue()


def health(**changes):
    value = dict(updated_at=time.time(), healthy=True, child_pid=8, kind="healthy",
                 restart_count=0, consecutive_failures=0, rms_dbfs=-24, detail=SECRET)
    value.update(changes)
    return archive(json.dumps(value).encode())


class DockerFixture:
    def __init__(self):
        self.roles = ROLES[:]
        self.broken = None
        self.commands = []

    def __call__(self, command, stop):
        self.commands.append(command)
        if self.broken == command[1]:
            raise ValueError(SECRET)
        if command[1] == "ps":
            return ("\n".join(IDS[r] for r in self.roles) + "\n").encode()
        if command[1] == "inspect":
            return ("\n".join(json.dumps(dict(id=IDS[r], image="sha256:" + "a" * 64,
                    service=r, state="running", health="healthy", started="2026-11-15T00:00:00Z",
                    restarts=0, oom=False, Env=[SECRET])) for r in self.roles)).encode()
        if command[1] == "stats":
            return ("\n".join(json.dumps(dict(id=IDS[r], cpu="1.2%", memory="233.7MiB / 31GiB",
                    pids="8", secret=SECRET)) for r in self.roles)).encode()
        if command[1] == "cp":
            return health()
        raise AssertionError(command)


class CollectionTests(unittest.TestCase):
    def test_allowlisted_project_scoped_measurements(self):
        docker = DockerFixture()
        with patch("radio.station_vitals.run_command", docker):
            result = collect("generative-radio", True, threading.Event())
        self.assertEqual(result["assessment"], "healthy")
        self.assertEqual(set(result["services"]), set(ROLES))
        self.assertEqual(result["services"]["broadcaster"]["memory_bytes"], round(233.7 * 1024**2))
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(result["host"]["scope"], "observer-host")
        self.assertIn("label=com.docker.compose.project=generative-radio", docker.commands[0])
        self.assertEqual({c[1] for c in docker.commands}, {"ps", "inspect", "stats", "cp"})
        self.assertTrue(all(IDS[r] in docker.commands[2] for r in ROLES))

    def test_missing_required_service_is_not_healthy(self):
        docker = DockerFixture()
        docker.roles.remove("renderer")
        with patch("radio.station_vitals.run_command", docker):
            self.assertEqual(collect("generative-radio", True, threading.Event())["assessment"], "not_healthy")

    def test_duplicate_role_does_not_overwrite_healthy(self):
        docker = DockerFixture()
        docker.roles.append("renderer")
        with patch("radio.station_vitals.run_command", docker):
            self.assertNotEqual(collect("generative-radio", True, threading.Event())["assessment"], "healthy")

    def test_each_command_failure_is_unknown_and_sanitized(self):
        for name in ["ps", "inspect", "stats", "cp"]:
            with self.subTest(name=name):
                docker = DockerFixture()
                docker.broken = name
                with patch("radio.station_vitals.run_command", docker):
                    result = collect("generative-radio", True, threading.Event())
                self.assertEqual(result["assessment"], "unknown")
                self.assertNotIn(SECRET, json.dumps(result))

    def test_memory_units_and_bad_values(self):
        self.assertEqual(parse_memory("1.5GiB / 8GiB"), 1610612736)
        self.assertEqual(parse_memory("2.1MB / 8GB"), 2100000)
        for value in ["NaNMiB", "-1B", "4XB", "infinity", "1e99GB"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_memory(value)

    def test_watchdog_freshness_fields_and_bounds(self):
        self.assertTrue(parse_watchdog(health())["healthy"])
        self.assertNotIn(SECRET, json.dumps(parse_watchdog(health())))
        for changes in [dict(updated_at=time.time()-100), dict(updated_at=float("nan")),
                        dict(updated_at=time.time()+10), dict(child_pid=None)]:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                parse_watchdog(health(**changes))
        for data in [archive(b"x"*4097), archive(b"{}", "other"), b"not tar"]:
            with self.assertRaises(ValueError):
                parse_watchdog(data)

    def test_malformed_stats_never_produce_health(self):
        docker = DockerFixture()
        def run(command, stop):
            if command[1] == "stats":
                return json.dumps(dict(id=IDS["composer"], cpu="NaN%", memory="1MiB", pids="8")).encode()
            return docker(command, stop)
        with patch("radio.station_vitals.run_command", run):
            self.assertEqual(collect("generative-radio", True, threading.Event())["assessment"], "unknown")


class CommandTests(unittest.TestCase):
    def test_real_child_success(self):
        self.assertEqual(run_command([sys.executable, "-c", "print('ok')"], threading.Event()), b"ok\n")

    def test_output_is_capped_and_child_reaped(self):
        with self.assertRaises(ValueError):
            run_command([sys.executable, "-c", "import os; os.write(1,b'x'*1000000)"], threading.Event())

    def test_cancel_after_stdout_closes_still_interrupts_child(self):
        stop = threading.Event()
        timer = threading.Timer(.05, stop.set)
        timer.start()
        started = time.monotonic()
        try:
            with self.assertRaises(ValueError):
                run_command([sys.executable, "-c", "import os,time; os.close(1); time.sleep(20)"], stop)
            self.assertLess(time.monotonic()-started, 2)
        finally:
            timer.join()

    def test_timeout_and_cancel_are_bounded(self):
        for cancel in [False, True]:
            stop = threading.Event()
            timer = threading.Timer(.05, stop.set) if cancel else None
            if timer:
                timer.start()
            started = time.monotonic()
            with patch("radio.station_vitals.COMMAND_TIMEOUT", .15), self.assertRaises(ValueError):
                run_command([sys.executable, "-c", "import time; time.sleep(20)"], stop)
            self.assertLess(time.monotonic()-started, 2)
            if timer:
                timer.join()


class RecorderTests(unittest.TestCase):
    def test_rotation_and_cumulative_unhealthy_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)/"record"
            states = iter(["not_healthy", "healthy", "healthy", "healthy"])
            def sample(*args):
                return dict(assessment=next(states), host={}, services={})
            clock = [0.0]
            stop = threading.Event()
            def advance(seconds):
                clock[0] += seconds
            with patch("radio.observer.collect", sample), patch("radio.observer.time.monotonic", lambda: clock[0]), patch.object(stop, "wait", advance):
                code = record(out, "generative-radio", True, 4, 1, 2, stop)
            summary = json.loads((out/"summary.json").read_text())
            self.assertEqual(code, 1)
            self.assertEqual(summary["state"], "complete")
            self.assertEqual(summary["samples"], 4)
            self.assertEqual(summary["retained"], 2)
            self.assertEqual(summary["not_healthy"], 1)
            self.assertEqual(len(list(out.glob("sample-*.json"))), 2)
            self.assertEqual(out.stat().st_mode & 0o777, 0o700)
            self.assertEqual(set(json.loads(p.read_text())["sequence"] for p in out.glob("sample-*.json")), {2,3})

    def test_existing_output_and_station_data_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root)
            with self.assertRaises(ValueError):
                record(parent, "generative-radio", False, 0, 30, 2, threading.Event())
            (parent/"radio.sqlite").write_text("station")
            with self.assertRaises(ValueError):
                record(parent/"child", "generative-radio", False, 0, 30, 2, threading.Event())
            self.assertFalse((parent/"child").exists())

    def test_cancel_retains_partial_receipt(self):
        with tempfile.TemporaryDirectory() as root:
            stop = threading.Event()
            def sample(*args):
                stop.set()
                return dict(assessment="unknown", host={}, services={})
            with patch("radio.observer.collect", sample):
                code = record(Path(root)/"cancel", "generative-radio", False, 100, 30, 2, stop)
            summary = json.loads((Path(root)/"cancel/summary.json").read_text())
            self.assertEqual(code, 130)
            self.assertEqual(summary["state"], "cancelled")
            self.assertEqual(summary["samples"], 1)

    def test_single_snapshot_and_bad_project(self):
        with tempfile.TemporaryDirectory() as root:
            with patch("radio.observer.collect", return_value=dict(assessment="healthy")):
                self.assertEqual(record(Path(root)/"one", "generative-radio", False, 0, 30, 1, threading.Event()), 0)
            with self.assertRaises(ValueError):
                record(Path(root)/"bad", "--bad", False, 0, 30, 1, threading.Event())


@unittest.skipUnless(os.environ.get("RADIO_OBSERVER_LIVE_PROJECT"), "requires explicit live Docker project")
class LiveObserverTests(unittest.TestCase):
    def test_selected_docker_templates_yield_real_healthy_snapshot(self):
        result = collect(os.environ["RADIO_OBSERVER_LIVE_PROJECT"], True, threading.Event())
        self.assertEqual(result["assessment"], "healthy", result["errors"])
        self.assertEqual(set(result["services"]), set(ROLES))
        self.assertTrue(result["audio_report"]["healthy"])
