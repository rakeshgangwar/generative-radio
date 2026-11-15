# Sound auditions implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Produce reproducible, matched-level listening comparisons of sound libraries.
**Architecture:** Isolated host/container CLI reuses existing renderer, verifies score identity, stitches and attenuates sequences, writes atomic manifest and static HTML.
**Tech Stack:** stdlib Python, existing FluidSynth/FFmpeg; optional FluidR3 lab image only.
**Spec:** docs/superpowers/specs/2026-11-15-sound-auditions-design.md

## Global Constraints

No live services/data/defaults changed; no font or audio binaries committed.
2–4 labeled fonts,1–24 positions,20–1800sec/clip and<=1800 nominal sec/font,40–90BPM.
Fresh exclusive output; caught failures recorded.5sec linear joins, MIDI identity,
attenuation-only shared level<=-22LUFS with-3dBTP headroom, final0.2LU tolerance.
Preserve supervisor456169/capture456184/monitor456185 and its immutable script.
One final review and current-head CI-cleared PR under standing authorization.

## Review Focus

- Existing output/symlinks and invalid inputs must not clobber station data.
- NaN/infinite loudness or missing MIDI identity must fail the comparison.
- Font mutation and partial tool failures must never publish complete status.
- Shared level must never boost a variant or hide a peak violation.
- HTML/CLI labels and subprocess arguments must not permit injection or remote assets.

### Task1: Deliver the listening bench and real comparison

**Files:** create radio/audition.py, tests/test_audition.py, scripts/Dockerfile.audition, docs/sound-auditions.md; modify README/journal/HANDOFF/plan receipts.
**Interfaces:** validate_inputs(fonts,positions,seconds,bpm,station_seed); shared_level(measurements); audition(output,fonts,station_seed=42,positions=(1,2,3),seconds=120,bpm=60). CLI standalone module, no Store.

- [x] Write tests for validation/refusal, finite shared attenuation/peak constraints and safe report output; observe RED.
- [x] Implement orchestration/report/measurement helpers and CLI to GREEN. Add real-media identity test2x2clips20sec with expected35sec master; verify same MIDI and matched levels.
- [x] Build isolated optional lab; verify installed FluidR3 copyright, compare all palettes/stages and a longer identical-score sequence, record time/resource/quality results and listening files.
- [ ] Update operator docs/journal with actual results and shipped timer receipt; one final independent review, important fix regressions, full suites/current-head CI then PR merge. Leave live music unchanged pending listening evidence.
