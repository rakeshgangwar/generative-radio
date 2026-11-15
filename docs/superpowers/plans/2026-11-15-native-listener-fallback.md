# Native Listener Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; one final whole-branch reviewer.

**Goal:** Keep radio playable when optional scripts fail, preserving native listening across delayed script delivery.

**Architecture:** Independent native HTML audio fallback plus existing enhanced player. Enhance only an unstarted native session, with source release and control visibility committed after initialization succeeds.

**Tech Stack:** Static HTML/CSS/ES modules, Node tests, Playwright-core Chromium, installed Firefox/GeckoDriver, existing Docker/Caddy.

**Spec:** docs/superpowers/specs/2026-11-15-native-listener-fallback-design.md

## Global Constraints

- Keep static HTML/CSS/JavaScript, existing Caddy proxy and local-only deployment.
- No autoplay or MP3 request before explicit user playback in either mode.
- Never stop/reload/replace an already started native session on late enhancement.
- Exactly one usable player; enhanced mode releases the unused native source.
- Keep enhanced recovery, timer, volume, chapter context and pause/source release.
- Native playback must work when app.js fails, an imported module fails, or JS is off.
- No external assets, accounts, storage or new runtime dependencies.
- No station role replacement until verified web-only rollout with identity receipts.

## Review Focus

- Late script delivery while native play is pending must not create a second stream.
- Previously played then paused native audio must retain its controls and source.
- Initialization exceptions must leave fallback available; previous HTML with new scripts must still initialize usable enhanced controls.
- Module failures and JS-off playback must remain keyboard accessible at 320px.
- Normal enhancement must not leave an unused hidden connection or alter pause/retry.

### Task 1: Deliver progressive native listening

**Files:** Modify web/public/index.html and app.js; update presentation tests; add
web/tests/native-fallback-browser.mjs imported by web/tests/browser.mjs. Document
README.md, HANDOFF.md, docs/product-journal.md and a source-linked evidence receipt.
**Interfaces:** Existing createPlayer/createSleepTimer/createBroadcastContext stay
unchanged. Add visible #native-fallback containing #native-stream; keep #stream
source-free. App initialization returns without enhancement if native is unpaused
or native.played.length>0. Commit fallback release/hide only at successful end.

- [x] Write failing presentation and actual-browser tests for blocked app/import,
  delayed native play/pause/pending-play, initialization failure and normal handoff.
- [x] Run RED on current main-derived source; distinguish legitimate behavior failure
  from missing fixture/driver/setup. Save bounded raw evidence outside station data.
- [x] Implement native markup and guarded app initialization to GREEN. Preserve all
  enhanced handlers and place visibility/source handoff after successful setup.
- [x] Run all Node tests and focused actual Chromium acceptance. Check no-JS real
  native playback, normal no-preload/one-source behavior, keyboard and 320px layout.
- [x] Run existing complete browser suite and stock Firefox check against isolated
  candidate web assets, then actual Firefox native controls. Never replace live core.
- [x] Document measured source/assets, candidate/local-only status, limitations and
  PR27 delivery receipt. One final fresh review; Important/Critical one RED→GREEN
  correction pass; Minor defer. Run relevant final checks after corrections.
- [ ] Open scoped PR, require four actual latest final-head/current-base CI jobs
  including Firefox step success, merge only after clearance. Verify web-only
  rollout separately with preserved core identities and decoded stream evidence.
