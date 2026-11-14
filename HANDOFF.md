# Generative Radio — laptop handoff

Updated: 14 November 2026 (Asia/Kolkata).

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
