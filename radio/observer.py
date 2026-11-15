"""Finite, bounded station observation; does not install or control services."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import signal
import tempfile
import threading
import time

from .station_vitals import collect, host_vitals


def publish(output, name, value):
    payload = json.dumps(value, allow_nan=False, sort_keys=True).encode()+b'\n'
    if len(payload) > 32768:
        raise ValueError('report_size_limit')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output, prefix='.report-', delete=False) as file:
            temporary = Path(file.name)
            file.write(payload)
        os.replace(temporary, output/name)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def record(output, project, expect_web, duration, interval, max_samples, stop):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,62}', project):
        raise ValueError('invalid_project')
    if (not math.isfinite(duration) or not (duration == 0 or 1 <= duration <= 86400)
            or not math.isfinite(interval) or not 1 <= interval <= 600
            or type(max_samples) is not int or not 1 <= max_samples <= 4096):
        raise ValueError('invalid_recording_bounds')
    output = output.resolve()
    if any((parent/'radio.sqlite').exists() for parent in (output, *output.parents)):
        raise ValueError('output_inside_station_data')
    try:
        output.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ValueError('output_already_exists') from exc
    start = time.monotonic()
    summary = dict(state='running', started_at=time.time(), requested_seconds=duration,
                   samples=0, retained=0, healthy=0, not_healthy=0, unknown=0,
                   max_samples=max_samples, interval_seconds=interval, project=project)
    publish(output, 'summary.json', summary)
    try:
        while not stop.is_set():
            sample_start = time.monotonic()
            sample = collect(project, expect_web, stop)
            # Disk values must describe the report filesystem, not the launch directory.
            try:
                sample['host'] = host_vitals(output)
            except (OSError, ValueError):
                sample.setdefault('errors', []).append('host_unavailable')
                if sample['assessment'] == 'healthy':
                    sample['assessment'] = 'unknown'
            sequence = summary['samples']
            sample.update(sequence=sequence, elapsed_seconds=time.monotonic()-start)
            publish(output, f'sample-{sequence % max_samples:04}.json', sample)
            summary['samples'] += 1
            summary['retained'] = min(summary['samples'], max_samples)
            summary[sample['assessment']] += 1
            summary['elapsed_seconds'] = time.monotonic()-start
            publish(output, 'summary.json', summary)
            if duration == 0:
                break
            # Wait through the requested window, never overlap or catch up missed intervals.
            remaining = start+duration-time.monotonic()
            if remaining <= 0:
                break
            stop.wait(min(remaining, max(0, sample_start+interval-time.monotonic())))
            if time.monotonic() >= start+duration:
                break
        summary['state'] = 'cancelled' if stop.is_set() else 'complete'
    except BaseException:
        summary['state'] = 'failed'
        raise
    finally:
        summary.update(finished_at=time.time(), elapsed_seconds=time.monotonic()-start)
        publish(output, 'summary.json', summary)
    return 130 if stop.is_set() else 1 if summary['unknown'] or summary['not_healthy'] else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--project', default='generative-radio')
    parser.add_argument('--expect-web', action='store_true')
    parser.add_argument('--duration', type=float, default=0)
    parser.add_argument('--interval', type=float, default=30)
    parser.add_argument('--max-samples', type=int, default=2048)
    args = parser.parse_args()
    stop = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: stop.set())
    try:
        return record(args.output, args.project, args.expect_web, args.duration,
                      args.interval, args.max_samples, stop)
    except (ValueError, OSError):
        parser.exit(2, 'Observer failed; check arguments, output permissions and any partial summary.\n')


if __name__ == '__main__':
    raise SystemExit(main())
