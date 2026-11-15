# Resting Profile Audition Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans; native inline execution is already chosen. One fresh whole-branch review.

**Goal:** Make the offline resting comparison reproducible without changing live music.
**Architecture:** New profile_audition module composes two declared profiles and uses existing render/level helpers. Add an escaped optional description to the existing comparison HTML helper; retain its default output.
**Tech Stack:** Python stdlib, FluidSynth, FFmpeg, existing static audition page and browser harness.
**Spec:** docs/superpowers/specs/2026-11-15-resting-profile-audition-design.md

## Global Constraints

- Current 60 BPM; resting 52 BPM, profile 0, programs (89, 32, 4); no default composer changes.
- At most 24 unique positive positions; integer 20–1800 seconds, at most 1800 nominal seconds per variant; integer seed, not boolean.
- New output outside station data; no SQLite, new dependency, station role change or automatic adoption.
- Intended/rendered MIDI match; one unchanged font; attenuation-only levels and exact duration; no completed HTML on failure.
- One final review and actual four-job current-head/current-base CI including Firefox before merge.

## Review Focus

- Broken/symlink station marker or existing output must be refused before engine work.
- Reference MIDI must match existing composer; resting renderer must use52 BPM and declared programs.
- Font or score drift must not be represented as a matched comparison.
- Nominal-duration bounds must not be described as a total wall-clock deadline.
- Failed/cancelled renders must not publish a completed listening page; native mode requires manual mutual exclusion.

### Task 1: Deliver the reproducible offline comparison

**Files:** Create radio/profile_audition.py and tests/test_profile_audition.py; modify radio/audition.py HTML helper, docs/resting-profile-experiment.md, README, HANDOFF, journal; add source-linked evidence.
**Interfaces:** score_for(profile,station_seed,position,seconds) returns (Arrangement,list[Note],bpm). audition_profile(output,soundfont,station_seed=42,positions=tuple(range(1,13)),seconds=120) returns report. audition.report_html(report,*,description=None) preserves existing default copy and escapes a supplied description.

- [x] Write CLI --help acceptance; run `python -m unittest discover -s tests -p test_profile_audition.py -v`, expect an assertion failure because the command is absent.
- [x] Add tests for reference parity, candidate score/tempo/palette and256-position reduction, invalid output/inputs/markers, engine and MIDI/font failure boundaries, HTML escaping and actual paired rendering without SQLite.
- [x] Implement from the spec and public helpers; do not adapt the throwaway prototype. Run targeted tests to GREEN.
- [x] Run full Python tests with real audio tools and Node tests; inspect every result. Render real three-chapter CLI output, verify fingerprints/duration/levels and actual browser playback/seek/native/narrow behavior on a separate preview.
- [x] Update truthful docs/evidence; commit and record the locally verified task.

## Branch delivery

- [x] Run one fresh whole-branch review and one Important/Critical RED→GREEN fix pass if needed, record Minor costs, no rereview.
- [x] Publish scoped PR; require actual latest final-head/current-base four-job CI including Firefox before guarded merge. No live-role redeploy for an offline tool.

Delivered as PR #35 (`e384215`) after all four jobs passed on `0f8c44e`, run 43748701299, including actual stock Firefox. The separate local lab image is built and source-checked; no live role rollout. Direct-SIGTERM reporting remains a deferred Minor as recorded in the delivery receipt.
