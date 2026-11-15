# Listener Volume Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; one fresh final whole-branch review.

**Goal:** Restore a listener's chosen full-player volume across refresh while preserving manual play and page-local timers.

**Architecture:** A small optional localStorage boundary in existing app.js: validate/read before requestedVolume, save only explicit unfaded range input, catch storage failures. No live cross-tab synchronization or native-player takeover.

**Tech Stack:** Existing static HTML/JS, native Node tests, actual Chromium/Firefox, existing Docker/Caddy.

**Spec:** docs/superpowers/specs/2026-11-15-listener-volume-memory-design.md

## Global Constraints

- Key generative-radio.volume.v1; canonical integer strings `0` to `100`, at most three characters.
- Invalid/absent/denied reads keep 65%; no write on page load and no raw preference/error logging.
- Save only explicit unfaded range choices; storage failures must not block listening.
- No saved play intent/timer/account/history; manual play and timer reset remain.
- No live cross-tab volume jumps; started native sessions and device-button fallback remain.
- No new dependencies/module/server/settings UI; retain eight served-asset identity.
- Explicitly isolated candidate labels; no core/music change; annotate any later web maintenance in active six-hour observation.

## Review Focus

- Invalid/oversized/noncanonical stored data must never become volume or displayed text.
- Getter/read/write failures must leave full-player controls usable and no autoplay.
- Fade/cancel/expiry/reload must save requested percent rather than attenuated gain.
- Another tab, native session or unsupported hardware must not get a surprise volume change.
- Restored0/max/readout/ARIA must agree while timer/play intent remain reset.

### Task 1: Deliver browser-local volume memory

**Files:** Modify web/public/app.js; add web/tests/volume-browser.mjs and wire into browser.mjs; extend existing hardware-volume fixture for a saved preference; update README, HANDOFF, journal/readiness and source-linked evidence.
**Interfaces:** Existing player/timer/context APIs unchanged. Read key after native guard and before requestedVolume initialization. Accept only typeof string, length<=3, integer `0` to `100`, String(number)===saved. Save validated chosen percent only from explicit input; initial setVolume and onGain never write. All storage access wrapped in try/catch.

- [x] Write actual browser restoration/no-autoplay/timer-reset regression; observe meaningful RED on current base before production changes.
- [x] Add boundary cases for zero/quiet/maximum, invalid values, denied getter/quota write, fade preference, cross-tab noninterference and saved-data hardware fallback.
- [x] Implement optional validated read/write boundary to GREEN; run Node and focused actual browser acceptance.
- [x] Run full browser suite and stock/native Firefox; inspect 320px/readout; record exact asset/proof hashes. No core changes.
- [x] One fresh whole-branch review; one Important/Critical RED→GREEN correction pass if needed, Minor ledger costs, no rereview. Publish scoped PR.
- [ ] Require four actual latest final-head/current-base CI jobs with actual Firefox success; guarded merge and measured web-only rollout. Annotate maintenance in running observation; publish truthful delivery/current direction later.
