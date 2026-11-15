# Sleep timer implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Let a listener settle down with an optional personal stop timer.
**Architecture:** Pure deadline/gain controller plus existing player/app wiring; native select UI.
**Tech Stack:** Existing browser ESmodules, Node tests, Playwright-core1.65.1; no new dependency.
**Spec:** docs/superpowers/specs/2026-11-15-sleep-timer-design.md

## Global Constraints

Off/15/30/60minutes,20second fade, no autoplay/persistence/server changes, deadlines
survive retries but cancel on explicit pause/terminal error/pagehide. Restore
requested volume, support external device volume, native noJS fallback and320px.
Preserve active primary capture21660/monitor84280 and core services. One final
review and CI-cleared PR merge under standing authorization.

## Review Focus

- A delayed or stale timer callback must never pause a later explicit session.
- Reconnect state changes must not extend a timer or re-arm after expiry.
- Manual volume changes during fade must never cause a gain jump above the envelope.
- Unsupported/throwing programmatic volume must still expire safely.
- Paused/idle selection and page lifecycle must not connect to audio accidentally.

### Task1: Deliver the personal listening timer

**Files:** new web/public/sleep-timer.js, web/tests/timer.mjs; modify app.js/index.html/style.css, unit.mjs/browser.mjs, README/journal/HANDOFF.
**Interfaces:** createSleepTimer({now,setTimeout,clearTimeout,onChange,onGain,onExpire}) returns setMinutes(number),setActive(bool),refresh(),dispose(). onChange emits {minutes,remainingSeconds,phase} where phase off/armed/running/expired. onGain(number) scales current requested volume in app; onExpire pauses existing player. Pure controller does not own media or volume.

- [x] Write tests for defaults/invalid/arming, active deadline/duration reset, delayed tick, pause/Off/dispose cancellation/stale callback, retry/noreset and20sec fade; observe missing controller RED.
- [x] Implement controller to GREEN, integrate into existing app without changing player retry policy; add native select/countdown/status and minimal styles. Unit suite passes.
- [x] Add actual-browser regression; first observe missing UI/behavior RED against prior image, then candidate real-audio fade/expiry/retry-cancel/resume GREEN. Verify existing desktop/mobile/native tests/screenshots.
- [x] Update docs/journal with measured evidence/limits, one independent review and regressions for important findings; verify full suites and CI, merge PR, deploy only web and verify core IDs/audio unchanged.

Receipt: PR13 merged2932dc1 after allfour exact-head6a06da6 CI checks. Web-only rollout01:04:38UTC; coreIDs/restarts unchanged; actual8080 browser delivery passed. Fullnew2h acceptance remains pending.
