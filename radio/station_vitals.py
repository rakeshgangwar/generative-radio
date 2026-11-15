"""Read-only, bounded Docker and Linux host measurements for operator receipts."""
import io
import json
import math
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import tarfile
import time

from .watchdog import terminate_process

COMMAND_TIMEOUT = 5
OUTPUT_LIMIT = 65536
ROLES = {'composer', 'renderer', 'broadcaster', 'icecast', 'web'}
ID = re.compile(r'[0-9a-f]{64}')
INSPECT = ('{"id":{{json .Id}},"image":{{json .Image}},'
           '"service":{{json (index .Config.Labels "com.docker.compose.service")}},'
           '"state":{{json .State.Status}},"health":{{if .State.Health}}{{json .State.Health.Status}}{{else}}"none"{{end}},'
           '"started":{{json .State.StartedAt}},"restarts":{{.RestartCount}},"oom":{{.State.OOMKilled}}}')
STATS = '{"id":{{json .ID}},"cpu":{{json .CPUPerc}},"memory":{{json .MemUsage}},"pids":{{json .PIDs}}}'


def run_command(command, stop):
    """Kill/reap only the owned CLI group on timeout, cancellation or output overflow."""
    if stop.is_set():
        raise ValueError('cancelled')
    process = None
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        data = bytearray()
        deadline = time.monotonic() + COMMAND_TIMEOUT
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                if stop.is_set() or time.monotonic() >= deadline:
                    raise ValueError('interrupted')
                if selector.select(min(.1, max(0, deadline-time.monotonic()))):
                    chunk = os.read(process.stdout.fileno(), 8192)
                    if not chunk:
                        break
                    data.extend(chunk)
                    if len(data) > OUTPUT_LIMIT:
                        raise ValueError('output_limit')
            while process.poll() is None:
                if stop.is_set() or time.monotonic() >= deadline:
                    raise ValueError('interrupted')
                stop.wait(min(.1, max(0, deadline-time.monotonic())))
            if process.returncode:
                raise ValueError('command_failed')
        return bytes(data)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('command_unavailable') from exc
    finally:
        if process is not None:
            try:
                terminate_process(process, .2)
            finally:
                process.stdout.close()


def number(value, low=0, high=10**18):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError('invalid_number')
    return value


def parse_memory(value):
    match = re.fullmatch(r'([0-9]+(?:\.[0-9]+)?)\s*(B|kB|KB|MB|GB|TB|KiB|MiB|GiB|TiB)(?:\s*/\s*[0-9.]+\s*[A-Za-z]+)?', value)
    if not match:
        raise ValueError('invalid_memory')
    units = dict(B=1, kB=1000, KB=1000, MB=1000**2, GB=1000**3, TB=1000**4,
                 KiB=1024, MiB=1024**2, GiB=1024**3, TiB=1024**4)
    return round(number(float(match[1])*units[match[2]]))


def parse_watchdog(data):
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
            members = archive.getmembers()
            if len(members) != 1:
                raise ValueError('invalid_report_archive')
            member = members[0]
            if (member.name != 'broadcaster-health.json' or not member.isfile()
                    or not 0 < member.size <= 4096):
                raise ValueError('invalid_report_archive')
            value = json.load(archive.extractfile(member))
        updated = number(value['updated_at'])
        if not 0 <= time.time()-updated <= 90:
            raise ValueError('stale_report')
        if type(value['healthy']) is not bool:
            raise ValueError('invalid_health')
        pid = value['child_pid']
        if value['healthy'] and (type(pid) is not int or pid <= 0):
            raise ValueError('invalid_child')
        kinds = {'healthy', 'starting', 'incomplete', 'silent', 'stalled', 'server_unavailable',
                 'cancelled', 'stream_error', 'child_exited', 'cooldown'}
        if value['kind'] not in kinds:
            raise ValueError('invalid_kind')
        result = {key: value[key] for key in ('healthy', 'kind', 'updated_at')}
        for key in ('restart_count', 'consecutive_failures'):
            if type(value[key]) is not int:
                raise ValueError('invalid_count')
            result[key] = number(value[key], high=10**9)
        if value.get('rms_dbfs') is not None:
            result['rms_dbfs'] = number(value['rms_dbfs'], -150, 10)
        return result
    except (KeyError, TypeError, UnicodeError, tarfile.TarError, OSError) as exc:
        raise ValueError('invalid_report') from exc


def host_vitals(output):
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, _, rest = line.partition(':')
        if key in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}:
            values[key] = int(rest.strip().split()[0])*1024
    if len(values) != 4:
        raise ValueError('missing_host_memory')
    disk = shutil.disk_usage(output)
    return dict(scope='observer-host', memory_bytes=values, load=list(os.getloadavg()),
                cpu_count=os.cpu_count(), disk_total_bytes=disk.total, disk_free_bytes=disk.free)


def rows(data):
    result = [json.loads(line) for line in data.decode().splitlines() if line.strip()]
    if len(result) > 16 or any(type(row) is not dict for row in result):
        raise ValueError('invalid_rows')
    return result


def collect(project, expect_web, stop):
    """Sequential measurements: unknown means incomplete evidence, never clearance."""
    result = dict(started_at=time.time(), services={}, errors=[], assessment='unknown')
    bad = False
    try:
        result['host'] = host_vitals(Path.cwd())
    except (OSError, ValueError):
        result['errors'].append('host_unavailable')
    required = ROLES if expect_web else ROLES-{'web'}
    try:
        raw = run_command(['docker', 'ps', '-a', '--no-trunc', '--filter',
                           'label=com.docker.compose.project='+project, '--format', '{{.ID}}'], stop)
        ids = raw.decode().split()
        if len(ids) > 16 or len(set(ids)) != len(ids) or any(not ID.fullmatch(v) for v in ids):
            raise ValueError('invalid_inventory')
        if not ids:
            bad = True
        else:
            inspected = rows(run_command(['docker', 'inspect', '--format', INSPECT, *ids], stop))
            seen_ids = set()
            for row in inspected:
                role, cid = row['service'], row['id']
                if role not in ROLES or role in result['services'] or cid not in ids or cid in seen_ids:
                    raise ValueError('ambiguous_inventory')
                seen_ids.add(cid)
                if (row['state'] not in {'created', 'running', 'paused', 'restarting', 'removing', 'exited', 'dead'}
                        or row['health'] not in {'healthy', 'unhealthy', 'starting', 'none'}
                        or type(row['oom']) is not bool or type(row['restarts']) is not int
                        or not re.fullmatch(r'sha256:[a-f0-9]{64}', row['image'])
                        or not re.fullmatch(r'[0-9TZ:.+\-]{1,40}', row['started'])):
                    raise ValueError('invalid_inspect')
                result['services'][role] = {key: row[key] for key in
                    ('id', 'image', 'state', 'health', 'started', 'oom', 'restarts')}
                number(row['restarts'], high=10**9)
                if row['state'] != 'running' or row['health'] != 'healthy' or row['oom']:
                    bad = True
            if seen_ids != set(ids):
                raise ValueError('incomplete_inspect')
            try:
                metrics = rows(run_command(['docker', 'stats', '--no-stream', '--no-trunc', '--format', STATS, *ids], stop))
                measured = set()
                by_id = {v['id']: v for v in result['services'].values()}
                for metric in metrics:
                    cid = metric['id']
                    if cid not in by_id or cid in measured:
                        raise ValueError('invalid_stats_inventory')
                    measured.add(cid)
                    cpu = metric['cpu']
                    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)?%', cpu):
                        raise ValueError('invalid_cpu')
                    by_id[cid].update(cpu_percent=number(float(cpu[:-1]), high=10**6),
                                     memory_bytes=parse_memory(metric['memory']),
                                     pids=number(int(metric['pids']), high=10**9))
                if measured != set(ids):
                    raise ValueError('incomplete_stats')
            except (ValueError, KeyError, TypeError, UnicodeError):
                result['errors'].append('stats_unavailable')
            try:
                bc = result['services']['broadcaster']['id']
                result['audio_report'] = parse_watchdog(run_command(
                    ['docker', 'cp', bc+':/data/broadcaster-health.json', '-'], stop))
                if not result['audio_report']['healthy']:
                    bad = True
            except (ValueError, KeyError, TypeError, UnicodeError):
                result['errors'].append('audio_report_unavailable')
        missing = sorted(required-result['services'].keys())
        result['missing_services'] = missing
        bad = bad or bool(missing)
    except (ValueError, KeyError, TypeError, UnicodeError):
        result['errors'].append('inventory_unavailable')
    result['assessment'] = 'not_healthy' if bad else 'unknown' if result['errors'] else 'healthy'
    result['finished_at'] = time.time()
    return result
