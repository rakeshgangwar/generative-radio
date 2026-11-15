# Native Listener Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; one final whole-branch reviewer.

**Goal:** Keep keyboard focus visible during late enhancement and explain native-mode limitations/reload.

**Architecture:** Add conditional focus transfer to the existing successful handoff; update ordinary HTML help. Preserve all player controllers and native ownership guards.

**Tech Stack:** Existing static HTML/JS, Node tests, actual Chromium/Firefox, Docker/Caddy.

**Spec:** docs/superpowers/specs/2026-11-15-native-listener-polish-design.md

## Global Constraints

- Static stack, no dependencies, no autoplay or pre-click stream request.
- Never replace started native playback; preserve unrelated keyboard focus.
- Keep old HTML/new-script compatibility and enhanced timer/retry/volume behavior.
- No music/core role change; only verified web-only rollout after real PR CI.

## Review Focus

- Late handoff must move focus only when it is inside the native fallback.
- Already playing, paused or pending native sessions keep focus and source.
- Missing native markup in legacy HTML must not crash or steal focus.
- Native-mode help must be truthful, readable at320px, and hidden after enhancement.
- No pre-click audio or extra connection from focus transfer/reload messaging.

### Task 1: Deliver native-mode usability polish

**Files:** Modify web/public/app.js and index.html; extend web/tests/native-fallback-browser.mjs; update source-linked evidence, HANDOFF, journal/readiness and the completed PR28 delivery receipt.
**Interfaces:** Existing player APIs unchanged. Inspect fallback.contains(document.activeElement) only in the successful unstarted-native handoff; after revealing controls call existing play button.focus({preventScroll:true}) when appropriate. Guard absent legacy fallback.

- [x] Add actual delayed-module test for native-focus handoff and keyboard realplay;
  add unrelated-link focus preservation and existing-session focus assertions.
- [x] Observe meaningful RED on deployed-base candidate before changing production.
- [x] Implement conditional visible focus handoff and concise native help; run Node
  and focused actual browser tests to GREEN, preserving zero pre-play requests.
- [x] Run full browser acceptance and actual Firefox; inspect320px help/focus visual;
  record exact asset/proof hashes and truthful scope. No core service changes.
- [x] One fresh final review, one Important/Critical correction pass with RED→GREEN;
  Minor ledger costs; run final relevant checks and publish scoped PR.
- [ ] Require all four latest final-head/current-base CI jobs and actualFirefoxstep
  success, merge only on clearance. Verify measured web-only rollout and journal.
