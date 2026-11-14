# Backup and Restore Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship repeatable verified queue/audio backups and safe isolated restores.
**Architecture:** Standard-library module snapshots SQLite, copies referenced media, publishes a final manifest, verifies bundles, and restores only into empty data roots.
**Tech Stack:** Python >=3.11, SQLite, pathlib/shutil/hashlib, existing Docker image.
**Spec:** `docs/superpowers/specs/2026-11-15-backup-restore-design.md`

## Global Constraints

No new dependencies, schema changes, Docker socket or credentials in backups. Three snapshot attempts for missing referenced media; other errors fail. Backup destination must not exist. Restore destination must be nonexistent or empty. Never mutate the backup during restore. Keep the running one-hour soak untouched. Native execution with one final independent reviewer; existing user autonomy authorizes implementation and CI-cleared PR merges.

## Review Focus

- Retention deletes an old served file while copying: retry the whole snapshot.
- A valid-checksum but incomplete manifest must not restore a broken ready queue.
- Traversal, symlinks and extra files must fail verification without writes outside the destination.
- Interrupted writes must not leave a complete-looking bundle or populated failed restore.
- Restored jobs/sequence/path/heartbeats must work at a different data root.

### Task 1: Ship backup, verification and restore commands

**Files:** Create `radio/backup.py`, `tests/test_backup.py`, `docs/operations.md`; update `README.md`, `HANDOFF.md`, `docs/product-readiness.md`.
**Interfaces:** `create_backup(data: Path, destination: Path) -> dict`, `verify_backup(backup: Path) -> dict`, `restore_backup(backup: Path, data: Path) -> dict`, and `python -m radio.backup {create,verify,restore}` CLI. Raise ValueError/OSError/sqlite3.Error for invalid inputs/IO, CLI returns nonzero with concise diagnostics.

- [x] Add tests for a real Store in WAL mode, ready/served/rendering jobs, fallback and optional MIDI; round-trip into new root verifies checksums, reset leases/heartbeats, dispatch and new IDs/seeds. Run focused tests; expect missing-module RED.
- [x] Implement snapshot/manifest/verification/restore. Add adversarial and IO-failure tests from Review Focus, observe each RED and fix to GREEN. Run full unittest suite; expect all passing.
- [x] Add concise non-root Docker/off-host/restore runbook and update current watchdog acceptance facts.
- [x] Build actual image without replacing the live image tag. Create from live read-only volume; restore to a separate volume, dispatch/analyze and render a new segment. Expected unchanged live service identities, valid audio and advancing job IDs.
- [x] Request one independent whole-branch review; fix Important/Critical findings with failing regressions and the full green suite.
- [ ] Commit/push PR, await current-head CI, mark ready and merge only after final CI passes. Record measured evidence without claiming whole-product completion.
