#!/usr/bin/env python3
"""Exercise the production profile on disposable loopback-only infrastructure."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from radio.production import initialize, preflight, compose_command, probe_https


def run(command, timeout=240):
    result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        # Compose's resolved environment contains passwords; never dump commands/config.
        raise RuntimeError('Smoke command failed; isolated services will be removed.')
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--core-image', default='generative-radio:local')
    parser.add_argument('--web-image', default='generative-radio-web:local')
    parser.add_argument('--artifacts', type=Path, default=Path('artifacts/production-smoke'))
    args = parser.parse_args()
    if not args.project.startswith('radio-smoke-'):
        parser.error('Use a unique disposable radio-smoke- project name.')
    # Refuse to touch an existing project, including stopped containers or retained volumes.
    for kind in ['container', 'volume', 'network']:
        if run(['docker', kind, 'ls', '-q', '--filter', 'label=com.docker.compose.project='+args.project]).strip():
            parser.error('Disposable project name already exists; choose another.')
    args.artifacts.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='radio-production-smoke-') as directory:
        temp = Path(directory)
        private = temp / '.env.production'
        initialize(private, 'radio.my-station.net', 42)
        _, public = preflight(private, project=args.project)
        override = temp / 'local.yaml'
        override.write_text('services:\n' + ''.join(
            f'  {role}:\n    image: {json.dumps(args.core_image)}\n    environment:\n      SEGMENT_SECONDS: "20"\n      BUFFER_SECONDS: "20"\n'
            for role in ['composer', 'renderer', 'broadcaster']) +
            f'  icecast:\n    image: {json.dumps(args.core_image)}\n    ports: !reset []\n' +
            f'  web:\n    image: {json.dumps(args.web_image)}\n    environment:\n      RADIO_DOMAIN: localhost\n'
            '    ports: !override\n      - "127.0.0.1:18082:8080"\n      - "127.0.0.1:18443:8443"\n')
        command = compose_command(private, project=args.project, overrides=[override])
        try:
            run(command + ['up', '--detach', '--no-build', '--wait', '--wait-timeout', '180'])
            ids = run(command + ['ps', '-q']).split()
            assert len(ids) == 5, 'Five healthy services required'
            inspection = json.loads(run(['docker', 'inspect', *ids]))
            for container in inspection:
                host = container['HostConfig']
                assert container['Config']['User'] == '10001:10001'
                assert host['ReadonlyRootfs'] and host['CapDrop'] == ['ALL']
                assert 'no-new-privileges:true' in host['SecurityOpt']
                assert container['State']['Health']['Status'] == 'healthy'
            web = run(command + ['ps', '-q', 'web']).strip()
            ca = temp / 'root.crt'
            run(['docker', 'cp', web+':/data/caddy/pki/authorities/local/root.crt', str(ca)])
            origin = 'https://localhost:18443'
            try:
                probe_https(origin)
            except ValueError:
                pass
            else:
                raise AssertionError('Untrusted local CA was accepted')
            verified = probe_https(origin, ca)
            assert verified['healthy'] and abs(verified['decoded_seconds'] - 3) < .1
            assert verified['rms_dbfs'] >= -50
            curl = ['curl', '--disable', '--silent', '--show-error', '--noproxy', '*', '--max-time', '10']
            redirect = run(curl + ['-I', '-H', 'Host: localhost', 'http://127.0.0.1:18082/'])
            assert 'location: https://localhost/' in redirect.lower(), redirect
            for path in ['/admin/', '/status-json.xsl', '/radio.sqlite']:
                status = run(curl + ['--cacert', str(ca), '-o', os.devnull, '-w', '%{http_code}', origin+path])
                assert status == '404', (path, status)
            # Run the exact capture helper and real decoder inside a disposable media container.
            capture = temp / 'capture'
            capture.mkdir(); capture.chmod(0o777)
            (capture/'artifacts').mkdir(); (capture/'artifacts').chmod(0o777)
            ca.chmod(0o644)
            run(['docker', 'run', '--rm', '--network', 'container:'+web, '--read-only', '--cap-drop', 'ALL',
                 '--tmpfs', '/tmp:rw,noexec,nosuid,size=64m,mode=1777',
                 '-v', str(ca)+':/tmp-ca/root.crt:ro', '-v', str(capture)+':/capture',
                 '-v', str(REPO/'scripts/capture.sh')+':/capture.sh:ro', '-w', '/capture',
                 '-e', 'RADIO_STREAM_URL=https://localhost:8443/radio.mp3',
                 '-e', 'RADIO_TLS_CA_FILE=/tmp-ca/root.crt', args.core_image,
                 'sh', '/capture.sh', '5'], timeout=45)
            # Verify persisted trust across replacement of the TLS process/container.
            digest = hashlib.sha256(ca.read_bytes()).hexdigest()
            run(command + ['up', '--detach', '--no-build', '--force-recreate', '--no-deps', '--wait', '--wait-timeout', '60', 'web'])
            web = run(command + ['ps', '-q', 'web']).strip()
            replacement = temp/'replacement.crt'
            run(['docker', 'cp', web+':/data/caddy/pki/authorities/local/root.crt', str(replacement)])
            assert hashlib.sha256(replacement.read_bytes()).hexdigest() == digest
            for attempt in range(10):
                try:
                    probe_https(origin, ca)
                    break
                except ValueError:
                    if attempt == 9: raise
                    time.sleep(1)
            report = {'public_preflight': public, 'local_tls': verified,
                      'services_hardened': 5, 'private_routes': '404',
                      'untrusted_ca_rejected': True, 'capture_seconds': 5,
                      'certificate_persisted': True, 'root_ca_sha256': digest}
            (args.artifacts/'result.json').write_text(json.dumps(report, indent=2)+'\n')
            (args.artifacts/'capture-analysis.log').write_text((capture/'artifacts/analysis.log').read_text())
            print(json.dumps(report, indent=2))
        finally:
            run(command + ['down', '--volumes', '--remove-orphans'], timeout=90)


if __name__ == '__main__':
    main()
