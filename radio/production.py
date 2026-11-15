"""Production setup on the repository host; never run inside a station service."""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import tempfile
import time

from .config import Config
from .watchdog import Options
from .listener_health import probe as probe_listener, ListenerHealthError

REPO = Path(__file__).resolve().parents[1]
ROLES = {'composer', 'renderer', 'broadcaster', 'icecast', 'web'}
FILES = ('compose.yaml', 'compose.web.yaml', 'compose.production.yaml')


class ProductionError(ValueError):
    pass


def validate_domain(domain):
    value = domain.lower()
    try:
        ipaddress.ip_address(value)
    except ValueError:
        pass
    else:
        raise ProductionError('Use an owned DNS hostname, not an IP address.')
    labels = value.split('.')
    reserved = ('localhost', '.localhost', '.local', '.test', '.invalid', '.example',
                'example.com', 'example.net', 'example.org')
    if (len(value) > 253 or len(labels) < 2 or not value.isascii()
            or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part) for part in labels)
            or any(value == item.lstrip('.') or value.endswith('.'+item.lstrip('.')) for item in reserved)):
        raise ProductionError('Use an owned ASCII DNS hostname without a scheme, port, path or wildcard.')
    return value


def _credential(value):
    return (isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]{32,128}', value)
            and len(set(value)) >= 12
            and not any(word in value.lower() for word in ['replace', 'change', 'example', 'placeholder']))


def _secret(exclude=None):
    for _ in range(10):
        value = secrets.token_urlsafe(32)
        if value != exclude and _credential(value):
            return value
    raise ProductionError('Could not generate distinct strong credentials.')


def initialize(env_file, domain, station_seed=None):
    domain = validate_domain(domain)
    seed = secrets.randbelow(2**31) if station_seed is None else station_seed
    if type(seed) is not int or not -(2**62) <= seed < 2**62:
        raise ProductionError('Station seed must be an integer with room for queue IDs.')
    source = _secret()
    admin = _secret(source)
    content = ('# Generated private production configuration. Keep an encrypted off-host copy.\n'
               f'RADIO_DOMAIN={domain}\nICECAST_SOURCE_PASSWORD={source}\n'
               f'ICECAST_ADMIN_PASSWORD={admin}\nSTATION_SEED={seed}\n'
               'SEGMENT_SECONDS=120\nBUFFER_SECONDS=1200\nBPM=60\nMUSICAL_MEMORY=1\n')
    env_file = Path(env_file).absolute()
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', prefix='.env.radio-', dir=env_file.parent, delete=False) as output:
            temporary = Path(output.name)
            os.fchmod(output.fileno(), 0o600)
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        # Hard-link publication is atomic and refuses even an existing broken symlink.
        os.link(temporary, env_file)
        with _directory(env_file.parent) as directory:
            os.fsync(directory)
        return env_file
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


class _directory:
    def __init__(self, path):
        self.path = path
    def __enter__(self):
        self.fd = os.open(self.path, os.O_RDONLY | os.O_DIRECTORY)
        return self.fd
    def __exit__(self, *_):
        os.close(self.fd)


def _private_file(path):
    try:
        info = Path(path).lstat()
    except OSError:
        raise ProductionError('Production env file is missing or unreadable; run init first.') from None
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) & 0o077 or not info.st_mode & stat.S_IRUSR):
        raise ProductionError('Production env file must be a private regular file owned by this user (mode600).')


def validate_config(config):
    """Inspect resolved Compose data; return public facts, never credential values."""
    services = config.get('services', {})
    if not isinstance(services, dict) or set(services) != ROLES:
        raise ProductionError('Production requires exactly the five known station services.')
    try:
        domain = validate_domain(services['web']['environment']['RADIO_DOMAIN'])
        auth = services['icecast']['environment']
        source, admin = auth['ICECAST_SOURCE_PASSWORD'], auth['ICECAST_ADMIN_PASSWORD']
    except (KeyError, TypeError, AttributeError):
        raise ProductionError('Production domain or credentials are missing.') from None
    if not _credential(source) or not _credential(admin) or source == admin:
        raise ProductionError('Generate distinct strong URL-safe source/admin credentials (at least32characters).')
    if config.get('configs') or config.get('secrets'):
        raise ProductionError('Compose configs and secrets are unsupported host-file mounts.')
    networks = config.get('networks', {})
    if (set(networks) != {'default'} or not isinstance(networks['default'], dict)
            or set(networks['default']) - {'name', 'driver', 'ipam'}
            or networks['default'].get('ipam') not in (None, {})
            or networks['default'].get('driver', 'bridge') != 'bridge'):
        raise ProductionError('Production requires an ordinary project-owned bridge network.')
    volumes = config.get('volumes', {})
    if any(v.get('driver_opts') or v.get('driver', 'local') != 'local' for v in volumes.values()):
        raise ProductionError('Production volumes must use ordinary named local storage.')
    if volumes.get('radio-data', {}).get('name', 'radio-data') == volumes.get('web-tls', {}).get('name', 'web-tls'):
        raise ProductionError('Station and certificate volumes must be separate.')
    for role, service in services.items():
        if any(service.get(key) for key in ['configs', 'secrets', 'volumes_from', 'network_mode']):
            raise ProductionError('Alternate file mounts and network namespaces are unsupported.')
        attachments = service.get('networks', {})
        if attachments != {'default': None} and attachments != {'default': {}}:
            raise ProductionError('Services must use only the ordinary default bridge.')
        if (service.get('user') != '10001:10001' or service.get('read_only') is not True
                or 'ALL' not in service.get('cap_drop', [])
                or 'no-new-privileges:true' not in service.get('security_opt', [])
                or service.get('privileged') or service.get('network_mode') == 'host'
                or service.get('pid') == 'host' or service.get('ipc') == 'host'
                or service.get('cap_add') or service.get('devices')):
            raise ProductionError('Production services require non-root read-only isolation without added privileges.')
        temporary = service.get('tmpfs', [])
        targets = set()
        for mount in temporary:
            target, _, raw_options = mount.partition(':')
            raw = raw_options.split(',')
            options = set(raw)
            if len(raw) != len(options) or options & {'exec', 'suid'} or {'ro', 'rw'} <= options:
                raise ProductionError('Conflicting temporary storage options are not permitted.')
            targets.add(target)
            sizes = [re.fullmatch(r'size=(\d+)([kKmM]?)', option) for option in options if option.startswith('size=')]
            if len(sizes) != 1 or any(size is None for size in sizes):
                raise ProductionError('Temporary storage must be bounded and non-executable.')
            size = sizes[0]
            amount = int(size[1]) * {'': 1, 'k': 1024, 'm': 1024**2}[size[2].lower()]
            if not 0 < amount <= 64*1024**2 or not {'noexec', 'nosuid'} <= options:
                raise ProductionError('Temporary storage must be bounded and non-executable.')
            if target == '/tmp' and not {'rw', 'mode=1777'} <= options:
                raise ProductionError('Temporary workspace permissions are invalid.')
            if target == '/config' and 'ro' not in options:
                raise ProductionError('Web configuration storage must be read-only.')
        if len(targets) != len(temporary) or targets != ({'/tmp', '/config'} if role == 'web' else {'/tmp'}):
            raise ProductionError('Only expected temporary storage paths are permitted.')
        env = service.get('environment', {})
        for key, expected in [('ICECAST_SOURCE_PASSWORD', source), ('ICECAST_ADMIN_PASSWORD', admin)]:
            if key in env and env[key] != expected:
                raise ProductionError('Resolved service credentials are inconsistent.')
        mounts = service.get('volumes', [])
        expected_source = 'web-tls' if role == 'web' else 'radio-data'
        data_mounts = [mount for mount in mounts if mount.get('target') == '/data']
        if (len(data_mounts) != 1 or data_mounts[0].get('type') != 'volume'
                or data_mounts[0].get('source') != expected_source or data_mounts[0].get('read_only')):
            raise ProductionError('The expected station/certificate data volume must be mounted.')
        assets = [mount for mount in mounts if mount.get('target') != '/data']
        for mount in assets:
            target = Path(mount.get('target', ''))
            if (role != 'renderer' or len(assets) != 1 or mount.get('type') != 'bind'
                    or mount.get('read_only') is not True or not target.is_relative_to('/soundfonts')
                    or '..' in target.parts or target.suffix.lower() not in {'.sf2', '.sf3'}
                    or str(target) != env.get('SOUNDFONT')
                    or not Path(mount.get('source', '')).is_file()):
                raise ProductionError('Only a renderer SoundFont file may be bind-mounted read-only under /soundfonts.')
        ports = service.get('ports', [])
        if role == 'web':
            try:
                mapping = {(int(p['published']), int(p['target']), p.get('protocol', 'tcp')) for p in ports}
            except (ValueError, TypeError, KeyError):
                raise ProductionError('Invalid public web ports.') from None
            if len(ports) != 2 or mapping != {(80, 8080, 'tcp'), (443, 8443, 'tcp')}:
                raise ProductionError('Production web must publish only TCP80/443 to internal8080/8443.')
        elif role == 'icecast':
            if any(p.get('host_ip') not in {'127.0.0.1', '::1'} or str(p.get('published')) != '8000'
                   or p.get('target') != 8000 or p.get('protocol', 'tcp') != 'tcp' for p in ports):
                raise ProductionError('Icecast administration must remain on loopback8000.')
        elif ports:
            raise ProductionError('Worker/broadcaster ports must not be published.')
    if services['broadcaster']['environment'].get('ICECAST_SOURCE_PASSWORD') != source:
        raise ProductionError('Broadcaster source credential is missing or inconsistent.')
    try:
        for role in ['composer', 'renderer']:
            parsed = Config.from_env(services[role]['environment'])
            if parsed.data != Path('/data') or not -(2**62) <= parsed.seed < 2**62:
                raise ValueError('invalid station data or seed')
        monitor = Options.load(env=services['broadcaster']['environment'])
        if monitor.data != Path('/data') or monitor.stream_url != Options.stream_url or monitor.status_url != Options.status_url:
            raise ValueError('external watchdog URL')
    except (ValueError, TypeError, KeyError):
        raise ProductionError('Invalid resolved music, data or watchdog configuration.') from None
    return {'domain': domain, 'services': sorted(services), 'public_ports': [80, 443]}


def _run(command, *, timeout=30, allowed=(0,)):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise ProductionError('Required Docker Compose or curl command is unavailable.') from None
    except subprocess.TimeoutExpired:
        raise ProductionError('Command timed out; inspect service state before retrying.') from None
    except subprocess.CalledProcessError:
        raise ProductionError('Command failed; inspect Docker/service configuration locally.') from None
    if result.returncode not in allowed:
        raise ProductionError('Command failed; inspect Docker/service configuration locally.')
    return result.stdout


def compose_command(env_file, repo=REPO, project=None, overrides=()):
    if project is not None and not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,62}', project):
        raise ProductionError('Invalid Compose project name.')
    repo = Path(repo).absolute()
    if any(not (repo / name).is_file() for name in FILES):
        raise ProductionError('Run production commands from the complete repository checkout on the host.')
    command = ['docker', 'compose', '--project-directory', str(repo), '--env-file', str(Path(env_file).absolute())]
    if project:
        command += ['--project-name', project]
    for name in FILES:
        command += ['-f', str(repo / name)]
    for path in overrides:
        path = Path(path).absolute()
        if not path.is_file():
            raise ProductionError('Compose override file is missing.')
        command += ['-f', str(path)]
    return command


def preflight(env_file, repo=REPO, project=None, overrides=()):
    _private_file(env_file)
    version = _run(['docker', 'compose', 'version', '--short'], timeout=10).strip()
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)(?:[-+].*)?', version)
    if not match or tuple(map(int, match.groups())) < (2, 24, 4):
        raise ProductionError('Docker Compose2.24.4 or newer is required.')
    command = compose_command(env_file, repo, project, overrides)
    try:
        config = json.loads(_run(command + ['config', '--format', 'json']))
    except (ValueError, TypeError):
        raise ProductionError('Could not resolve the production Compose configuration.') from None
    return command, validate_config(config)


def probe_https(base_url, ca_file=None):
    try:
        return probe_listener(base_url, ca_file)
    except ListenerHealthError as error:
        raise ProductionError(str(error)) from None


def start(env_file, repo=REPO, project=None, build=True, overrides=()):
    command, summary = preflight(env_file, repo, project, overrides)
    arguments = ['up', '--detach', '--wait', '--wait-timeout', '180']
    if build:
        arguments.append('--build')
    _run(command + arguments, timeout=900)
    deadline = time.monotonic() + 90
    while True:
        try:
            return summary | probe_https('https://' + summary['domain'])
        except ProductionError:
            if time.monotonic() >= deadline:
                raise ProductionError('Containers started but public HTTPS/stream verification failed. Check DNS/certificates/logs; services were left running.') from None
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ['init', 'check', 'up', 'status']:
        child = sub.add_parser(name)
        child.add_argument('--env-file', type=Path, default=REPO / '.env.production')
        if name == 'init':
            child.add_argument('--domain', required=True)
            child.add_argument('--seed', type=int)
        else:
            child.add_argument('--project')
            child.add_argument('--override', action='append', type=Path, default=[])
        if name == 'up':
            child.add_argument('--no-build', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            path = initialize(args.env_file, args.domain, args.seed)
            print(f'Created private production configuration: {path}')
        elif args.command == 'check':
            print(json.dumps(preflight(args.env_file, project=args.project, overrides=args.override)[1], indent=2))
        elif args.command == 'up':
            print(json.dumps(start(args.env_file, project=args.project, build=not args.no_build, overrides=args.override), indent=2))
        else:
            command, _ = preflight(args.env_file, project=args.project, overrides=args.override)
            print(_run(command + ['ps']), end='')
    except (ProductionError, OSError) as exc:
        parser.exit(1, f'{args.command}: {exc}\n')


if __name__ == '__main__':
    main()
