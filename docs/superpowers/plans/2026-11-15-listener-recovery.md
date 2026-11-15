# Listener maintenance recovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Recover automatically after a thirty-second stream interruption while keeping recovery finite and cancellation reliable.

**Architecture:** Extend the existing fixed player schedule; preserve its single owned retry/deadline/stability timers and generation guards. No new services or backend changes.

**Tech Stack:** Plain JS, Node deterministic tests, Chromium/Playwright, existing Caddy and CI.

**Spec:** docs/superpowers/specs/2026-11-15-listener-recovery-design.md

## Global constraints

- Fixed backoffs1/3/8/15/15/15s; six retries,15s connection deadline,30s stable reset. Max57s backoff+105s hanging connections=162s finite exhaustion.
- No autoplay, unbounded polling, backend/audio changes, extra settings or independent timer ownership. Pause/disposal/sleep expiry cancel recovery. Permission denial needs a new gesture.
- Preserve metadata, volume, timer and native fallback. Develop in isolated worktree/image/loopback preview; do not interrupt main music to inject test failures.
- Honest chapter rollout evidence: all11ready hashes/fallback preserved,workers unchanged,fivehealthy,10s decoded; prior maintenance observer timed out, not an automatic recovery success.

## Review focus

- Recovery from real HTTP failures must resume after30s without second user gesture; permission restrictions still fail honestly.
- Expanded retry schedule must stay finite for hanging connections and short playing/drop loops; pause/dispose/timer expiry must cancel even late retries.
- Actual browser fault test must remain isolated to its context, log request/state evidence on failure, and prove real audio/timer behavior after recovery.
- Source-vs-live state, old failed maintenance observer and new controlled outage evidence must not be conflated.

### Task 1: Extend and verify bounded recovery

**Files:** Modify web/public/player.js,web/tests/player.test.mjs,web/tests/browser.mjs; create web/tests/recovery-browser.mjs; update HANDOFF.md,docs/product-journal.md,README.md and docs/evidence/listener-recovery-20261115.json.

**Interfaces:** createPlayer unchanged; existing fixture clock exposes currenttime only to tests; browserhelper imported by fullbrowser runner. Metadata/timer modules unchanged.

- [x] Add deterministic30s-outage acceptance and actual Chromium30s failed-request acceptance with diagnostic finally receipt; run both RED on old policy. Expected: error before source returns, specifically at15s browser observation.
- [x] Extend fixed schedule; update finite-exhaustion/short-drop-loop expectations. Run full listener suite. Expected:30s outage recovers by45s, permission/pause/disposal/stable reset unchanged, all tests pass, all-hung exhaustion finite by180s.
- [x] Build uniquely tagged isolated web candidate; expose only loopback18088, read-only/no private data mounts, proxy existing station read-only. Run full actualbrowser suite and inspect current screenshots. Expected:11scenarios pass including failed30s requests then realMP3 advance with timerstillarmed. Remove only temporary gateway afterward.
- [x] Record existing chapter-rollout and recovery proof separately, update journal/handoff, commit validated feature. Expected: mainrole IDs remain unchanged during recovery development.

## Delivery gates

- [ ] One fresh independent final review; Important/Critical findings reproduced/fixed in one pass; full green validation.
- [ ] Scoped PR, allfour actual latest final-head/current-base CI checks, authorized merge and primaryfastforward; later web-only rollout preserves four music roles.
