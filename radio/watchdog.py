"""Bounded decoded-audio monitoring and ownership of the Liquidsoap process."""
import argparse
import array
from collections import deque
from dataclasses import dataclass
import json
import logging
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time

log = logging.getLogger("radio.watchdog")


@dataclass(frozen=True)
class Options:
    data: Path = Path("/data")
    stream_url: str = "http://icecast:8000/radio.mp3"
    status_url: str = "http://icecast:8000/status-json.xsl"
    grace: float = 90
    probe_seconds: float = 12
    interval: float = 30
    timeout: float = 20
    failures: int = 3
    restart_limit: int = 3
    restart_window: float = 900
    stop_timeout: float = 3

    def __post_init__(self):
        bounds = {"grace": (0, 300), "probe_seconds": (.25, 60),
                  "interval": (.1, 300), "timeout": (.5, 90),
                  "failures": (1, 10), "restart_limit": (1, 10),
                  "restart_window": (1, 3600), "stop_timeout": (.1, 5)}
        for name, (low, high) in bounds.items():
            value = getattr(self, name)
            if not math.isfinite(value) or not low <= value <= high:
                raise ValueError(f"watchdog {name} must be between {low} and {high}")
        if self.timeout <= self.probe_seconds:
            raise ValueError("watchdog timeout must exceed probe duration")

    @classmethod
    def load(cls, env=None):
        env = os.environ if env is None else env
        values = {"data": Path(env.get("RADIO_DATA", "/data")),
                  "stream_url": env.get("RADIO_STREAM_URL", cls.stream_url),
                  "status_url": env.get("RADIO_STATUS_URL", cls.status_url)}
        names = {"grace": "GRACE_SECONDS", "probe_seconds": "PROBE_SECONDS",
                 "interval": "INTERVAL_SECONDS", "timeout": "TIMEOUT_SECONDS",
                 "failures": "FAILURES", "restart_limit": "RESTART_LIMIT",
                 "restart_window": "RESTART_WINDOW_SECONDS"}
        for name, suffix in names.items():
            raw = env.get(f"WATCHDOG_{suffix}")
            if raw is not None:
                values[name] = int(raw) if name in {"failures", "restart_limit"} else float(raw)
        return cls(**values)


@dataclass(frozen=True)
class ProbeResult:
    kind: str
    detail: str = ""
    rms_dbfs: float | None = None


def assess_pcm(data: bytes, seconds: float) -> ProbeResult:
    frames = len(data) // 2
    if len(data) % 2 or not .95 * seconds * 8000 <= frames <= 1.05 * seconds * 8000:
        return ProbeResult("incomplete", f"decoded {frames / 8000:.3f}s, expected {seconds}s")
    samples = array.array("h", data)
    if sys.byteorder != "little":
        samples.byteswap()
    windows = [samples[i:i + 8000] for i in range(0, len(samples), 8000)]
    peak_power = max(sum(v * v for v in w) / len(w) for w in windows)
    level = 10 * math.log10(max(peak_power, 1) / 32768**2)
    return ProbeResult("silent" if level < -50 else "healthy", rms_dbfs=level)


class RestartPolicy:
    def __init__(self, failures, limit, window):
        self.threshold, self.limit, self.window = failures, limit, window
        self.failures = 0
        self.restarts = deque()

    def can_restart(self, now):
        while self.restarts and self.restarts[0] <= now - self.window:
            self.restarts.popleft()
        return len(self.restarts) < self.limit

    def observe(self, kind, now):
        if kind in {"healthy", "server_unavailable", "cancelled"}:
            self.failures = 0
            return False
        self.failures += 1
        return (kind == "child_exited" or self.failures >= self.threshold) and self.can_restart(now)

    def record_restart(self, now):
        self.restarts.append(now)
        self.failures = 0


def report_is_healthy(path: Path, now=None) -> bool:
    try:
        report = json.loads(path.read_text())
        timestamp, pid = report["updated_at"], report["child_pid"]
        if report["healthy"] is not True or not isinstance(timestamp, (float, int)):
            return False
        age = (time.time() if now is None else now) - timestamp
        if not math.isfinite(age) or not 0 <= age <= 90:
            return False
        if type(pid) is not int or pid <= 0:
            return False
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def terminate_process(process, timeout=3):
    """Terminate the owned process group, escalate if needed, and reap it."""
    if process is None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=timeout)
    # The leader can exit before a descendant that ignored SIGTERM.
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _run_owned(command, deadline, stop, stop_timeout, capture=False):
    """Bound the whole external operation, including DNS and response headers."""
    if stop.is_set():
        return None, b"", "cancelled"
    process = subprocess.Popen(command, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL,
                               start_new_session=True)
    try:
        while not stop.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None, b"", "stalled"
            try:
                data, _ = process.communicate(timeout=min(.2, remaining))
                return process.returncode, data or b"", None
            except subprocess.TimeoutExpired:
                continue
        return None, b"", "cancelled"
    finally:
        try:
            terminate_process(process, stop_timeout)
        finally:
            if process.stdout is not None:
                process.stdout.close()


def probe_stream(options: Options, stop: threading.Event) -> ProbeResult:
    deadline = time.monotonic() + options.timeout
    status_command = ["curl", "--disable", "--silent", "--fail", "--noproxy", "*", "--output", os.devnull,
                      "--max-time", str(min(3, options.timeout)), options.status_url]
    code, _, problem = _run_owned(status_command, min(deadline, time.monotonic() + 3),
                                  stop, options.stop_timeout)
    if problem == "cancelled":
        return ProbeResult("cancelled")
    if problem or code:
        return ProbeResult("server_unavailable", "Icecast status is unreachable or timed out")
    command = ["ffmpeg", "-nostdin", "-v", "error", "-probesize", "32768",
               "-analyzeduration", "1000000", "-rw_timeout", "5000000",
               "-i", options.stream_url, "-t", str(options.probe_seconds), "-vn",
               "-ac", "1", "-ar", "8000", "-f", "s16le", "pipe:1"]
    code, data, problem = _run_owned(command, deadline, stop, options.stop_timeout, capture=True)
    if problem:
        return ProbeResult(problem, "audio probe interrupted or exceeded its deadline")
    if code:
        return ProbeResult("stream_error", f"FFmpeg exited {code}")
    return assess_pcm(data, options.probe_seconds)


class Supervisor:
    def __init__(self, options: Options, command=None, probe=probe_stream):
        self.options = options
        self.command = command or ["liquidsoap", "/app/deploy/radio.liq"]
        self.probe = probe
        self.stop = threading.Event()
        self.policy = RestartPolicy(options.failures, options.restart_limit, options.restart_window)
        self.child = None
        self.started_once = False
        self.crashes = 0
        self.next_start = 0.
        self.next_probe = 0.
        self.last_audio = None
        self.last_audio_at = None
        self.result = ProbeResult("starting")
        options.data.mkdir(parents=True, exist_ok=True)
        self.report_path = options.data / "broadcaster-health.json"

    def _start(self, now):
        if self.started_once:
            self.policy.record_restart(now)
        self.started_once = True
        self.last_audio = self.last_audio_at = None
        self.result = ProbeResult("starting")
        try:
            self.child = subprocess.Popen(self.command, start_new_session=True)
        except OSError as exc:
            self.child = None
            self.crashes += 1
            self.next_start = now + min(30, 2 ** min(self.crashes - 1, 5))
            self.result = ProbeResult("child_exited", str(exc)[:300])
            log.exception("Could not start Liquidsoap")
            return
        self.next_probe = now + self.options.grace
        log.info("Started Liquidsoap pid=%s recovery_attempts=%s", self.child.pid,
                 len(self.policy.restarts))

    def _publish(self):
        now = time.monotonic()
        self.policy.can_restart(now)
        alive = self.child is not None and self.child.poll() is None
        healthy = (alive and self.result.kind == "healthy" and self.last_audio is not None
                   and now - self.last_audio <= max(90, self.options.interval + self.options.timeout + 5))
        report = {"updated_at": time.time(), "healthy": healthy,
                  "child_pid": self.child.pid if alive else None,
                  "kind": self.result.kind, "detail": self.result.detail,
                  "last_audio_at": self.last_audio_at,
                  "consecutive_failures": self.policy.failures,
                  "restart_count": len(self.policy.restarts),
                  "rms_dbfs": self.result.rms_dbfs}
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", dir=self.options.data,
                                             prefix=".broadcaster-health-", delete=False) as output:
                temporary = Path(output.name)
                json.dump(report, output, allow_nan=False)
            os.replace(temporary, self.report_path)
        except OSError:
            # A full/unwritable volume must not stop otherwise healthy playback.
            # The previous report expires naturally and health will then fail.
            log.exception("Could not publish audio-health report; retaining broadcaster")
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass

    def run(self):
        previous_handlers = {}
        if threading.current_thread() is threading.main_thread():
            for sig in [signal.SIGTERM, signal.SIGINT]:
                previous_handlers[sig] = signal.signal(sig, lambda *_: self.stop.set())
        last_publish, previous_kind = 0., None
        try:
            self._publish()  # Invalidate reports left by a prior supervisor.
            while not self.stop.is_set():
                now = time.monotonic()
                if self.child is not None and self.child.poll() is not None:
                    log.warning("Liquidsoap exited code=%s", self.child.returncode)
                    terminate_process(self.child, self.options.stop_timeout)
                    self.child = None
                    self.crashes += 1
                    self.next_start = now + min(30, 2 ** min(self.crashes - 1, 5))
                    self.result = ProbeResult("child_exited", "Liquidsoap exited")
                if self.child is None:
                    if self.started_once and not self.policy.can_restart(now):
                        if self.result.kind != "cooldown":
                            log.error("Restart budget exhausted; waiting for rolling window")
                        self.result = ProbeResult("cooldown", "restart budget exhausted")
                    elif now >= self.next_start:
                        self._start(now)
                elif now >= self.next_probe:
                    try:
                        self.result = self.probe(self.options, self.stop)
                    except Exception as exc:
                        log.exception("Audio probe failed")
                        self.result = ProbeResult("stream_error", str(exc)[:300])
                    now = time.monotonic()
                    self.next_probe = now + self.options.interval
                    if self.result.kind == "healthy":
                        if self.last_audio is None or previous_kind != "healthy":
                            log.info("Decoded audio healthy level=%s dBFS", self.result.rms_dbfs)
                        self.last_audio, self.last_audio_at = now, time.time()
                        self.crashes = 0
                    elif self.result.kind != "cancelled":
                        log.warning("Audio unhealthy kind=%s reason=%s", self.result.kind,
                                    self.result.detail)
                    if self.policy.observe(self.result.kind, now) and not self.stop.is_set():
                        log.warning("Restarting Liquidsoap after consecutive audio failures")
                        terminate_process(self.child, self.options.stop_timeout)
                        self.child = None
                        self._start(time.monotonic())
                    elif (self.policy.failures >= self.options.failures
                          and not self.policy.can_restart(now)):
                        log.error("Restart budget exhausted; retaining child until recovery is allowed")
                        self.result = ProbeResult("cooldown", "restart budget exhausted")
                if now - last_publish >= 5 or self.result.kind != previous_kind:
                    self._publish()
                    last_publish, previous_kind = now, self.result.kind
                self.stop.wait(.1)
        finally:
            terminate_process(self.child, self.options.stop_timeout)
            self.child = None
            self.result = ProbeResult("stopped")
            self._publish()
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description="Supervise Liquidsoap and probe decoded audio")
    parser.add_argument("--health", action="store_true", help="Check the latest audio-health report")
    args = parser.parse_args()
    if args.health:
        path = Path(os.getenv("RADIO_DATA", "/data")) / "broadcaster-health.json"
        raise SystemExit(0 if report_is_healthy(path) else 1)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    Supervisor(Options.load()).run()


if __name__ == "__main__":
    main()
