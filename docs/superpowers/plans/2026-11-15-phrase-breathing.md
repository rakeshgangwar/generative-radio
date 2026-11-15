# Melodic phrase breathing implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Compare a melody that leaves periodic phrase-ending rests with the current continuous middle stages.

**Architecture:** Version-2 arrangement metadata chooses a chapter-shared phrase length. Compose skips its last bar and clips preceding melody tails; sustained harmony and existing recovery/buffering remain intact. Old plans and unplanned composition retain exact output.

**Tech Stack:** Existing Python, FluidSynth, FFmpeg, Liquidsoap and Docker; no new package or asset.

**Spec:** `docs/superpowers/specs/2026-11-15-phrase-breathing-design.md`

## Global constraints

- Append `phrase_bars: int = 0` without breaking positional arguments; default constructor version stays 1.
- New planner version 2 uses chapter-shared integer phrase lengths {6, 8, 10}; preserve all existing scheduling choices.
- Every phrase's final bar has no new melody attack or held MIDI note; note-off margin is 0.1 beat; pads/bass continue.
- Legacy/unplanned and explicit version-1 MIDI are byte-identical; unsupported versions/invalid version-2 lengths fail clearly.
- Keep TimGM, immutable ready audio and current live services; no public deployment or listening acceptance claim.

## Review focus

- Huge or out-of-order positions must remain bounded and deterministic: Task 1 planner tests.
- A 20-second clip may not contain a whole phrase: Task 1 duration/tempo matrix.
- A long melody release could invade the rest: Task 1 interval intersection assertions.
- Constructor positional callers and explicit version-1 plans must keep output: Task 1 compatibility hashes.
- Sustained harmony must keep quiet phrases audible: Task 2 real-media matrix and sequence gates.

### Task 1: Versioned phrase scheduling and composition

**Files:** Modify `radio/arrangement.py`, `radio/compose.py`; add `tests/test_phrase_breathing.py`.

**Interfaces:** Existing `arrangement_for(station_seed: int, position: int) -> Arrangement`, `compose(seed, seconds, bpm=60, arrangement=None) -> list[Note]` and `midi(...) -> bytes` stay callable. Arrangement appends `phrase_bars`; new plans report version 2.

- [x] Add failing planner tests: lengths in {6,8,10}, chapter sharing/balanced blocks, huge/out-of-order determinism, existing non-phrasing plan fields unchanged against version-1 fixtures.
- [x] Add failing compose tests: for each complete phrase interval, no channel-2 note intersects its final bar (including 0.1 beat release); pads overlap the rest. Cover all stages, BPM 40/60/90 and seconds 20/120/600; require positive bounded finite notes and existing pitch/velocity safety.
- [x] Pin old explicit-plan MIDI using preserved baseline SHA-256s, and old unplanned MIDI from the unchanged base; invalid version-2 lengths (0, negative, bool, float, unknown length) and unsupported versions raise ValueError.
- [x] Run `python3 -m unittest discover -s tests -p 'test_phrase_breathing.py' -v`; confirm behavioral failures before implementation.
- [x] Append metadata, choose new chapter label with existing scheduler, and implement last-bar omission/release clipping only for validated version-2 plans. Preserve version-1 and unplanned code paths.
- [x] Run focused tests and full Python suite; investigate actual failures. Commit passing code/tests.

### Task 2: Paired audio, measured journal and delivery

**Files:** Update `docs/product-journal.md`, `HANDOFF.md`, this plan and relevant composition docs. Keep media/raw measurement artifacts ignored.

**Interfaces:** Existing renderer/audition metadata must carry phrase_bars/version without new CLI/config. Existing quality gates remain authoritative.

- [x] Build isolated candidate image; run full real-media Python and listener unit suites. Use isolated data, never live volume writes.
- [x] Render every palette/stage case and a 12-position 120-second sequence; compare identical seeds against current image. Existing duration, audibility, peak/headroom and no-silence gates must pass. Export paired MP3s, report source/version provenance and render/resource measurements.
- [x] Recompute the 256-position rest/density comparison; confirm complete phrase rests in middle stages while notes remain present. Record results without claiming subjective improvement.
- [ ] Record concrete previews and measured decisions in journal; preserve current TimGM. One independent final review; fix/reproduce Important/Critical findings, then run required full checks.
- [ ] Open scoped PR. Require all four real checks on the actual final head and current base before merge. After merge, any worker-only rollout must preserve ready hashes and other service identities, retain rollback image, and verify actual decoded audio; document delivered vs merely compared status.
