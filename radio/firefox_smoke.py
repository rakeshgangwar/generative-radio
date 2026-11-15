"""Finite Linux stock-Firefox playback acceptance using an owned GeckoDriver."""
import argparse
import base64
import binascii
from dataclasses import dataclass
import hashlib
import http.client
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit

from .watchdog import terminate_process

ELEMENT = 'element-6066-11e4-a52e-4f735466cecf'
ASSETS = ('index.html', 'app.js', 'player.js', 'sleep-timer.js',
          'broadcast-context.js', 'style.css', 'dial.svg', 'favicon.svg')


class Problem(Exception):
    def __init__(self, kind):
        allowed = {'deadline', 'response_limit', 'http_error', 'transport_error',
                   'webdriver_error', 'protocol_error', 'invalid_element', 'driver_exited',
                   'invalid_session', 'unexpected_browser', 'invalid_version',
                   'unexpected_origin', 'invalid_volume', 'invalid_screenshot'}
        self.kind = kind if kind in allowed else 'check_failed'
        super().__init__(self.kind)


class Cancelled(BaseException):
    pass


def origin(url):
    try:
        p = urlsplit(url)
        if (p.scheme != 'http' or p.hostname not in {'127.0.0.1', 'localhost', '::1'}
                or p.username is not None or p.password is not None or p.query or p.fragment
                or p.path not in ('', '/') or not 1 <= (p.port or 80) <= 65535
                or p.port == 0 or len(url) > 2048):
            raise ValueError('invalid_local_url')
        return p.scheme, p.hostname, p.port or 80
    except (TypeError, AttributeError) as exc:
        raise ValueError('invalid_local_url') from exc


@dataclass(frozen=True)
class Options:
    driver: Path
    firefox: Path
    output: Path
    url: str = 'http://127.0.0.1:8080/'
    timeout: float = 120

    def __post_init__(self):
        origin(self.url)
        if (type(self.timeout) not in (int, float) or not 1 <= self.timeout <= 300
                or not math.isfinite(self.timeout)):
            raise ValueError('invalid_timeout')
        for name in ('driver', 'firefox', 'output'):
            object.__setattr__(self, name, Path(getattr(self, name)).resolve())
        for path in (self.driver, self.firefox):
            if not path.is_file() or not os.access(path, os.X_OK):
                raise ValueError('executable_unavailable')
        if self.output.exists() or not self.output.parent.is_dir():
            raise ValueError('output_not_fresh')
        if any((p/'radio.sqlite').exists() for p in (self.output, *self.output.parents)):
            raise ValueError('output_inside_station_data')


def publish(output, report):
    payload = json.dumps(report, allow_nan=False, sort_keys=True).encode()+b'\n'
    if len(payload) > 32768:
        raise ValueError('report_size_limit')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=output, prefix='.result-', delete=False) as file:
            temporary = Path(file.name)
            file.write(payload)
        os.replace(temporary, output/'result.json')
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def fetch(host, port, method, path, payload=None, limit=1024*1024):
    connection = http.client.HTTPConnection(host, port, timeout=15)
    try:
        body = None if payload is None else json.dumps(payload).encode()
        connection.request(method, path, body=body, headers={'Content-Type': 'application/json'})
        response = connection.getresponse()
        data = response.read(limit+1)
        if len(data) > limit:
            raise Problem('response_limit')
        if response.status != 200:
            raise Problem('http_error')
        return data
    except (OSError, http.client.HTTPException) as exc:
        raise Problem('transport_error') from exc
    finally:
        connection.close()


class Client:
    def __init__(self, port):
        self.port = port
        self.session = None

    def request(self, method, path, payload=None):
        try:
            value = json.loads(fetch('127.0.0.1', self.port, method, path, payload))['value']
            if type(value) is dict and 'error' in value:
                raise Problem('webdriver_error')
            return value
        except (ValueError, KeyError, TypeError, OverflowError, RecursionError) as exc:
            raise Problem('protocol_error') from exc

    def command(self, method, path, payload=None):
        return self.request(method, '/session/'+self.session+path, payload)

    def script(self, script):
        return self.command('POST', '/execute/sync', {'script': script, 'args': []})

    def until(self, script):
        while self.script(script) is not True:
            time.sleep(.1)

    def element(self, selector):
        value = self.command('POST', '/element', {'using': 'css selector', 'value': selector})
        try:
            ident = value[ELEMENT]
            if type(ident) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', ident):
                raise Problem('invalid_element')
            return ident
        except (TypeError, KeyError) as exc:
            raise Problem('invalid_element') from exc

    def click(self, selector):
        self.command('POST', '/element/'+self.element(selector)+'/click', {})


def run(options):
    if threading.current_thread() is not threading.main_thread() or signal.getitimer(signal.ITIMER_REAL)[0]:
        raise ValueError('requires_unalarmed_main_thread')
    # Reserve fresh output exclusively even if another process raced Options validation.
    options.output.mkdir(mode=0o700)
    profiles = options.output/'.profiles'
    profiles.mkdir(mode=0o700)
    report = dict(version=1, state='running', **{'pass': False}, checks=[], started_at=time.time(),
                  url=options.url, cleanup={'driver_reaped': False, 'profiles_removed': False})
    publish(options.output, report)
    started = time.monotonic()
    process = None
    stage = 'driver'
    old_handlers = {}
    def expired(*_):
        raise Problem('deadline')
    def cancelled(*_):
        raise Cancelled()
    for sig, handler in ((signal.SIGALRM, expired), (signal.SIGTERM, cancelled), (signal.SIGINT, cancelled)):
        old_handlers[sig] = signal.signal(sig, handler)
    signal.setitimer(signal.ITIMER_REAL, options.timeout)
    try:
        with socket.socket() as reserved:
            reserved.bind(('127.0.0.1', 0))
            port = reserved.getsockname()[1]
        report['webdriver_port'] = port
        process = subprocess.Popen([str(options.driver), '--host', '127.0.0.1', '--port', str(port),
                                    '--profile-root', str(profiles), '--log', 'error'],
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        client = Client(port)
        while True:
            if process.poll() is not None:
                raise Problem('driver_exited')
            try:
                ready = client.request('GET', '/status')
                if type(ready) is dict and ready.get('ready') is True:
                    break
            except Problem as error:
                if str(error) not in {'transport_error'}:
                    raise
            time.sleep(.05)
        stage = 'launch'
        session = client.request('POST', '/session', {'capabilities': {'alwaysMatch': {
            'browserName': 'firefox', 'acceptInsecureCerts': False,
            'moz:firefoxOptions': {'binary': str(options.firefox), 'args': ['-headless']}}}})
        try:
            ident, caps = session['sessionId'], session['capabilities']
            if type(ident) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', ident):
                raise Problem('invalid_session')
            if caps['browserName'] != 'firefox' or caps['platformName'] != 'linux':
                raise Problem('unexpected_browser')
            version = caps['browserVersion']
            if type(version) is not str or not re.fullmatch(r'[A-Za-z0-9_. -]{1,80}', version):
                raise Problem('invalid_version')
            report['browser'] = dict(name='firefox', version=version, platform='linux')
            client.session = ident
        except (KeyError, TypeError) as exc:
            raise Problem('invalid_session') from exc
        stage = 'navigate'
        client.command('POST', '/url', {'url': options.url})
        if origin(client.command('GET', '/url')) != origin(options.url):
            raise Problem('unexpected_origin')
        stage = 'idle'
        client.until("return document.querySelector('#player')?.dataset.state==='idle' && document.querySelector('#stream').paused && document.querySelector('#stream').getAttribute('src')===null")
        report['checks'].append({'name': 'idle_without_source', 'pass': True})
        stage = 'start'
        playing = "return document.querySelector('#player').dataset.state==='playing' && document.querySelector('#stream').currentTime>1"
        client.click('#toggle')
        client.until(playing)
        report['checks'].append({'name': 'click_starts_advancing_mp3', 'pass': True})
        stage = 'volume'
        before = client.script("return document.querySelector('#stream').volume")
        if type(before) not in (int, float) or not 0 <= before <= 1 or not math.isfinite(before):
            raise Problem('invalid_volume')
        key = '\ue012' if before > 0 else '\ue014'
        client.command('POST', '/element/'+client.element('#volume')+'/value', {'text': key})
        client.until(f"return document.querySelector('#stream').volume!=={before} && document.querySelector('#stream').volume===document.querySelector('#volume').valueAsNumber/100")
        report['checks'].append({'name': 'keyboard_changes_audio_volume', 'pass': True})
        stage = 'screenshot'
        encoded = client.command('GET', '/screenshot')
        try:
            screenshot = base64.b64decode(encoded, validate=True)
            if not screenshot.startswith(b'\x89PNG\r\n\x1a\n'):
                raise Problem('invalid_screenshot')
        except (ValueError, TypeError, binascii.Error) as exc:
            raise Problem('invalid_screenshot') from exc
        (options.output/'playing.png').write_bytes(screenshot)
        stage = 'pause'
        paused = "return document.querySelector('#player').dataset.state==='paused' && document.querySelector('#stream').paused && document.querySelector('#stream').getAttribute('src')===null"
        client.click('#toggle')
        client.until(paused)
        report['checks'].append({'name': 'pause_releases_source', 'pass': True})
        stage = 'resume'
        client.click('#toggle')
        client.until(playing)
        report['checks'].append({'name': 'resume_advances_mp3', 'pass': True})
        client.click('#toggle')
        client.until(paused)
        stage = 'assets'
        _, host, port = origin(options.url)
        report['asset_sha256'] = {name: hashlib.sha256(fetch(host, port, 'GET', '/'+name, limit=262144)).hexdigest() for name in ASSETS}
        stage = 'close'
        client.command('DELETE', '')
        report.update(state='complete', **{'pass': True})
    except Cancelled:
        report.update(state='cancelled', **{'pass': False}, failure={'stage': stage, 'kind': 'cancelled'})
    except (Problem, OSError, ValueError, KeyError, TypeError, OverflowError, RecursionError) as error:
        # Preserve stage, never remote diagnostics or raw exception text.
        report.update(state='failed', **{'pass': False}, failure={'stage': stage, 'kind': error.kind if isinstance(error, Problem) else 'check_failed'})
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, signal.SIG_IGN)
        try:
            terminate_process(process, .3)
            report['cleanup']['driver_reaped'] = process is None or process.poll() is not None
            shutil.rmtree(profiles)
            report['cleanup']['profiles_removed'] = True
        except (OSError, subprocess.SubprocessError):
            report.update(state='failed', **{'pass': False}, failure={'stage': 'cleanup', 'kind': 'cleanup_failed'})
        finally:
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
            report.update(finished_at=time.time(), elapsed_seconds=time.monotonic()-started)
            publish(options.output, report)
    return 130 if report['state'] == 'cancelled' else 0 if report['pass'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--driver', required=True, type=Path)
    parser.add_argument('--firefox', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--url', default='http://127.0.0.1:8080/')
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    try:
        return run(Options(**vars(args)))
    except (OSError, ValueError):
        parser.exit(2, 'Firefox check requires valid local options and fresh writable output.\n')


if __name__ == '__main__':
    raise SystemExit(main())
