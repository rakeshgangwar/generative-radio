# Production deployment

Use a Linux host you control with Python 3.11+, Docker Engine, Docker Compose
2.24.4+ and curl. The station uses CPU rendering; no GPU or API key is needed.
Allow disk space for images, roughly an hour of retained PCM audio, the ready
buffer and backups. Measure capacity on your target rather than relying on this
machine's timing. The target host and domain have not yet been selected.

## First installation

Clone this repository at a reviewed release commit. Point your owned domain's A
record at the host; publish an AAAA record only when IPv6 reaches the same host.
Allow inbound TCP 80/443 and outbound DNS/HTTPS. Keep Docker access restricted to
trusted operators. Enable Docker at boot using your distribution's service tools.
The containers restart unless explicitly stopped.

From the checkout on the host:

```sh
python3 -m radio.production init --domain radio.your-owned-domain.tld
python3 -m radio.production check
python3 -m radio.production up
python3 -m radio.production status
```

Replace the domain with your actual owned hostname. `init` creates mode600
`.env.production` with independent random source/admin passwords and a station
seed; it refuses to overwrite any existing file or symlink. Keep an encrypted
off-host copy. Never source this file as a shell script or commit it. The example
template has intentionally unusable blank credentials. `check` resolves and
validates the actual Compose configuration, including shell environment overrides,
without starting services or printing secrets.

`up` builds, starts the five services, waits for container health, then checks the
public HTTPS page and MP3 stream with normal CA/hostname validation. Successful
container health alone does not establish public reachability. Failed verification
leaves services and volumes available for diagnosis. Check DNS, firewall, ACME
rate limits and Caddy logs before retrying. Never bypass TLS verification.

Only the web gateway publishes TCP80/443. Caddy runs internally on8080/8443;
HTTP redirects use the standard public HTTPS port. Icecast's8000 administrative
endpoint remains on loopback. The proxy serves only the page/assets and GET/HEAD
`/radio.mp3`; admin/status/database paths return404. All services use UID10001,
read-only roots, bounded temporary storage and dropped capabilities. The web
service has its own certificate volume and no access to station data.

## Health, capture and restart

Use the same project and overrides for every operation. Explicit Compose commands
must include the private env file and all three configuration files:

```sh
docker compose --env-file .env.production -f compose.yaml -f compose.web.yaml -f compose.production.yaml ps
docker compose --env-file .env.production -f compose.yaml -f compose.web.yaml -f compose.production.yaml logs --tail 100 web broadcaster
RADIO_STREAM_URL=https://radio.your-owned-domain.tld/radio.mp3 sh scripts/capture.sh 1800
```

The capture helper needs local FFmpeg/ffprobe and curl. It verifies requested
recording length and writes silence/level analysis under `artifacts/`. For an
explicitly trusted private CA, set `RADIO_TLS_CA_FILE` to its PEM certificate.
Do not install a test CA system-wide. Production normally uses public ACME trust.

After an intentional host reboot, check all five health states, the authenticated
public URL and decoded audio. Watch queue replenishment, memory, disk and restart
counts through at least one retention interval. The existing [operations
runbook](operations.md) describes watchdog diagnostics, leases and failure drills.
A public launch still requires this target-host validation and human listening.

## Upgrade and rollback

Keep the private env file, station data and certificate volume across upgrades.
Record the current Git commit and image IDs first. Tag the currently running core
and web images with private local rollback tags before building replacements;
`docker compose images` identifies them. Keep those images until the upgrade has
passed actual playback and recovery checks. Create and verify a backup using the
operations runbook before changing data or software.

Fetch and check out a reviewed commit, run `check`, then `up`. Run a decoded capture
and verify ready/served queues and watchdog health. Expect already-rendered audio
to drain naturally; do not delete the buffer to force new music on air.

For rollback, use the earlier compatible checkout and retained images. An override
can set `image: generative-radio:rollback` for composer, renderer, broadcaster and
Icecast, and a compatible production web image for web. Pass the override with
`--override /absolute/path/rollback.yaml` to `check` and `up --no-build`. Do not
replace the TLS gateway with an older image that lacks the production Caddyfile.
The legacy music toggle `MUSICAL_MEMORY=0` changes future renders, preserving
already-ready tracks. Do not use `down --volumes`, prune volumes or overwrite the
private configuration during an upgrade/rollback.

## Backups and recovery

Follow [verified backup and isolated restore](operations.md) for queue/audio
snapshots and archive verification. Adapt the project volume name when using
`--project`; the default data volume is `generative-radio_radio-data`.
Copy verified snapshots off-host to a destination you control. Separately preserve
the private env file, reviewed commit/image identifiers, licensed SoundFonts and
Caddy's certificate volume (`generative-radio_web-tls` by default). Certificates
contain private keys: store their backup encrypted and restrict access. A queue
snapshot alone does not preserve credentials or TLS identity.

Restore queue/audio only into a fresh volume and validate it in isolation first.
To switch production to a verified external data volume, write an override:

```yaml
volumes:
  radio-data:
    external: true
    name: radio-restored
```

Then use `python3 -m radio.production check --override /absolute/path/restore.yaml`
and `up` with the same override in an announced maintenance window. Keep the old
volume intact for rollback. Never point a second running project at the same data.
A custom licensed SoundFont may be bound read-only into the renderer under
`/soundfonts/`, with `SOUNDFONT` set to that exact sf2/sf3 file; do not share it
with the gateway.

## Local production rehearsal

Build images without replacing a live station's tags, then exercise the real
profile with disposable loopback ports and its own volumes:

```sh
docker build -t generative-radio:production-test .
docker build -t generative-radio-web:production-test web
python3 scripts/production-smoke.py --project radio-smoke-local-1 \
  --core-image generative-radio:production-test \
  --web-image generative-radio-web:production-test
```

The smoke script refuses existing projects, uses ports18082/18443, tests explicit
local-CA trust, records real audio, replaces only its web container and checks
certificate persistence, then removes only its disposable project/volumes.
It changes no host trust store and performs no public deployment. Public DNS,
ACME issuance, target reboot and off-host restore must be exercised on the actual
target before claiming production acceptance.
