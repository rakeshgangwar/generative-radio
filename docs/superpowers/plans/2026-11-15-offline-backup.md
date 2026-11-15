# Offline backup recovery implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Back up a stopped WAL station from a read-only mount without losing committed frames or modifying its source.

**Architecture:** Explicit offline mode recovers a private database/sidecar copy, then uses the existing SQLite backup/manifest pipeline. Online mode remains default and never implicitly uses immutable reads.

**Tech Stack:** Python sqlite3/tempfile/pathlib, existing Docker image and backup CLI.

**Spec:** `docs/superpowers/specs/2026-11-15-offline-backup-design.md`

## Global constraints

- Preserve `create_backup(data, destination)`; append keyword-only `offline=False`. Only create accepts `--offline`.
- Offline requires every DB writer stopped, including broadcaster; the tool does not stop them or prove offline state from stats.
- Copy DB and present WAL/rollback journal to private staging; never copy SHM or open original source writable; never implicitly use immutable=1.
- Preserve committed WAL data, bundle format, source names/bytes, existing destination/manifest/path checks; reject observed copy-time source changes.
- Keep live station containers, volume, TimGM and current recording unchanged.

## Review focus

- Crash-like WAL commits missing from main must survive: Task 1 copied-open-WAL fixture.
- Source sidecars appear/disappear during copy: Task 1 fingerprint regression.
- Symlink or nonregular WAL/journal must fail safely: Task 1 path tests.
- Existing online callers/mocks/CLI must keep working: Task 1 compatibility and argument tests.
- Private recovery sidecars must not leak into final manifest: Task 1 bundle enumeration and Task 2 real mount/restore.

### Task 1: Explicit private offline recovery

**Files:** Modify `radio/backup.py`, `tests/test_backup.py`; add focused `tests/test_offline_backup.py` if needed.

**Interfaces:** `create_backup(data: Path, destination: Path, *, offline: bool = False) -> dict`; existing verify/restore signatures and manifest version1 unchanged. Internal snapshot helper may take offline keyword; preserve tests that patch it.

- [x] Write failing tests for offline API/CLI support, closed WAL/no SHM, committed crash-like WAL recovery, source filenames/SHA-256 equality, no staging files in manifest, rejected sidecar symlinks/nonregular files and observed source changes. Use actual SQLite schema and existing backup/restore checks.
- [x] Run focused tests and confirm missing behavior before implementation. Keep existing online baseline passing.
- [x] Implement private-copy recovery with temporary context cleanup before final enumeration, read source only and compare pre/post copy stats. Keep consistent online SQLite backup and its timeout.
- [x] Add clear mode/help guidance; offline is explicit and does not freeze the station. Run focused and full unit suites with real audio tools; fix actual regressions and commit.

### Task 2: Read-only mount/recovery evidence and runbook

**Files:** Update `docs/operations.md`, `docs/product-journal.md`; add compact measured receipt under `docs/evidence/` and update handoff's known issue after verified delivery.

**Interfaces:** Existing image-based create/verify/restore CLI, plus create --offline. No source/restore volume mounted together during restored rendering.

- [x] Exercise a non-root read-only closed-WAL fixture and a crash-like committed-WAL fixture; verify and restore complete bundles, checking source hashes before/after. Require failed/default create to stay a failure, not fallback immutable.
- [x] On isolated actual station audio, create/verify/restore an offline bundle and decode/analyze a restored render; check queue sequence continuity and no source writes. No live volume write/recreation.
- [x] Record measured results, exact modes and limits; document stopping all DB writers for offline mode and keeping default online backups for normal uninterrupted operation.
- [x] Confirm diff/source/evidence checks and commit the deliverable.

## Delivery gates

- [ ] One fresh independent whole-branch review; one verified Important/Critical fix pass if needed.
- [ ] Scoped PR with all four actual final-head/current-base checks passing before merge; main fast-forward and honest journal update. CLI is on demand; no worker rollout is needed for this backup-only change.
