# Stock Firefox playback implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repeatable actual Firefox playback acceptance with owned temporary profiles.

**Architecture:** One Python CLI module owns validation, bounded W3C requests, checks, reports and driver cleanup. Reuse watchdog process-group termination; use no extra client dependency.

**Tech Stack:** Python 3.11 standard library, Linux POSIX signals, installed Firefox/GeckoDriver.

**Spec:** docs/superpowers/specs/2026-11-15-firefox-playback-design.md

## Global Constraints

- HTTP loopback root only, no credentials/query/fragment; new private output outside station data.
- Timeout 1..300 seconds, HTTP response <=1 MiB, asset <=256 KiB, JSON report <=32 KiB.
- Fresh owned profile and process group; no existing user session or station mutation.
- Actual five flows required for pass; selected error codes only; cancellation/timeout keep partial evidence.
- No dependencies/downloads; same four required CI job names; one native implementer and one fresh final reviewer, one Important/Critical correction pass, minors deferred.

## Review Focus

- Credentials/nonlocal origins/redirects must not be followed by control clicks.
- Slow or malformed protocol data must fail with bounded, sanitized evidence.
- Deadline/cancellation must reap the owned driver and its process group.
- Existing output/station data must remain untouched; profiles removed after failure too.
- An early failed flow must never become a success receipt.

### Task 1: Firefox acceptance tool and delivery

**Files:** Create radio/firefox_smoke.py, tests/test_firefox_smoke.py, docs/firefox-check.md; update .github/workflows/ci.yml, docs/product-journal.md and HANDOFF.md.

**Interfaces:** `Options(driver: Path, firefox: Path, output: Path, url: str, timeout: float)` validates before I/O; `run(options: Options) -> int` owns the whole finite main-thread operation; module CLI exposes those options.

- [ ] Write tests for invalid origins/options, existing/data output preservation, actual owned-child protocol failure/oversize/deadline/cancellation, sanitized error canaries, profile cleanup and no false pass from partial work. Fake WebDriver is an external protocol fixture, not a substitute for actual playback acceptance.
- [ ] Run `python -m unittest discover -s tests -p test_firefox_smoke.py -v`; expect missing module RED.
- [ ] Implement the bounded client/ownership and five real checks; run focused tests, expect green.
- [ ] Run actual installed Firefox and verified GeckoDriver against the live local station in a private profile; expect five actual successful checks, closed driver port and unchanged station identities/state. Preserve result/source provenance. No runtime service deployment.
- [ ] Wire actual Firefox CI step using installed binaries; document setup/limits and actual proof. Commit cohesive change.
- [ ] Run whole suite with real audio tools via read-only source mount in existing dependency image; expect all green with explicit live opt-in skipped; run listener tests. Use task-done for final whole-task gate.
- [ ] One fresh final whole-branch review, one blocking TDD correction pass, no rereview; scoped PR then actual latest final-head/current-base all-four CI plus new Firefox step before authorized merge.
