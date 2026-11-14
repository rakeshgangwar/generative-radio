# Stream Watchdog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Detect and recover persistent silent/hung Liquidsoap output unattended.

**Architecture:** A non-root supervisor owns Liquidsoap and bounded FFmpeg audio
probes. Atomic health reports replace mount-only health. Restart policy is bounded
and never controls Docker, workers, or Icecast.

**Tech Stack:** Python standard library, installed FFmpeg/Liquidsoap, Compose.

**Spec:** `docs/superpowers/specs/2026-11-15-stream-watchdog-design.md`

## Global Constraints

- Preserve four service roles, current queue, non-root user and CPU-only pipeline.
- No Docker socket, new dependency, public endpoint or schema change.
- Defaults: grace 90 seconds, 12-second audio samples, 30-second probe interval,
  three consecutive failures, three restarts per rolling 900 seconds.
- Handle signals and reap all child/probe processes; bound probe memory and time.
- Keep PR draft until tests and isolated runtime drills pass; do not merge PRs.

## Review Focus

- Quiet fades and partially audible samples must not be classified as silence.
- Short/odd PCM and stalled probes must not masquerade as healthy full samples.
- Icecast outage must not trigger pointless Liquidsoap restart loops.
- Restart budget and shutdown must work while a child is dead or a probe blocked.
- Stale reports, dead PIDs and reports from a prior supervisor must fail health.

### Task 1: Supervise and validate decoded audio

**Files:** Create `radio/watchdog.py`, `tests/test_watchdog.py`; modify
`deploy/stream_health.py`, `compose.yaml`, `.env.example`, `README.md`, `HANDOFF.md`.

**Interfaces:** `Options.load()` validates bounded environment settings;
`assess_pcm(data, seconds)` classifies full mono 8 kHz PCM16 samples;
`RestartPolicy.observe(kind, now)` tracks failures/budget;
`report_is_healthy(path, now=None)` checks freshness and PID liveness;
`Supervisor(options, command=None).run()` owns child/probe lifecycle.

- [ ] Write failing tests for healthy/silent/partial PCM, failure streak reset,
  unavailable-server behavior, rolling budget, stale reports and dead PIDs.
- [ ] Implement bounded probes/policy/report health. Run focused tests; expected
  all pass, including real FFmpeg fixtures and probe cancellation/timeout.
- [ ] Add failing subprocess tests for crash recovery, restart limiting and
  termination; implement supervisor ownership and signal handling. Expected:
  children reaped, no restart loop, no live-station changes.
- [ ] Wire Compose command/health and configuration. Run full suite; expected all
  tests pass. Validate Compose config and script with the built image.
- [ ] Run isolated healthy/silent/hung-child/server-outage drills using shorter
  test thresholds. Expected bounded recovery and decodable post-recovery audio.
- [ ] Request one fresh review; fix important findings using RED→GREEN tests.
- [ ] Preserve the currently running one-hour soak. After it completes and is
  independently validated, update only broadcaster and verify health/audio.
- [ ] Record measured results and update draft PR #3. Leave no speculative
  completion claims: final configuration soak and actual VPS remain required.
