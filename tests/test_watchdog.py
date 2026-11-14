import array
import gc
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import wave
import warnings

from radio.watchdog import Options, RestartPolicy, Supervisor, assess_pcm, probe_stream, report_is_healthy


def tone(seconds=1):
    samples = array.array("h", (int(5000 * math.sin(2 * math.pi * 220 * i / 8000))
                               for i in range(int(seconds * 8000))))
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


class AudioProbeTests(unittest.TestCase):
    def test_audible_full_sample_is_healthy(self):
        self.assertEqual(assess_pcm(tone(), 1).kind, "healthy")

    def test_all_quiet_windows_are_silent_but_a_fade_is_healthy(self):
        quiet = bytes(16000)
        self.assertEqual(assess_pcm(quiet, 1).kind, "silent")
        self.assertEqual(assess_pcm(quiet + tone(), 2).kind, "healthy")

    def test_short_empty_and_odd_samples_are_not_healthy(self):
        for sample in [b"", b"\x01", tone(.25), tone() + b"\x00"]:
            self.assertEqual(assess_pcm(sample, 1).kind, "incomplete")

    def test_low_amplitude_noise_is_silent(self):
        self.assertEqual(assess_pcm(array.array("h", [1, -1] * 4000).tobytes(), 1).kind,
                         "silent")


class RestartPolicyTests(unittest.TestCase):
    def test_only_consecutive_audio_failures_trigger_recovery(self):
        policy = RestartPolicy(3, 3, 900)
        self.assertFalse(policy.observe("silent", 0))
        self.assertFalse(policy.observe("stream_error", 30))
        self.assertFalse(policy.observe("healthy", 60))
        self.assertFalse(policy.observe("silent", 90))
        self.assertFalse(policy.observe("silent", 120))
        self.assertTrue(policy.observe("silent", 150))

    def test_unavailable_icecast_resets_the_failure_streak(self):
        policy = RestartPolicy(3, 3, 900)
        policy.observe("silent", 0)
        policy.observe("silent", 30)
        self.assertFalse(policy.observe("server_unavailable", 60))
        self.assertFalse(policy.observe("stream_error", 90))

    def test_child_exit_recovers_immediately_with_a_rolling_budget(self):
        policy = RestartPolicy(3, 3, 900)
        for at in [0, 10, 20]:
            self.assertTrue(policy.observe("child_exited", at))
            policy.record_restart(at)
        self.assertFalse(policy.observe("child_exited", 899))
        self.assertTrue(policy.observe("child_exited", 900))


class ReportHealthTests(unittest.TestCase):
    def test_health_command_reads_report_without_starting_a_child(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broadcaster-health.json"
            env = dict(os.environ, RADIO_DATA=directory, PATH="/nonexistent")
            for timestamp, wanted in [(time.time(), 0), (time.time() - 100, 1)]:
                path.write_text(json.dumps({"updated_at": timestamp, "healthy": True,
                                            "child_pid": os.getpid()}))
                try:
                    result = subprocess.run([sys.executable, "-m", "radio.watchdog", "--health"],
                                            env=env, capture_output=True, timeout=2)
                except subprocess.TimeoutExpired:
                    self.fail("Health command started a long-running supervisor")
                self.assertEqual(result.returncode, wanted, result.stderr)

    def test_fresh_report_requires_live_child_and_healthy_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health.json"
            self.assertFalse(report_is_healthy(path, now=100))
            report = {"updated_at": 100, "healthy": True, "child_pid": os.getpid()}
            path.write_text(json.dumps(report))
            self.assertTrue(report_is_healthy(path, now=110))
            self.assertFalse(report_is_healthy(path, now=200))
            self.assertFalse(report_is_healthy(path, now=90))
            report["healthy"] = False
            path.write_text(json.dumps(report))
            self.assertFalse(report_is_healthy(path, now=110))

    def test_bad_reports_and_exited_child_are_unhealthy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "health.json"
            for content in ["{", "null", "[]", '{}']:
                path.write_text(content)
                self.assertFalse(report_is_healthy(path))
            child = subprocess.Popen([sys.executable, "-c", "pass"])
            child.wait()
            path.write_text(json.dumps({"updated_at": time.time(), "healthy": True,
                                        "child_pid": child.pid}))
            self.assertFalse(report_is_healthy(path))


class WatchdogOptionsTests(unittest.TestCase):
    def test_invalid_timeouts_or_restart_limits_are_rejected(self):
        for settings in [{"timeout": 1}, {"probe_seconds": 0}, {"interval": 0},
                         {"restart_limit": 0}, {"restart_window": 0}, {"failures": 0}]:
            with self.subTest(settings=settings):
                with self.assertRaises(ValueError):
                    Options(**settings)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("curl") and hasattr(os, "mkfifo"),
                     "Needs FFmpeg, curl and POSIX")
class RealProbeTests(unittest.TestCase):
    def check_status_phase(self, cancel):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blocked-status"
            os.mkfifo(path)
            code = ("import json,threading,time\nfrom radio.watchdog import Options,probe_stream\n"
                    f"options=Options(status_url={path.as_uri()!r},probe_seconds=.25,timeout=.6,stop_timeout=.1)\n"
                    "stop=threading.Event()\n"
                    + ("threading.Timer(.2,stop.set).start()\n" if cancel else "")
                    + "started=time.monotonic();result=probe_stream(options,stop)\n"
                    "print(json.dumps({'kind':result.kind,'elapsed':time.monotonic()-started}))\n")
            try:
                result = subprocess.run([sys.executable, "-c", code], capture_output=True,
                                        text=True, timeout=3)
            except subprocess.TimeoutExpired:
                self.fail("Icecast status phase exceeded the overall probe deadline")
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report["kind"], "cancelled" if cancel else "server_unavailable")
            self.assertLess(report["elapsed"], 1.5)

    def test_status_phase_is_bounded_by_the_overall_deadline(self):
        self.check_status_phase(cancel=False)

    def test_status_phase_is_cancelled_without_waiting_for_network(self):
        self.check_status_phase(cancel=True)

    def test_real_decoder_accepts_audio_and_rejects_early_eof(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            with wave.open(str(path), "wb") as audio:
                audio.setparams((1, 2, 8000, 0, "NONE", "not compressed"))
                audio.writeframes(tone(1))
            for expected, kind in [(1, "healthy"), (2, "incomplete")]:
                options = Options(status_url=path.as_uri(), stream_url=str(path),
                                  probe_seconds=expected, timeout=3)
                result = probe_stream(options, threading.Event())
                self.assertEqual(result.kind, kind)

    def test_stalled_decoder_is_timed_out_and_reaped(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blocked"
            os.mkfifo(path)
            status = Path(directory) / "status.json"
            status.write_text('{}')
            options = Options(status_url=status.as_uri(), stream_url=str(path),
                              probe_seconds=.25, timeout=.6, stop_timeout=.1)
            started = time.monotonic()
            with warnings.catch_warnings(record=True) as emitted:
                warnings.simplefilter("always", ResourceWarning)
                result = probe_stream(options, threading.Event())
                gc.collect()
            self.assertEqual(result.kind, "stalled")
            self.assertLess(time.monotonic() - started, 3)
            self.assertFalse(any(isinstance(w.message, ResourceWarning) for w in emitted))

    def test_cancellation_interrupts_a_blocked_decoder(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blocked"
            os.mkfifo(path)
            status = Path(directory) / "status.json"
            status.write_text('{}')
            options = Options(status_url=status.as_uri(), stream_url=str(path),
                              probe_seconds=1, timeout=5, stop_timeout=.1)
            stop = threading.Event()
            timer = threading.Timer(.2, stop.set)
            timer.start()
            self.addCleanup(timer.join)
            started = time.monotonic()
            result = probe_stream(options, stop)
            self.assertEqual(result.kind, "cancelled")
            self.assertLess(time.monotonic() - started, 3)


@unittest.skipUnless(hasattr(os, "killpg"), "Supervisor requires POSIX process groups")
class SupervisorProcessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.counter = self.directory / "starts.txt"
        self.report = self.directory / "broadcaster-health.json"
        self.parent = None
        self.addCleanup(self.stop_parent)

    def start_parent(self, probe, crash=False, ignore_term=False, child_override=None,
                     report_error=False):
        child = ("import os,time,signal\nfrom pathlib import Path\n"
                 + ("signal.signal(signal.SIGTERM,signal.SIG_IGN)\n" if ignore_term else "")
                 + f"with Path({str(self.counter)!r}).open('a') as f: f.write(str(os.getpid())+'\\n')\n"
                 + ("raise SystemExit(2)\n" if crash else
                    "time.sleep(60)\n"))
        if child_override is not None:
            child = child_override
        code = ("import sys\nfrom pathlib import Path\nfrom radio.watchdog import *\n"
                f"options=Options(data=Path({str(self.directory)!r}),grace=0,probe_seconds=.25,"
                "timeout=.5,interval=.1,failures=2,restart_limit=2,restart_window=30,stop_timeout=.2)\n"
                + ("from unittest.mock import patch\n"
                   "patch('radio.watchdog.tempfile.NamedTemporaryFile',side_effect=OSError('disk full')).start()\n"
                   if report_error else "")
                + f"Supervisor(options,command=[sys.executable,'-c',{child!r}],probe={probe}).run()\n")
        self.parent = subprocess.Popen([sys.executable, "-c", code],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop_parent(self):
        if self.parent is not None and self.parent.poll() is None:
            self.parent.terminate()
            try:
                self.parent.wait(timeout=4)
            except subprocess.TimeoutExpired:
                self.parent.kill()
                self.parent.wait(timeout=2)
        if self.report.exists():
            pid = json.loads(self.report.read_text()).get("child_pid")
            if pid:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def wait_report(self, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.report.exists():
                report = json.loads(self.report.read_text())
                if predicate(report):
                    return report
            if self.parent.poll() is not None:
                self.fail(f"Supervisor exited unexpectedly: {self.parent.returncode}")
            time.sleep(.02)
        self.fail("Expected supervisor state was not reached")

    def test_silence_restarts_child_then_healthy_audio_resets_failure(self):
        probe = (f"lambda options,stop: ProbeResult('healthy' if Path({str(self.counter)!r}).exists() "
                 f"and len(Path({str(self.counter)!r}).read_text().splitlines())>=2 else 'silent')")
        self.start_parent(probe)
        report = self.wait_report(lambda r: r["healthy"])
        self.assertEqual(len(self.counter.read_text().splitlines()), 2)
        self.assertEqual(report["consecutive_failures"], 0)

    def test_server_outage_does_not_restart_a_live_child(self):
        self.start_parent("lambda options,stop: ProbeResult('server_unavailable')")
        self.wait_report(lambda r: r["kind"] == "server_unavailable")
        time.sleep(.4)
        self.assertEqual(len(self.counter.read_text().splitlines()), 1)

    def test_crashing_child_is_rate_limited(self):
        self.start_parent("lambda options,stop: ProbeResult('healthy')", crash=True)
        report = self.wait_report(lambda r: r["kind"] == "cooldown")
        self.assertFalse(report["healthy"])
        self.assertEqual(len(self.counter.read_text().splitlines()), 3)
        self.assertIsNone(self.parent.poll())

    def test_sigterm_reaps_even_a_child_ignoring_termination(self):
        self.start_parent("lambda options,stop: ProbeResult('healthy')", ignore_term=True)
        report = self.wait_report(lambda r: r["healthy"])
        pid = report["child_pid"]
        time.sleep(.1)
        self.parent.terminate()
        self.parent.wait(timeout=3)
        self.assertEqual(self.parent.returncode, 0)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertFalse(report_is_healthy(self.report))

    def test_report_write_failure_keeps_audio_child_running(self):
        self.start_parent("lambda options,stop: ProbeResult('healthy')", report_error=True)
        deadline = time.monotonic() + 3
        while not self.counter.exists() and self.parent.poll() is None and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertIsNone(self.parent.poll(), "Report write failure stopped the broadcaster")
        self.assertTrue(self.counter.exists())
        pid = int(self.counter.read_text().strip())
        self.parent.terminate()
        self.parent.wait(timeout=3)
        self.assertEqual(self.parent.returncode, 0)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    @unittest.skipUnless(Path("/proc").is_dir(), "Uses Linux process state")
    def test_shutdown_kills_a_descendant_after_its_parent_exits(self):
        pidfile = self.directory / "descendant.pid"
        descendant = ("import os,signal,time\nfrom pathlib import Path\n"
                      "signal.signal(signal.SIGTERM,signal.SIG_IGN)\n"
                      f"Path({str(pidfile)!r}).write_text(str(os.getpid()))\n"
                      "time.sleep(60)\n")
        child = ("import subprocess,sys,time\n"
                 f"subprocess.Popen([sys.executable,'-c',{descendant!r}])\n"
                 "time.sleep(60)\n")
        self.start_parent(f"lambda options,stop: ProbeResult('healthy' if Path({str(pidfile)!r}).exists() else 'silent')",
                          child_override=child)
        self.wait_report(lambda r: r["healthy"])
        pid = int(pidfile.read_text())
        def cleanup():
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        self.addCleanup(cleanup)
        self.parent.terminate()
        self.parent.wait(timeout=3)
        state = Path(f"/proc/{pid}/stat")
        deadline = time.monotonic() + 1
        while state.exists() and state.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(.02)
        self.assertTrue(not state.exists() or state.read_text().split()[2] == "Z",
                        "Owned descendant remains alive after supervisor shutdown")
