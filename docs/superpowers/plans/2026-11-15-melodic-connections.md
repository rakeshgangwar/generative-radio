# Melodic connections audition implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** Produce an honest matched long audition of occasional melodic connections while preserving the on-air version2 station.

**Architecture:** A pure bounded note-list transform plus an offline same-font bench; extract existing rendering without changing worker defaults. Reuse established measurement/stitching/level checks.

**Tech Stack:** Python/stdlb, FluidSynth/FFmpeg, existing MIDI/render/arrangement helpers, static HTML/Chromium.

**Spec:** docs/superpowers/specs/2026-11-15-melodic-connections-design.md

## Global constraints

- Audition-only; no live config/images/queue/SQLite changes. Compose/midi/arrangement defaults unchanged; golden legacy MIDI bytes preserved.
- <=4096 valid notes,seconds20..1800,BPM40..90,v2phrase6/8/10/profile0..2. Preserve starts/pitches/velocities/channels; profile0 unchanged.
- Stepwise intermediate diatonic pitch only for3/4-semitone anchors. Add at target-.75beat for.5beat, velocitytarget-5 minimum1, clear.1beat gaps (predecessor may retain at least max(.5beat,half original duration)), middle20..80%, weak beat only. Same >=3-class held-pad field containing both anchors; no rests/cross-phrase additions; one per phrase, profile1 even phrases.
- Exclusive output outside station data; same font/seed/plan, no font changes, <=24unique positions/1800nominal seconds. Existing5s crossfades and attenuation-only level checks:duration within.1s, shared loudness within.2LUFS, truepeak<=-2.9dBFS, gain<=0.
- Separate score/engineering evidence from subjective musical acceptance; no default adoption without the audition judgment.

## Review focus

- Added notes must not violate original attack/pitch identity and bounded predecessor tails, explicit rests, held-note gaps, pitch/velocity/channel bounds or harmonic/phrase boundaries.
- Renderer extraction must preserve legacy MIDI bytes, render flags, atomic publication and failure cleanup; normal workers must not invoke the transform.
- Offline output refusal/validation must precede side effects, never touch live database/data and never mislabel partial work as complete or unchanged scores as improved.
- Same-font/source hashes, duration/loudness matching and actual additions must support the listening comparison; no claim of perceptual improvement from score metrics.

### Task 1: Pure bounded melodic connector

**Files:** Create radio/melodic_connections.py, tests/test_melodic_connections.py; capture tests/fixtures/melody-baseline-midi.json from unchanged merged main.

**Interfaces:** connect_melody(notes,seconds,bpm,arrangement)->list[Note]; original anchors retained, bounded predecessor-tail copies allowed, additions appended; only trusted score input from compose in later bench.

- [x] Capture baseline MIDI hashes from main for unplanned/v1/v2 cases before renderer edits. Write pure connector tests and run RED. Expected: missing connector; synthetic clear-gap fixture explicitly insertsF betweenE/G over stableC field.
- [x] Implement exact spec validation/selection; run focused tests and bounded score matrix. Expected: at least one real-score addition, all originals preserved, no overlaps/rest breaches, deterministic results, no additions for profile0 or ineligible gaps.
- [x] Commit verified helper and complete task with python3 -m unittest discover -s tests -p test_melodic_connections.py -v.

### Task 2: Same-font offline audition and measured pair

**Files:** Modify radio/render.py; create radio/melody_audition.py,tests/test_melody_audition.py,docs/melodic-connections.md; update docs/product-journal.md,HANDOFF.md and docs/evidence/melodic-connections-20261115.json.

**Interfaces:** render_notes(config,notes,seconds,stem,*,arrangement=None) preserves existing publication/analysis/cleanup; render default delegates without transform. CLI/report wraps base and connected note lists, using existing audition helpers.

- [ ] Write renderer/bench tests RED: historical MIDI hashes, exact same-font base/candidate scores, bounds/exclusive/data guard/noDB, failed report, HTML escaping/controls, real short render and levels. Expected: missing helper/bench until implemented.
- [ ] Extract render_notes and implement offline CLI/report; run full real-media and46listener suites in uniquely tagged candidate core. Expected: allgreen and unchanged worker behavior.
- [ ] Render12positions120s matched pair with currentTimGM using no live mounts/network. Verify23m05s duration, matching level/peaks, real additions and no>=2s silent run at-50dB. Browser-test report explicit playback/one-at-time/narrow layout, inspect screenshots. Expected: measurable honest comparison, no quality verdict.
- [ ] Record source-vs-live evidence, journal and runbook; commit and complete with full real-media test command from actual candidate image. Existing main roles must remain unchanged.

## Delivery gates

- [ ] One fresh whole-branch review; one Critical/Important RED/GREEN fix pass, minors deferred; all required checks actualsuccess.
- [ ] Scoped PR after docs23merge/rebase ifneeded; real latest final-head/current-base CI before authorized merge. No station rollout for offline audition.
