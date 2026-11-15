"""Read-only HTTPS listener verification, suitable for an independent monitor."""
import argparse
import ipaddress
import json
import math
from pathlib import Path
import re
import os
import selectors
import signal
import subprocess
import sys
import tempfile
import time
import threading
from urllib.parse import urlsplit, urlunsplit

from .watchdog import assess_pcm, terminate_process

SAMPLE_BYTES = 256 * 1024
SECONDS = 3


class ListenerHealthError(ValueError):
    def __init__(self, kind, detail):
        super().__init__(detail)
        self.kind = kind


def validate_origin(url):
    try:
        if (not isinstance(url, str) or not url.isascii()
                or any(ord(c) <= 32 or ord(c) == 127 for c in url) or '?' in url or '#' in url):
            raise ValueError
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username is not None
                or parsed.password is not None or parsed.path not in {'', '/'}
                or parsed.netloc.endswith(':') or (parsed.port is not None and not 1 <= parsed.port <= 65535)):
            raise ValueError
        try:
            ipaddress.ip_address(parsed.hostname)
        except ValueError:
            if (len(parsed.hostname) > 253
                    or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                               for label in parsed.hostname.split('.'))):
                raise ValueError
        return urlunsplit(('https', parsed.netloc, '', '', ''))
    except (ValueError, TypeError, AttributeError):
        raise ListenerHealthError('configuration', 'Use a plain ASCII HTTPS origin without credentials, path, query or fragment.') from None


def check_cancelled(stop):
    if stop is not None and stop.is_set():
        raise ListenerHealthError('cancelled', 'Listener verification cancelled.')


def remaining(deadline, cap, stop=None):
    check_cancelled(stop)
    value = min(cap, deadline - time.monotonic())
    if value <= 0:
        raise ListenerHealthError('timeout', 'Listener verification deadline expired.')
    return value


def owned(arguments, deadline, cap, stop=None):
    process = None
    try:
        budget = remaining(deadline, cap, stop)
        phase_end = min(deadline, time.monotonic() + budget)
        process = subprocess.Popen(arguments, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        while True:
            budget = remaining(phase_end, cap, stop)
            try:
                data, _ = process.communicate(timeout=min(.1, budget))
                check_cancelled(stop)
                return process.returncode, data
            except subprocess.TimeoutExpired:
                continue
    except subprocess.TimeoutExpired:
        raise ListenerHealthError('timeout', 'Listener verification timed out.') from None
    except OSError:
        raise ListenerHealthError('tool', 'Required curl/FFmpeg tool is unavailable or could not start.') from None
    finally:
        if process is not None:
            try:
                terminate_process(process, .5)
            finally:
                if process.stdout is not None:
                    process.stdout.close()


def response_headers(block):
    try:
        lines = block.split(b'\r\n')
        protocol, status, *_ = lines[0].split()
        if not protocol.startswith(b'HTTP/'):
            raise ValueError
        status = int(status)
        kinds = [line.split(b':', 1)[1].strip().split(b';', 1)[0].lower()
                 for line in lines[1:] if line.lower().startswith(b'content-type:')]
        if any(b':' not in line for line in lines[1:]):
            raise ValueError
        return status, kinds
    except (ValueError, IndexError):
        raise ListenerHealthError('response', 'Listener returned invalid HTTPS headers.') from None


def fetch(origin, path, destination, deadline, ca_file, stream=False, stop=None):
    cap = 8 if stream else 5
    limit = SAMPLE_BYTES if stream else 1024 * 1024
    phase_end = min(deadline, time.monotonic() + cap)
    args = ['curl', '--disable', '--silent', '--show-error', '--fail', '--globoff', '--noproxy', '*',
            '--proto', '=https', '--http1.1', '--include', '--no-buffer',
            '--connect-timeout', str(min(3, remaining(phase_end, cap, stop))),
            '--max-time', str(remaining(phase_end, cap, stop))]
    if ca_file is not None:
        args += ['--cacert', str(ca_file)]
    process = None
    try:
        process = subprocess.Popen(args + [origin + path], stdin=subprocess.DEVNULL,
                                   stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
        pending = bytearray()
        header_bytes = size = 0
        checked = capped = expired = False
        with selectors.DefaultSelector() as selector, destination.open('wb') as output:
            selector.register(process.stdout, selectors.EVENT_READ)
            while True:
                check_cancelled(stop)
                budget = phase_end - time.monotonic()
                if budget <= 0:
                    expired = True
                    break
                if not selector.select(min(.1, budget)):
                    continue
                amount = min(65536, limit - size) if checked else min(65536, 65537 - header_bytes - len(pending))
                chunk = os.read(process.stdout.fileno(), max(1, amount))
                if not chunk:
                    break
                if not checked:
                    pending.extend(chunk)
                    while b'\r\n\r\n' in pending:
                        block, tail = pending.split(b'\r\n\r\n', 1)
                        header_bytes += len(block) + 4
                        if header_bytes > 65536:
                            raise ListenerHealthError('response', 'HTTPS response headers exceed the probe budget.')
                        pending = bytearray(tail)
                        status, kinds = response_headers(block)
                        if 100 <= status < 200 and status != 101:
                            continue
                        if status != 200 or kinds != [b'audio/mpeg' if stream else b'text/html']:
                            raise ListenerHealthError('response', 'Listener returned an unexpected HTTPS status or content type.')
                        checked = True
                        break
                    if not checked:
                        if header_bytes + len(pending) > 65536:
                            raise ListenerHealthError('response', 'HTTPS response headers exceed the probe budget.')
                        continue
                    chunk = bytes(pending)
                    pending.clear()
                portion = chunk[:limit - size]
                output.write(portion)
                size += len(portion)
                if size == limit:
                    if not stream:
                        raise ListenerHealthError('response', 'Station page exceeds the probe budget.')
                    capped = True
                    break
        code = process.poll()
        if code is None and not (capped or expired):
            try:
                code = process.wait(timeout=remaining(deadline, .5, stop))
            except subprocess.TimeoutExpired:
                raise ListenerHealthError('timeout', 'Listener request did not finish within its deadline.') from None
        if code == 60:
            raise ListenerHealthError('tls', 'TLS trust or hostname validation failed.')
        if code not in (None, 0, 28):
            raise ListenerHealthError('transport', 'HTTPS listener request failed.')
        if (expired or code == 28) and not stream:
            raise ListenerHealthError('timeout', 'HTTPS page verification timed out.')
        if not checked or size < (4096 if stream else 1):
            raise ListenerHealthError('response', 'Listener returned an invalid or incomplete HTTPS response.')
    except OSError:
        raise ListenerHealthError('tool', 'Required curl tool or temporary output is unavailable.') from None
    finally:
        if process is not None:
            try:
                terminate_process(process, .5)
            finally:
                if process.stdout is not None:
                    process.stdout.close()


def _probe(url, ca_file=None, timeout=20, stop=None):
    origin = validate_origin(url)
    if type(timeout) not in (int, float) or not math.isfinite(timeout) or not 1 <= timeout <= 60:
        raise ListenerHealthError('configuration', 'Verification timeout must be between 1 and 60 seconds.')
    if ca_file is not None:
        try:
            ca_file = Path(ca_file).resolve(strict=True)
            if not ca_file.is_file():
                raise OSError
            with ca_file.open('rb') as source:
                source.read(1)
        except (OSError, ValueError):
            raise ListenerHealthError('configuration', 'Explicit CA file must be a readable regular file.') from None
    started = time.monotonic()
    deadline = started + timeout
    with tempfile.TemporaryDirectory(prefix='radio-listener-health-') as directory:
        page, sample = Path(directory) / 'page.html', Path(directory) / 'sample.mp3'
        fetch(origin, '/', page, deadline, ca_file, stop=stop)
        if b'Generative Radio' not in page.read_bytes():
            raise ListenerHealthError('page', 'HTTPS origin did not serve the station page.')
        fetch(origin, '/radio.mp3', sample, deadline, ca_file, stream=True, stop=stop)
        # Only authenticated local bytes reach the decoder. Force MP3; never parse a playlist/URL.
        code, pcm = owned(['ffmpeg', '-nostdin', '-v', 'error', '-protocol_whitelist', 'file,pipe',
                           '-f', 'mp3', '-i', str(sample), '-map', '0:a:0', '-t', str(SECONDS),
                           '-ar', '8000', '-ac', '1', '-f', 's16le', 'pipe:1'], deadline, 5, stop)
        if code:
            raise ListenerHealthError('decode', 'Authenticated stream sample could not be decoded as MP3.')
        result = assess_pcm(pcm, SECONDS)
        if result.kind != 'healthy':
            raise ListenerHealthError(result.kind, 'Decoded public audio is silent or incomplete.')
    check_cancelled(stop)
    return {'healthy': True, 'url': origin, 'page_verified': True, 'stream_verified': True,
            'decoded_seconds': len(pcm) / 16000, 'rms_dbfs': result.rms_dbfs,
            'elapsed_seconds': round(time.monotonic() - started, 3)}


def probe(url, ca_file=None, timeout=20, stop=None):
    try:
        return _probe(url, ca_file, timeout, stop)
    except OSError:
        raise ListenerHealthError('tool', 'Local temporary or process resources are unavailable.') from None


class SafeParser(argparse.ArgumentParser):
    def error(self, message):
        raise ListenerHealthError('configuration', 'Invalid command arguments; use --help for usage.')


def main():
    parser = SafeParser(description=__doc__)
    parser.add_argument('--url', required=True)
    parser.add_argument('--ca-file', type=Path)
    parser.add_argument('--timeout', type=float, default=20)
    stop = threading.Event()
    def cancelled(*_):
        # Do not raise during Popen construction: wait until its owned handle is registered.
        stop.set()
    previous = {sig: signal.signal(sig, cancelled) for sig in [signal.SIGTERM, signal.SIGINT]}
    try:
        try:
            args = parser.parse_args()
            result = probe(args.url, args.ca_file, args.timeout, stop=stop)
            check_cancelled(stop)
            code = 0
        except ListenerHealthError as error:
            result = {'healthy': False, 'kind': error.kind, 'detail': str(error)}
            code = 130 if error.kind == 'cancelled' else 1
        except KeyboardInterrupt:
            result = {'healthy': False, 'kind': 'cancelled', 'detail': 'Listener verification cancelled.'}
            code = 130
        print(json.dumps(result, indent=2, allow_nan=False))
        return code
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    sys.exit(main())
