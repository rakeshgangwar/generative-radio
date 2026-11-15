# Station observer implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repeatable bounded host-side station vitals receipts without disturbing playback.

**Architecture:** One collector module with capped owned subprocess reads and strict output projection; one recorder module owns private bounded files and CLI scheduling.

**Tech Stack:** Python 3.11 standard library, Linux procfs, Docker CLI.

**Spec:** docs/superpowers/specs/2026-11-15-station-observer-design.md

## Global Constraints

- Existing Python 3.11+ and Docker CLI, no added dependencies or deployed services.
- Duration zero or 1..86400; interval 1..600; max-samples 1..4096.
- Command deadline 5 seconds; stdout at most 64 KiB; inventory at most 16.
- Fixed ring slots, atomic JSON, fresh 0700 output outside radio.sqlite ancestors.
- No Docker mutations/exec, database queries, environment persistence or alerting.
- One native implementation and one fresh final reviewer; one blocking-fix pass, minors deferred.

## Review Focus

- Missing Docker access or malformed data must yield unknown, never healthy.
- Cancelled/hung commands must terminate only owned client process groups.
- Arbitrary Docker diagnostics and watchdog detail must not leak into receipts.
- Rotation must preserve bounded files and cumulative counts through cancelled runs.
- Remote Docker context must not mislabel observer-host RAM as station-host RAM.

### Task 1: Complete recorder

**Files:** Create radio/station_vitals.py (collection), radio/observer.py (recording/CLI), tests/test_observer.py, docs/station-observer.md; update README.md, HANDOFF.md and docs/product-journal.md.

**Interfaces:** collector `collect(project: str, expect_web: bool, stop: threading.Event) -> dict`; runner `record(output: Path, project: str, expect_web: bool, duration: float, interval: float, max_samples: int, stop: threading.Event) -> int`. No other task consumes these.

- [ ] Write failing tests for actual selection/projection with secret canaries, missing/duplicate services, malformed stats, watchdog freshness/tar bounds; real subprocess timeout/output cap/cancellation; ring retention/cumulative failure state/fresh-output/dataguard and bounded cancellation.
- [ ] Run `python -m unittest discover -s tests -p test_observer.py -v`; expected missing module RED.
- [ ] Implement collector and recorder from the spec, preserving only allowlisted measurements and fixed error codes.
- [ ] Run focused tests; expected all pass. Run `python -m unittest discover -s tests -v`; expected green with explicitly reported media skips on host, then full real-media image suite before delivery.
- [ ] Run actual main-host one-shot and short recording; compare service identities and health before/after, report sanitization and bounded retention. Expected all-healthy with no service identity changes.
- [ ] Write operator runbook and journal distinguishing source completion from actual PR/CI/rollout. Commit cohesive change.
- [ ] Whole-task gate: `python -m unittest discover -s tests -v` (host); separately record real-media verification. One fresh whole-branch reviewer, one Important/Critical TDD fix pass, no rereview.
- [ ] PR and actual latest-head/current-base four-job CI, then authorized merge; no station redeployment needed for host tool.
