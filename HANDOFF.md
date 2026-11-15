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
- Version-2 source plans add chapter-shared 6/8/10-bar melodic phrases with a
  one-bar score/MIDI rest over sustained harmony. Workers rolled out at 08:53 IST;
  version-2 job 306 is actually ready with phrase_bars=10. Previously queued version-1
  WAVs still play first; actual broadcaster transition is pending. SoundFont release/
  reverb can ring through MIDI rests. Explicit version-1/unplanned MIDI is unchanged.
- TimGM remains the default sound. Paired TimGM/FluidR3 previews are available in
  the audition artifacts; the asynchronous listening-preference question is open.
- The listener has explicit play/pause, bounded reconnection, native fallback and
  an optional 15/30/60-minute personal sleep timer with a 20-second fade where device
  volume control permits. The timer is page-local and cannot run while frozen.

The musical workers rolled out at 04:54 IST; all 11 ready file hashes were preserved.
Liquidsoap actually crossed into planned job 182 at 05:19:43 IST. The gateway-only
sleep-timer rollout at 06:34 IST left all four music-service IDs/restarts unchanged.

## Delivery and operator tools

PRs #1–#17 merged after current-head CI. PR #16 (`a00557d`) records the completed
two-hour acceptance and replaces the stale first-laptop handoff. Latest source
is PR #17 (`d82bd17`), version-2 melodic phrasing. All four checks passed on final
head `84c9d33`, run 43671299403. The candidate image matches all 17 tracked runtime
source files. Composer/renderer now use it; broadcaster/Icecast/web stayed unchanged.
The runtime feature branch has 127 real-media Python and 30 listener tests passing.
Source checkout is clean on main. Public decoded HTTPS monitoring remains an
operator command, without an installed independent schedule or alert target.

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

## Current phrase rollout and live acceptance

PR #17's successful rollout at 03:23:52 UTC preserved all 11 ready WAV hashes and
broadcaster/Icecast/web IDs. Rollback is `generative-radio:before-phrase-breathing`.
An initial snapshot attempt stopped the workers, then failed before new code ran.
The original workers were explicitly restored; the second attempt replaced them.
This extra stop/start is intentional maintenance, not an absent event inferred
from Docker restart_count=0. Raw monitoring observed one exited-worker sample
and one replacement-composer starting sample. Decoded source health stayed good.

The error was reproduced on isolated data: a closed WAL database without sidecars
cannot initialize them on a fully read-only mount. The successful rollout used
SQL mode=ro through the existing data mount, where SQLite may initialize sidecars.
The shipped backup CLI reproduces this same stopped-source edge case on a read-only
mount; an explicit safe offline-backup path is the next operational fix. Do not
silently use immutable=1 to bypass WAL recovery.

The 30-minute live capture started 03:21:05 UTC /08:51 IST and remains in progress:

- `artifacts/phrase-breathing-live-20261115-032105/run.json` is the exit receipt.
- Supervisor PID 596862, capture 596863, monitor 596864; verify actual matching
  /proc commands before treating them as live. Never restart on observation timeout.
- Capture is 1,800 s, monitor 1,860 s, supervisor safety bound 1,980 s. Expected
  recording finish around 03:51 UTC; monitor around 03:52 UTC.
- Existing version-1 queue plays through naturally. Job 306 is ready, not proof
  that a listener heard it. Match actual broadcaster transitions before claiming it.
- The full completed two-hour result above belongs to the earlier version-1 run.
  New rollout evidence does not relabel that as a version-2 soak.

[Rollout receipt](docs/evidence/phrase-worker-rollout-20261115.json) records image/
container identities, maintenance and the active test. Public deployment, physical
mobile devices, actual off-host recovery and subjective listening stay open.

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
- `artifacts/phrase-breathing-rollout-20261115/`: aborted/successful attempts, queued
  file hashes, source/image proof and isolated WAL/backup regressions.
- `artifacts/phrase-breathing-live-20261115-032105/`: active new live capture/vitals.

`/tmp/generative-radio-continuation.json` holds convenient pointers, not proof of
liveness or completion. Prefer files/processes/CI/PR state as authoritative.

## Remaining work

Complete the current capture and actual version-2 transition evidence; fix the
stopped-source backup edge case. Obtain real listening feedback on repetition,
coherence and sound character.
Then deploy to the provided host/domain, verify public DNS/ACME/reboot/capacity,
perform actual off-host recovery and install independent monitoring/alerting at a
chosen destination. Public/physical-device listening remains unverified.

Original architecture conversation reference:
https://chatgpt.com/share/6af89399-506c-83ee-a3cd-66072b4e141b
