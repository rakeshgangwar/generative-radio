# Musical Variety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Reduce repeated harmony and phrasing while retaining calm ambient music.

**Architecture:** Keep `compose(seed, seconds, bpm) -> list[Note]` and MIDI output
compatible. Select seeded harmonic paths and hold patterns, develop related
melodies with bounded movement, and shape texture over introduction, development,
and release. Preserve the live queue and broadcaster during rollout.

**Tech Stack:** Python standard library, FluidSynth, FFmpeg, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-11-15-musical-variety-design.md`

## Global Constraints

- CPU-only Python/FluidSynth; no new dependencies or instrument changes.
- Deterministic inputs; pitches 36–84; velocities 1–60; A natural minor scale.
- Note timing bounded by duration; support 20–600 seconds and 40–90 BPM.
- Keep queue data and buffered audio; change only newly rendered music.
- Human listening remains the quality gate for reduced repetition.

## Review Focus

- Short/slow tracks must contain positive-duration notes and a melodic phrase.
- Long/fast tracks must remain sparse and fit the requested duration.
- Melody must develop without unbounded leaps or random pitch scattering.
- Repeated pad pitches must not overlap on one MIDI channel and cut each other off.
- New music must render, crossfade, and pass the existing audio gates.

### Task 1: Develop the composer and validate live rollout

**Files:** Modify `radio/compose.py`, `tests/test_radio.py`, `README.md`,
`HANDOFF.md`; retain preview/measurement artifacts under ignored `artifacts/`.

**Interfaces:** Consumes the existing `Config`/render pipeline. Produces the same
`compose(seed: int, seconds: float, bpm: int = 60) -> list[Note]` and
`midi(notes: list[Note], seconds: float, bpm: int) -> bytes` interfaces.

- [x] Write failing behavioral tests for multiple harmonic root paths across
  seeds, phrase/rhythm development, quieter opening/release than development,
  and a bounded melodic step size (maximum seven semitones).
- [x] Extend constraint/reproducibility coverage across 20/120/600 seconds and
  40/60/90 BPM; assert at least one melodic phrase, bounded note density, and no
  overlapping equal pad pitches. Run the suite and verify intended failures.
- [x] Implement curated seeded progressions, bounded hold patterns, related
  phrase variants and density phases. Keep current instruments/MIDI interface.
- [x] Run `python3 -m unittest discover -s tests -v`; expected: all tests pass.
- [x] Render three two-minute seeds in an isolated preview volume, check audio
  gates and render speed, and render their five-second crossfaded sequence.
  Expected: all gates pass and rendering remains comfortably faster than playback.
- [x] Obtain one fresh code review of the final diff; fix important findings
  with failing regression tests and rerun the suite.
- [x] Rebuild the local image and recreate only composer/renderer, leaving
  broadcaster/Icecast and buffered tracks intact. Expected: all services healthy,
  at least one new-version render completes and passes the existing gates.
- [x] Document results, preview paths and buffer delay. Run `git diff --check`;
  expected: no whitespace errors. Preserve the existing integration work as a
  separate commit/PR and publish the feature on `feat/musical-variety`, following
  the user's subsequent instruction to create PRs for completed work.
