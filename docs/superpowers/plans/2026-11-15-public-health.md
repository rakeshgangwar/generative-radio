# Public listener health implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Verify authenticated public audio is decodable and audible, not merely returned as bytes.
**Architecture:** Standalone HTTPS CLI/API with shared deadline and bounded local decode, reused by production startup.
**Tech Stack:** stdlib Python, existing curl/FFmpeg, watchdog PCM assessment/process cleanup; no dependencies.
**Spec:** docs/superpowers/specs/2026-11-15-public-health-design.md

## Global Constraints

HTTPS only/normal or explicitCA trust/no insecure mode, no URL credentials/query/path.
Default20s shared deadline,1–60s configurable;256KiB MP3 prefix,3s8kHzmono PCM.
Owned groups cleanup, local-file/pipe MP3-only decode, structuredsafeJSON/exit0/1/130.
No source control/restarts/schedules/messages/publicdeployment. Preserve live acceptance.
One final independent review and current-head CI-cleared PR under standing authority.

## Review Focus

- Content-type/body size must not disguise junk or encoded silence.
- TLS trust/hostname failure must not reach a direct insecure decoder path.
- DNS/headers, downloads and decoding share one deadline, including cancellation cleanup.
- Malformed origins/ports/control characters must not reach subprocesses or leak secrets.
- Finite/truncated prefixes and tool failures must never be reported healthy.

### Task1: Deliver and integrate the public listener probe

**Files:** new radio/listener_health.py, tests/test_listener_health.py, docs/public-monitoring.md; modify production.py, production-smoke.py, deployment/runbook/journal/HANDOFF/readiness.
**Interfaces:** ListenerHealthError(kind,detail), validate_origin(url), probe(url,ca_file=None,timeout=20). production.probe_https wraps API preserving ProductionError. CLI module no Docker/config dependency.

- [x] Reproduce current false-positive with private TLS junk/silence and trusted positive control. Both assertions fail; trust/hostname controls pass. Fixture initially lacked Content-Length and produced curl56; corrected framing before claiming RED.
- [x] Add pure URL/budget/metadata tests and bounded header-hang/CLI-cancellation regressions; observe missing behavior RED. Implement probe and production wrapper to GREEN.
- [x] Run all real-media tests and an isolated hardened production/TLS smoke, proving returned decoded seconds/RMS; verify no live service changes.
- [ ] Document off-host read-only monitoring/scheduler examples and limitations, update journal, one final independent review/regressions, full suite/current-head CI then PR merge. Actual external deployment remains pending target.
