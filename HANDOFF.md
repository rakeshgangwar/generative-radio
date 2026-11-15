# Generative Radio — current handoff

Updated 15 November 2026 (Asia/Kolkata). Read this snapshot first; detailed history
and measured iterations are in the [product journal](docs/product-journal.md).

## Goal and standing instructions

Build an always-on original ambient station worth returning to. The user asked
for continued creative iteration, PRs for cohesive work and merges after real
current-head CI passes. The release checklist does not exhaust that product goal.
Keep the journal current on main. Routine implementation, validation, committing,
pushing and CI-cleared merges are already authorized.

The repository is public under MIT: https://github.com/rakeshgangwar/generative-radio.
Installed third-party tools/SoundFonts keep their separate licenses. No VPS,
public domain, off-host backup destination or alert destination has been supplied.
Do not invent a target, provision paid infrastructure or publish this machine.

## What is running locally

- Listener: http://localhost:8080; direct MP3: http://localhost:8000/radio.mp3.
- Five healthy Docker services: composer, renderer, broadcaster, Icecast, optional
  Caddy web gateway. Core remains CPU-only, without a generation API or GPU model.
- Music is composed/rendered ahead into a roughly 20-minute buffer, then streamed
  with crossfades. It is not note-by-note real-time model inference.
- Musical memory reconstructs three-to-five-segment chapters from saved seed/ID,
  balancing harmonic paths and developing a motif/register/palette. Ready audio
  remains immutable; skipped queue jobs can skip chapter stages. A served record
  means dispatched/prefetched, not exact on-air history.
- TimGM remains the default sound. Paired TimGM/FluidR3 previews are available in
  the audition artifacts; the asynchronous listening-preference question is open.
- The listener has explicit play/pause, bounded reconnection, native fallback and
  an optional 15/30/60-minute personal sleep timer with a 20-second fade where device
  volume control permits. The timer is page-local and cannot run while frozen.

The musical workers rolled out at 04:54 IST; all 11 ready file hashes were preserved.
Liquidsoap actually crossed into planned job 182 at 05:19:43 IST. The gateway-only
sleep-timer rollout at 06:34 IST left all four music-service IDs/restarts unchanged.

## Delivery and operator tools

PRs #1–#15 merged after current-head CI. Latest code delivery is PR #15, merge
`ddaa4c7`: authenticated public-listener verification now decodes/audits a bounded
MP3 prefix instead of trusting MIME/byte count. Its final code has 121 real-media
and 30 listener tests; CI also passes actual browser and hardened TLS rehearsals.
The initial CI attempt exposed a missing host FFmpeg dependency; the cleared head
includes that dependency. Source checkout is clean on main.

- [Architecture](docs/architecture.md): Python, SQLite WAL, FluidSynth, FFmpeg,
  supervised Liquidsoap, Icecast and optional static Caddy listener.
- [Operations/backup](docs/operations.md): verified create/verify/restore commands,
  exclusive fresh restores, off-host/archive and rollback instructions. Only
  same-host isolated recovery has been exercised; real off-host recovery is open.
- [Production deployment](docs/deployment.md): private random credentials,
  resolved Compose preflight, hardened non-root/read-only profile, persistent TLS,
  startup checks, upgrade/rollback. Package validated locally; no public deployment.
- [Public monitoring](docs/public-monitoring.md): standalone HTTPS+decoded-audio
  check and optional systemd examples. No schedule/notification is installed.
  It needs curl/FFmpeg on the monitoring host and normal or explicit CA trust.
- [Sound auditions](docs/sound-auditions.md): identical-score, attenuation-matched
  comparison CLI, optional isolated FluidR3 image, WAV/MP3/HTML/JSON outputs.
  Fifteen palette/stage cases and three complete chapters were actually compared.

Use isolated worktrees/images/volumes for experiments. Preserve current audio;
roll out only changed roles with explicit source/image and container-ID checks.
Keep existing data and rollback images; no force pushes/admin CI overrides.

## Completed listening-test evidence

The initial 30-minute acceptance, recovery/fallback/reconnect/lease-expiry drills,
one-hour variety baseline and one-hour deployed-watchdog soak passed. The watchdog
hour has 3,600 s audio, no −50 dB silence lasting 2 s, 114 healthy samples, zero restarts/OOM
and stable broadcaster quarter means around 243–245 MiB.

The first attempted two-hour musical rollout recorder ended 143 after about 90 min;
its partial 5,403.38 s is preserved with an unfinalized WAV tail. It is not a completed
two-hour test. Partial analysis: no detected 2 s silence, peak −7.37/RMS −24.62 dBFS,
167 healthy watchdog observations. Old recorder handle 21660 is terminal 143; old
monitor handle 84280 completed exit 0. Never restart or repoll those terminal handles.

The fresh full acceptance completed successfully on 15 November, with capture and
monitor exit 0. Exactly 7,200 s of stereo 44.1 kHz PCM audio has no detected −50 dB
silence lasting 2 s; peak −6.82 and RMS −24.65 dBFS. All 226 watchdog observations
from 06:19:46 through 08:20:46 IST were healthy, with zero recovery/container
restarts or OOM events and unchanged four music-service IDs / Liquidsoap PID 8.
A deliberate web replacement at 06:34 IST shipped the sleep timer; this is not a
full two-hour soak of one web container. Planned ready jobs stayed between 10–11.

Broadcaster memory ranged 246.5–263.5 MiB; quarter averages 249.87, 249.93, 249.39,
249.86 MiB. The post-run SQLite quick_check returned ok, with 11 ready/31 dispatched
jobs, no expired terminal rows, missing referenced audio or temporary work files,
and 907,409,376 data bytes. These observations cover two retention intervals, not
an indefinite leak guarantee or target-host capacity claim.

See the [tracked receipt](docs/evidence/musical-memory-two-hour-20261115.json) for
exact values, source hashes and the intentional web change. Supervisor/capture/
monitor PIDs 456169/456184/456185 are all terminal, verified absent in /proc after
final exit receipts. No acceptance process needs restarting. Other old terminal
handles 24627/77513 and 73227/15955 completed prior baseline/soak runs. CI/preview
handles from merged PRs are terminal.

## Evidence locations

All local recordings, logs, assets and snapshots are Git-ignored:

- `artifacts/watchdog-soak-20261115/summary.json`: completed watchdog hour.
- `artifacts/musical-memory-20261115/`: score benchmarks, paired rehearsals, worker
  origin/rollback tests, preserved-buffer hashes and first actual planned transition.
- `artifacts/musical-memory-rollout-20261115/partial-summary.json`: interrupted run.
- `artifacts/sleep-timer-rollout-20261115/`: source hashes, rollback/before/after IDs
  and actual delivered localhost:8080 browser playback/cancellation.
- `artifacts/sound-auditions-20261115/`: all palette/stage cases and paired 23m05s
  masters at −22.10 LUFS; provenance, CPU/memory trials and portable player.
- `artifacts/musical-memory-acceptance-20261115-004946/`: completed full acceptance.

`/tmp/generative-radio-continuation.json` holds convenient pointers, not proof of
liveness or completion. Prefer files/processes/CI/PR state as authoritative.

## Remaining work

Obtain real listening feedback on repetition, coherence and sound character.
Then deploy to the provided host/domain, verify public DNS/ACME/reboot/capacity,
perform actual off-host recovery and install independent monitoring/alerting at a
chosen destination. Public/physical-device listening remains unverified.

Original architecture conversation reference:
https://chatgpt.com/share/6af89399-506c-83ee-a3cd-66072b4e141b
