# Consistent station backup and restore

Status: engineering design under the user's active finished-product goal and instruction to keep implementing/creating PRs. No separate design approval claimed.

Ship Python-standard-library `python -m radio.backup create BACKUP --data DATA`, `verify BACKUP`, and `restore BACKUP --data EMPTY_DATA` commands. Operators need a repeatable way to recover the queue and completed music after disk/host loss, rather than the existing one-off validation script.

## Approach

A directory bundle with an SQLite online backup and JSON SHA-256 manifest is the chosen implementation. A tar archive would add extraction/path handling and make incremental off-host copies harder. A cloud backup agent would add credentials/dependencies before a target provider is known. Directory bundles can be copied by rsync and verified on either host.

Create reads live SQLite in read-only mode and uses its backup API. Copy immutable WAVs for ready/served snapshot jobs plus the required cached fallback, and available MIDI files. Do not copy temporary renders, health reports, credentials or logs. If retention removes a referenced file during the copy, retry a fresh snapshot at most three times. Other failures propagate and the incomplete new destination is removed. Never overwrite an existing backup. Only publishing the final manifest marks a bundle complete.

Verify requires version 1, exact allowed relative paths, regular non-symlink files, matching sizes and SHA-256, SQLite quick_check and the queue schema, fallback and every ready/served WAV referenced by the snapshot. Validation also checks row IDs/statuses and prevents manifest omissions from silently producing a partial restore. No archive extraction or arbitrary database path value is used.

Restore verifies first, requires a nonexistent or empty destination, copies into a private staging directory, resets rendering jobs to pending (attempts zero), clears stale worker heartbeats, and rewrites saved track paths for the new data root. Retain IDs/seeds and sqlite_sequence. Already-dispatched tracks remain served. On a copy/validation failure leave the original empty destination empty. A destination containing any existing station data must be rejected. Restore is an offline operation into a fresh volume; operator must not start services until success. It does not merge queues.

## Constraints and evidence

No new runtime dependencies, Docker privileges, public ports or queue schema changes. Backups are not encrypted; use encrypted transport/storage and restrict filesystem access. Document non-root Docker mounts, off-host transfer, fresh-volume restore/switch, config/image provenance and verification before deleting old data. Local same-host volumes alone do not satisfy disaster recovery.

Tests cover a live WAL snapshot, identity/sequence continuation, missing optional MIDI, cleanup race retries, corrupt/missing/extra files, unsafe paths/symlinks, invalid DB/manifest, interrupted copy cleanup, destination refusal, and restored render leases/heartbeats. Build the image, perform an actual live-volume backup with read-only source, restore into an isolated volume and render/dispatch from that restored queue. Keep the live station and hour soak untouched. PR remains draft until review and validation, then merge after actual current-head CI passes.
