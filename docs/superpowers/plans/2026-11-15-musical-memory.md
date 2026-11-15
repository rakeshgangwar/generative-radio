# Musical Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Develop coherent themes across segments while reducing repeated openings.
**Architecture:** Stateless bounded planner from saved seed/ID; optional composition/MIDI context, versioned render metadata, rollback flag and explicit previews. No queue migration.
**Tech Stack:** Python standard library, existing FluidSynth/FFmpeg/MIDI/SQLite/Compose.
**Spec:** `docs/superpowers/specs/2026-11-15-musical-memory-design.md`

## Global Constraints

CPU-only, no new runtime asset/model/dependency/schema. Natural A-minor, pitches36–84, velocities<=60, no unsafe same-channel overlaps. Plan work bounded independently of station age. Positions positive integer, origin seed integer. Three-to-five segment chapters, five harmonic paths nonrepeating at consecutive positions, palettes(89,32,4)/(94,32,4)/(89,32,11). `MUSICAL_MEMORY` strictly0/1, default1. Legacy previews/composition and independent fallback retained. No claim of confirmed play history or subjective quality acceptance.

## Review Focus

- Restore/seed-environment changes must not shift existing queued jobs' plans.
- Block boundaries and huge station ages must not introduce repeats/unbounded work.
- Short/long durations and tempo extremes must preserve valid MIDI timing/release.
- Different palettes must pass real headroom/silence/transition checks, not just score tests.
- Rollback flag and original preview path must remain usable and reproducible.

### Task 1: Deliver planned musical continuity

**Files:** Create `radio/arrangement.py`, `tests/test_arrangement.py`; modify `radio/{compose,render,config,__main__}.py`, Compose/.env.example, tests, README/journal/readiness/handoff. Local benchmark/renders remain ignored.
**Interfaces:** `arrangement_for(station_seed:int,position:int)->Arrangement`; `compose(seed,seconds,bpm=60,arrangement=None)`; `midi(notes,seconds,bpm,programs=None)`; `render(config,seed,seconds,stem,*,arrangement=None)`; Config.musical_memory defaultTrue. Preview `--station-seed N --position N`, mutually exclusive with `--seed`.

- [x] Write failing planner tests for bounded deterministic schedules, no-repeat/balanced paths, chapter themes/arcs, safe composed notes and varied starts; observe missing module RED. Record legacy MIDI hash before edits.
- [x] Implement planner and optional composition/MIDI integration to GREEN; verify legacy hash unchanged. Add RED tests for Config/renderer/preview integration, implement and run full Python/JS suites.
- [x] Reproduce256-position score benchmark, render all palettes/stages and crossfade a multi-segment sequence; expected unchanged quality gates and render comfortably faster than playback. Record only measured differences.
- [x] One independent whole-branch review, fix important findings RED→GREEN, update journal with evidence/limits and completed watchdog soak.
- [x] Commit/push PR, merge latest main, require current-head CI before merge. After validation deploy workers only (preserve live data/Icecast/broadcaster), verify new planned renders/replenishment/audio and monitor. Record pending listening/target-deployment gates.

Receipt: PR #11 merged after all four current-head checks. Workers replaced at04:54 IST; eleven ready hashes preserved; first actual planned transition182 at05:19:43 IST. Long rollout recording remains pending.
