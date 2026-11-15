# Generative Radio


Read the [product journal](docs/product-journal.md) for the starting idea, current work and directions we may explore next.
**Local station verified:** real rendering, recovery drills, a 30-minute broadcast,
and separate one-hour variety/watchdog runs passed. The listener page and verified
backup/restore commands are implemented. Musical listening acceptance and target
VPS/HTTPS deployment remain open; see [HANDOFF.md](HANDOFF.md).

A CPU-only ambient music station: Python composition → MIDI → FluidSynth →
buffered WAV segments → Liquidsoap → Icecast. No sound card, GPU, AI model or
external music API is needed. This project lives in the existing `radiojack`
checkout; the package and Compose project are named `generative-radio`.

## Listen in your browser

The optional listener page adds play/pause, volume and bounded reconnection at
[localhost:8080](http://localhost:8080). It joins the existing live stream when you
press play. On stream failure it tries six bounded reconnects, waiting at most
15 seconds between attempts. A 30-second interruption can recover without another
click; persistent failure still shows Try again. Pause or sleep-timer expiry cancels
recovery. Browser permission refusal requires a new gesture. The optional chapter
sentence describes the broadcast; buffered audio may be behind it.

To start a new station with the page:

```sh
docker compose -f compose.yaml -f compose.web.yaml up --build -d --wait --wait-timeout 180
```

For a station that is already playing, add only the page without recreating its
core services:

```sh
docker compose -f compose.yaml -f compose.web.yaml build web
docker compose -f compose.yaml -f compose.web.yaml up -d --no-deps --wait web
```

The page/proxy runs non-root with a read-only filesystem and exposes only the
static page and audio mount. Icecast administration and station data stay behind
the proxy. This configuration is local HTTP; public HTTPS deployment still needs
a chosen hostname. Core streaming remains available without the optional page.

Listener tests (Node 20+): `node web/tests/unit.mjs`. For isolated browser QA, run
`npm --prefix web ci --ignore-scripts`, then
`CHROME_BIN=/path/to/chrome npm --prefix web run test:browser` with the page running.
The browser dependency is test-only; the listening page requires no Node server,
frontend build, external font, account or analytics.

## Run locally

Install Docker with Compose and start the Docker engine. Then:

```sh
cp .env.example .env
docker compose up --build -d
docker compose logs -f renderer broadcaster
```

The first build downloads the Python/Debian base and audio tools. Startup renders
a 60-second emergency track before starting Liquidsoap. Open
[the live stream](http://localhost:8000/radio.mp3) in a browser or VLC.
[Icecast status](http://localhost:8000/status.xsl) shows the active mount/listeners.
Only port 8000 is published, bound to **127.0.0.1**.
Audio can begin before the broadcaster's audio-health grace period finishes.
For startup that waits for all health checks, use
`docker compose up --build -d --wait --wait-timeout 180`.

```sh
docker compose exec composer python -m radio status
docker compose ps
docker stats --no-stream
docker compose down
```

`down` retains music and queue state in the named volume. `down -v` destroys
that state. No source files or secrets are mounted into the containers.

## Listen to a standalone preview

```sh
docker compose run --rm --no-deps renderer python -m radio preview --seconds 120 --seed 42
mkdir -p artifacts
docker compose cp renderer:/data/audio/preview.wav artifacts/preview.wav
```

The copy command assumes the normal renderer container exists (`up -d` first).
Alternatively, use `docker compose run --rm -v "$PWD/artifacts:/preview" renderer`
with `RADIO_DATA=/preview` set via `-e` **before** the service name.

To audition a planned station segment, use its station seed and queue position:

```sh
docker compose run --rm --no-deps renderer python -m radio preview \
  --station-seed 20261114 --position 7 --seconds 120
docker compose cp renderer:/data/audio/preview-7.wav artifacts/planned-preview.wav
```

`--seed` retains the original independent-preview behavior; it cannot be combined
with `--station-seed`. Planned previews need a positive `--position`. Preview files
are standalone and do not enter the queue; archive/remove them manually when done.

## Music and queue behavior

The station creates slow A-minor arrangements using five harmonic paths, developed
phrase families and changing pad/bass/keys texture. With `MUSICAL_MEMORY=1`
(default), consecutive queue positions use different harmonic paths. Three-to-five
segment chapters share a motif, register and sound palette, with a spare arrival,
a more active middle and a release. Palettes vary warm/halo pads and electric
piano/vibraphone over acoustic bass. At the default two-minute length a chapter
spans roughly six to ten minutes. Version-2 plans share a 6/8/10-bar phrase
length within the chapter: the melody rests for the final bar while pads and bass
continue. This adds breathing room to the middle stages as well as the edges.
Explicit version-1 plans and legacy composition retain their previous MIDI.

Plans are reconstructed from each saved job's seed and ID, so cleanup, restart,
restore or later station-seed changes do not shift existing queued jobs. Versioned
chapter/stage/program metadata is saved in analysis and renderer logs. The schedule
follows queue order, not confirmed on-air history: skipped/failed jobs can skip
chapter stages or weaken the consecutive-position guarantee on air.

Set `MUSICAL_MEMORY=0` in `.env` and recreate composer/renderer to return new renders
to independent legacy arrangements. No database migration is needed. Cached
fallback and already-ready WAVs remain unchanged; allow roughly 20–25 minutes for
newly rendered arrangements to reach the live stream. The original `--seed`
preview path remains available for comparison. Seed/duration/tempo plus arrangement
context reproduce notes/MIDI within a composer version; upgrades can change music.

The same 256-position score sample reduced equal adjacent four-chord openings from
54 to 0 and broadened first melody notes from 3 pitches to 8. Actual paired 12-segment
rehearsals are in `artifacts/musical-memory-20261115/`: each joins twelve two-minute
renders with five-second FFmpeg crossfades (23m05s). They pass the existing quality
gates and have no detected two-second silence at -50 dB. These are offline listening
comparisons; user listening and the actual target VPS remain acceptance gates.

`SEGMENT_SECONDS` defaults to 120; `BUFFER_SECONDS` to 1200 (20 minutes).
The queue counts five seconds of crossfade overlap per segment. `BPM` is 40–90;
`STATION_SEED` makes generation reproducible. Edit `.env` and run
`docker compose up -d` to apply changes. Existing queued segments retain their
original settings; changes become audible after the queue drains.

The composer adds jobs until the target is reached. A single renderer generates
each job, processes it to a conservative loudness target, checks duration, peak
and excessive silence, then atomically publishes it. Jobs retry up to three times;
abandoned render leases expire after ten minutes. Liquidsoap independently claims
ready files through a local Python command and crossfades them. If the queue runs
dry, it loops cached music, returning to new music at a track boundary.

`served` in status means **dispatched to Liquidsoap**, which may prefetch; it is
not precise now-playing history. A broadcaster crash can skip a dispatched track.
Served files/history expire after one hour. Expired failed jobs also remove
temporary render WAV files left by abruptly stopped workers. Active work and
recently dispatched/failed files are retained. Ready/in-flight jobs are bounded by
the buffer; subprocesses have timeouts and Docker logs rotate. Allow approximately
1 GB for the default audio buffer/history plus container images. SQLite requires
a local Docker volume; do not place the queue on NFS or share it across VPS hosts.
Run one composer, one renderer and one broadcaster per station.

## Verification

Every PR runs Python 3.11/3.14 unit checks and a container integration job. The
integration job builds the actual image, runs tests with FFmpeg installed,
validates a FluidSynth render and Liquidsoap's script, starts all four services,
and decodes/measures ten seconds from the real Icecast mount. It removes only
its own ephemeral Compose project/data. PRs may be merged after these checks pass;
missing checks do not count as clearance.

```sh
python3 -m unittest discover -s tests -v
docker compose run --rm --no-deps broadcaster liquidsoap --check /app/deploy/radio.liq
sh scripts/capture.sh 1800
```

The Liquidsoap check requires the fallback file from the renderer. The recording
uses locally installed FFmpeg and ffprobe and runs in real time. It fails if the
decoded duration is shorter than requested, even when FFmpeg exits successfully
after an early stream disconnect. Incomplete WAV files are retained for diagnosis,
and stale analysis from a previous run is removed. Positive fractional durations
are supported. Set `RADIO_STREAM_URL` to validate another station endpoint:

```sh
RADIO_STREAM_URL=http://localhost:8001/radio.mp3 sh scripts/capture.sh 120
```

Review `artifacts/analysis.log`
for long silence, clipping/peak levels, and listen to transitions in the WAV.
Automatic gates check measurable audio properties; listening establishes whether
the music is worth broadcasting.

While capturing, exercise these recovery cases:

1. `docker compose stop composer renderer` — buffered segments should continue,
   followed by cached fallback music. Use a smaller buffer for a short drill.
2. `docker compose start composer renderer` — new music should resume at a track
   boundary after rendering catches up.
3. `docker compose restart icecast` — Liquidsoap should reconnect. Listener clients
   may need to reconnect; an Icecast restart cannot preserve their TCP sessions.
4. `docker compose restart renderer` — the worker should retry abandoned work once
   its lease expires; the broadcaster keeps playing.

Worker health checks monitor heartbeats. The broadcaster runs a non-root Python
supervisor which owns Liquidsoap and probes the actual decoded MP3 stream.
After a 90-second startup grace it samples 12 seconds of mono audio and waits
30 seconds between completed probes. Three consecutive missing, stalled,
undecodable or continuously quiet samples (below -50 dBFS) trigger a Liquidsoap
restart. Healthy samples reset the failure streak; ordinary short fades remain
audible within the full probe. Icecast outages report unhealthy and rely on
Liquidsoap's reconnection rather than repeatedly restarting the child.

Recovery is limited to three child restarts in a rolling 15-minute window.
Cooldown remains visible as unhealthy; recovery can resume as the window permits.
Shutdown terminates owned processes, and a failed health-report write preserves
otherwise working audio. Docker still restarts exited containers rather than
merely unhealthy ones. Public DNS/HTTPS reachability and host failures require
deployment-level monitoring.

```sh
docker compose exec broadcaster python -m radio.watchdog --health
docker compose exec broadcaster cat /data/broadcaster-health.json
docker compose logs --tail 50 broadcaster
```

The report contains the failure reason, current child PID, restart count and last
successful audio-probe time. Its RMS value is the loudest one-second decoded
window. Stale reports or dead child PIDs fail health checks.
`WATCHDOG_*` settings are documented in `.env.example`; retain the defaults for
normal operation and include startup/decoding and native reconnect time when
changing probe deadlines or intervals.
The supervisor has no Docker socket and cannot restart Icecast, workers or a VPS.

## VPS deployment

Start with the same Compose stack on a Linux CPU VPS. Measure resource use for your
chosen SoundFont and audience before choosing capacity. No VPS deployment is
performed by this project setup. Before public access, replace local passwords,
put Icecast behind an HTTPS reverse proxy, and restrict administrative endpoints.
Keep the local binding and proxy to it. Plan outbound bandwidth: 128 kbps is about
41.5 GB per continuously connected listener per 30 days, before overhead.

## SoundFont and licenses

Code is MIT licensed. The container installs Debian's `timgm6mb-soundfont` package;
its TimGM6mb SoundFont is GPL-2 licensed, separately from this code, with copyright
attributed to Tim Brechbill (2004) and David Bolton (2010). Package license
and attribution are installed at `/usr/share/doc/timgm6mb-soundfont/copyright`.
FluidSynth, Liquidsoap, FFmpeg and Icecast retain their own licenses. Review those
licenses when distributing images or substituting assets. To use another local
SoundFont, mount it read-only and set `SOUNDFONT` in the renderer environment.

Architecture and deferred work: [docs/architecture.md](docs/architecture.md).

Back up, verify, transfer off-host and restore the station: [operator commands](docs/operations.md).

Production setup and recovery: [deployment runbook](docs/deployment.md).

The listener's optional **Sleep timer** offers 15, 30 or 60 minutes. Choosing it before
play arms it for the next explicit start; choosing it while listening starts it
from now. It keeps counting through reconnects. Pause cancels it, and the final 20
seconds fade where browser volume control works before releasing the stream.
The timer belongs to this page and is not saved across reloads. Keep the page
open; a frozen/suspended browser cannot execute its deadline.

Compare instrument libraries using identical, matched-level music: [sound auditions](docs/sound-auditions.md).

Verify decoded audible output from a separate machine: [public listening checks](docs/public-monitoring.md).

For repeatable RAM, CPU, service-health and decoded-audio-report receipts, use the
[bounded host-side station observer](docs/station-observer.md). It does not change playback.
