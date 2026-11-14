# Generative Radio — laptop handoff

Updated: 15 November 2026 (Asia/Kolkata).

## Goal and agreed scope

Build a 24×7 VPS-based generative ambient music station, starting with a local
working MVP. Use Python, FluidSynth, Liquidsoap, Icecast and Docker Compose.
Generate coherent original arrangements using music theory and seeded probability;
render ahead of playback into a 10–30 minute buffer. No GPU or AI model dependency
in the MVP. A GPU on the next laptop is optional for future model experiments.

The user initially requested a new `generative-radio` repository, then explicitly
asked to use the current checkout (`radiojack`). The code/package and Compose
project are named `generative-radio`. The user subsequently chose to switch laptops
and asked to publish this work to a private GitHub repository.

Architecture source conversation:
https://chatgpt.com/share/6af89399-506c-83ee-a3cd-66072b4e141b

## What is implemented

- Deterministic ambient composer: four-chord A-minor arc, pads, bass and sparse
  electric-piano motifs, with a Standard MIDI File writer using only Python's
  standard library.
- FluidSynth fast rendering, FFmpeg loudness processing, fades, peak/silence checks
  and atomic publication of completed WAV files.
- Shared local SQLite queue with transactional claims, render leases, three-attempt
  retry limit, bounded ahead-of-playback work and hourly dispatched-file retention.
- Separate composer, renderer and Liquidsoap broadcaster roles, plus Icecast.
- Cached fallback music, five-second crossfades, localhost-only stream binding,
  non-root containers, rotating logs and basic health checks.
- Configuration examples, MIT license, architecture notes, README and a script
  to record/analyze a real-time acceptance broadcast.

## Verified versus pending

### Recovery and acceptance run — 14–15 November 2026

The user requested fallback/recovery drills, a 30-minute listening test and an
ordered startup of all four services. Failure injection uses an isolated Compose
project, `generative-radio-drill`, with its own volume, 20-second segments,
20-second target buffer and localhost port 8001. The main station on port 8000
continues playing and is being recorded independently.

Verified drill results:

- Stopped the drill composer and renderer, drained all generated tracks, and
  observed Liquidsoap switch to cached fallback. Restarted generation and observed
  recovery to generated music at a fallback track boundary.
- Recorded that sequence continuously for 240 seconds. FFmpeg reported no silence
  events at -50 dB for 2 seconds or longer; overall peak was -8.87 dBFS and RMS
  -24.76 dBFS. Evidence: `artifacts/recovery-20261114/`.
- Restarted drill Icecast. Liquidsoap detected a broken pipe and reconnected
  automatically approximately four seconds later; mount health passed and a new
  10-second recording decoded successfully. Existing listener TCP sessions cannot
  survive an Icecast restart.
- Restarted the drill broadcaster; it reconnected without intervention, mount
  health passed, and a new 10-second recording decoded successfully.
- Killed the drill renderer with SIGKILL while job 11 was rendering (600-second
  segment, attempt 1), then restarted it. Without editing job timestamps, the
  worker reclaimed it after the real ten-minute lease expiry. Attempt 2 rendered
  successfully in 18.1 seconds, passed audio gates, and Liquidsoap logged playback
  of `/data/audio/11.wav` after fallback. `/data/work` was empty afterward. A
  20-second post-recovery recording had no >=2-second silence and a peak of
  -9.67 dBFS. Job states and full drill logs are saved with the audio evidence.
- The isolated drill containers/network were removed with `down` after testing.
  Its named test volume was retained; the main station was not interrupted.

Completed a fresh 30-minute main-station recording, with 56 resource/queue/health
samples from 23:52 on 14 November to 00:22 on 15 November (Asia/Kolkata):

- Decoded audio duration: exactly 1800.000 seconds, stereo PCM16 at 44.1 kHz.
- No silence events at -50 dB for 2 seconds or longer. Overall peak -8.05 dBFS;
  RMS -25.20 dBFS; integrated loudness -23.0 LUFS; true peak -8.1 dBFS; loudness
  range 5.1 LU. No clipping observed by these measurements.
- All health samples were healthy, with zero restarts/OOM kills and no recent
  queue errors. Generation replenished the buffer throughout the run.
- Broadcaster RAM stayed between 226.9 and 228.6 MiB. Composer used 14.1–15.0
  MiB; renderer 15.0–71.8 MiB including sampled render activity; Icecast 4.2–6.2
  MiB. These are sampled ranges, not guaranteed peak allocations. No broadcaster
  memory growth trend was evident over this run; a longer soak is still needed.
- Evidence: `artifacts/acceptance-20261114/broadcast-30min.wav`,
  `analysis-30min.log`, `loudness-30min.log`, `vitals.jsonl`,
  `resource-summary.json`, `queue-before-restart.json`, and
  `services-before-restart.log` in the same directory. Artifacts are ignored by Git.

**Technical continuity and recovery checks passed. Musical variety is not yet
accepted:** user listening feedback during the run was **"Too repetitive."**
Earlier feedback was that the melody sounds nice. No composition changes were
made during this run.

Completed the requested final startup: stopped the main stack, then started
**Icecast → composer → renderer → broadcaster** sequentially with `--no-deps
--wait`, requiring each service to become healthy before starting the next. All
four reported healthy. Startup evidence is saved in
`artifacts/acceptance-20261114/ordered-startup.log`. The main stream remains at
`http://localhost:8000/radio.mp3`; reconnect the player if its TCP connection was
closed by this intentional restart. No main data volume was deleted.
A fresh 30-second post-startup recording decoded successfully, with no >=2-second
silence and a peak of -9.51 dBFS. Liquidsoap then logged fallback-to-generated
playback of `/data/audio/27.wav`; the queue had 11 ready tracks and no recent
errors, and all four services remained healthy.

Next work: address musical repetition, then run a longer unattended soak and
verify retention/cleanup after at least an hour. Public VPS deployment and an
external stream watchdog remain deferred.

### Continuation on the new laptop — 14 November 2026

- Docker 29.8.2 / Compose 5.6.0: image build completed successfully.
- All eight unit tests pass on this laptop.
- Actual FluidSynth preview: 20 seconds, peak 0.3614, RMS -25.12 dBFS,
  quiet fraction 0.11; the renderer's audio gates passed. Exported to
  `artifacts/preview.wav` (ignored by Git). Independent FFmpeg analysis measured
  -22.1 LUFS integrated loudness and -8.8 dBFS true peak.
- Actual 120-second segments render in approximately 3.7–4.0 seconds, with no
  queue errors observed while filling the default buffer.
- Installed Liquidsoap 2.1.3 exposed two script compatibility issues: use
  `getenv(...)` instead of `environment.get(...)`, and wrap the crossfade source
  in `mksafe(...)` to satisfy the output's infallibility requirement. The updated
  script passes `liquidsoap --check` and connects to the Icecast MP3 mount.
- All four default Compose services were started on this laptop. The stream is
  bound to `127.0.0.1:8000`; data is in `generative-radio_radio-data`. No `.env`
  was needed: Compose used the documented local defaults.
- Idle snapshot after filling the queue: broadcaster about 146 MiB RAM / 9% CPU;
  Icecast about 5 MiB; composer and renderer about 15 MiB each. This is a single
  snapshot, not a rendering-load or long-term resource benchmark.
- Inspected the installed SoundFont copyright: TimGM6mb.sf2 is GPL-2,
  copyright 2004 Tim Brechbill and 2010 David Bolton. The configured path worked.
- Completed `sh scripts/capture.sh 150`: decoded recording is exactly 150 seconds,
  overall peak -8.87 dBFS, RMS -25.89 dBFS, with no silence events at the script's
  -50 dB / 2-second threshold. Recording and analysis are in
  `artifacts/broadcast.wav` and `artifacts/analysis.log` (ignored by Git).
  Liquidsoap logged fallback-to-generated and generated-to-generated crossfades;
  all four containers were healthy afterward, the buffer replenished to 11 ready
  tracks, and the queue reported no recent errors. This is a short technical
  smoke test; no human listening review was performed.

At this earlier point the 30-minute acceptance recording, human listening review,
fallback/recovery drills, renderer lease recovery and long soak were pending.
See the newer results above. The next snapshot describes the previous laptop.

### Previous laptop snapshot

**Verified:** eight unit tests pass on Python 3.14.5 using
`python3 -m unittest discover -s tests -v`. Python compilation checks also pass.
Tests cover reproducibility, note constraints, queue bounds, exclusive claims,
stale lease recovery, retry limits, dispatch rules, cleanup and seed continuity.

**Not verified:** the complete Docker image, actual FluidSynth renders, SoundFont
package metadata/license, Liquidsoap script compatibility, Icecast output,
crossfades, recovery under real playback, measured resource use, musical quality,
or the 30-minute acceptance broadcast. Treat the current implementation as an
untested integration draft, not a working/production-ready radio station yet.

Docker was available on the first laptop (engine 29.8.1; Compose 5.5.1). The initial
image build reached Debian audio-package downloads and was **cancelled with exit
code 130** when the user decided to move laptops. No Compose station was started;
no stream, audio buffer, or production deployment was created. Build cache/images
are local to the old laptop and are not required for migration.

## Resume on the next laptop

Install Git, Python 3.11+ and Docker with Compose. Authenticate to GitHub, clone
this private repository, and open it in Codex. Read this file and README first.

```sh
python3 -m unittest discover -s tests -v
cp .env.example .env
docker compose build
docker compose up -d
docker compose logs -f renderer broadcaster
```

The intended stream is `http://localhost:8000/radio.mp3`.

Work through these steps before claiming the MVP works:

1. Finish the container build. Debian bookworm currently selects Liquidsoap 2.1.3;
   validate the script against the installed version, especially
   `process.read.lines`, `request.dynamic`, logging settings and environment access.
   Fix any API/type errors. The renderer must create the fallback file before
   checking/starting the broadcaster.
2. Confirm the actual SoundFont path and inspect
   `/usr/share/doc/timgm6mb-soundfont/copyright`; correct attribution if needed.
3. Render a short preview and listen. Check MIDI timing, duration, loudness, peak
   headroom, silence checks and rendering speed. Confirm rendering comfortably
   outpaces real-time playback on the target CPU.
4. Start the full stack. Verify queue replenishment, the Icecast MP3 mount and
   audible crossfades. Measure actual CPU/RAM/disk usage with `docker stats`.
5. Exercise queue exhaustion/fallback and recovery, renderer interruption, and
   Icecast reconnection. Use shorter segments/buffer for a quick failure drill.
6. Run `sh scripts/capture.sh 1800` with host FFmpeg installed. Inspect the recording
   and analysis log; listen for musical coherence, silent gaps and abrupt changes.
7. Record the results and remaining issues here. Only then plan VPS deployment.

## Known design limits and review points

- One composer and one renderer per station. Queue storage must be local disk,
  not NFS. This is not a distributed job system.
- A `served` record means dispatched/prefetched, not confirmed on-air. Broadcaster
  crashes can skip a dispatched segment. Exact playback history is deferred.
- Health checks report problems; Compose does not restart a merely unhealthy
  process. There is no external stream monitor or silence-triggered restart yet.
- Uniform A-minor harmony simplifies transitions but limits musical diversity.
- `.env` changes affect newly queued work; existing jobs retain seed/tempo/duration.
- Check cleanup after failed renders and unusual shutdowns during a longer soak.
- All four containers currently share one image including all audio tools; split
  images later only if disk/maintenance measurements justify it.
- No web control panel, PostgreSQL, multiple genres, FM-1 hardware integration,
  YouTube output, GPU models or public deployment has been implemented.

Suggested continuation prompt:

> Read HANDOFF.md and continue the generative ambient radio MVP. Finish the Docker
> build, fix and validate real FluidSynth/Liquidsoap/Icecast integration, then test
> streaming and recovery. Preserve the agreed CPU-only buffered architecture.
