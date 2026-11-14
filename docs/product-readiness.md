# Product completion requirements

The goal is a finished, unattended 24×7 CPU-only generative ambient station on a
single Linux VPS. The accepted architecture remains Python, FluidSynth,
Liquidsoap, Icecast, local SQLite and Docker Compose. No GPU, management UI,
multiple genres or external composition API is required for this release.

## Completion gates

| Requirement | Evidence required | Current state |
| --- | --- | --- |
| Original coherent, reproducible music | Note/MIDI tests, real SoundFont renders, user listening | Technical checks pass; listening acceptance of the variety update is pending |
| Buffered continuous output | Full-stack recording and queue replenishment evidence | 30-minute recording passed; 11 ready tracks maintained |
| Recovery from interrupted generation and streaming | Failure drills and decoded audio after recovery | Fallback, restart, Icecast reconnect and real lease-expiry drills passed |
| Silent/hung broadcaster detection and recovery | Missing-stream/silent-audio/hung-child drills, bounded restart evidence | Not implemented; watchdog design proposed |
| Bounded storage and resource use | More than one retention interval observed, longer unattended soak | Retention cleanup observed after one hour; continuous long soak still needed |
| Repeatable validation of changes | Automated PR unit checks and short container integration checks | Local tests pass; CI workflow still needed |
| Safe operation on the target VPS | HTTPS, non-default credentials, restricted administration, startup/reboot verification | Target host/domain not yet provided; deployment package still needed |
| Backup and recovery | Consistent queue/audio backup and tested restore on isolated data | Local isolated restore passes; repeatable operator command and off-host storage still needed |
| Operator documentation | Install, upgrade, monitor, recover, back up and roll back commands | Local startup/recovery documented; production runbook incomplete |
| Reviewed delivery | Scoped PRs with measured validation and resolved release findings | PRs #1 and #2 open; merges require user instruction |

The goal is not complete while any gate is missing or unverified. A green unit
suite alone is insufficient. Local audio artifacts are referenced in HANDOFF.md
and remain Git-ignored; measured results are recorded in tracked documentation.

## Work order

1. Add broadcaster supervision and decoded-audio monitoring, then run isolated
   failure drills. Keep the live station running while developing it.
2. Add automated PR validation and package the tested backup/restore procedure
   into repeatable operator commands, including off-host backup instructions.
3. Prepare the production deployment/runbook, then deploy when the user supplies
   the target host/domain and access. Do not provision a paid VPS implicitly.
4. Run the final configuration through an uninterrupted soak, including at least
   one retention cycle, resource monitoring and user listening acceptance.
5. Resolve release findings through PRs. Keep PRs open until the user requests
   merges; do not claim the unmerged main branch is the finished release.

## Runtime retention observation — 15 November 2026

After more than one hour of station activity, a direct SQLite/filesystem check
found 11 ready tracks (IDs 48–58), 32 retained dispatched tracks (IDs 16–47), no
expired terminal rows, and no temporary render files. Earlier dispatched IDs had
been cleaned up. The data volume used 928,553,349 bytes, consistent with the
documented approximately 1 GB buffer/history budget. Broadcaster RAM was 227.1
MiB. This verifies an actual cleanup cycle; it does not substitute for a longer
uninterrupted soak of the final release configuration.

## Isolated backup/restore validation — 15 November 2026

Using the current station image, mounted the live data volume read-only and
disabled networking for the backup container. Python's SQLite backup API created
a consistent database snapshot in a separate Docker volume. Copied the completed
audio files referenced by that snapshot, available MIDI files, and cached fallback;
saved a SHA-256 manifest after closing the snapshot database.

Restored into a second isolated volume with networking disabled and no live
volume mounted. All 88 checksums matched; SQLite `quick_check` returned `ok`.
The snapshot contained 43 jobs and 11 ready tracks. Dispatching restored track 51
returned valid 120-second audio that passed the existing quality gates. The queue
then allocated job 62 after snapshot maximum ID 61 and rendered it successfully
in 3.705 seconds, restoring the ready buffer to 11 tracks with no errors.

The backup used 920,880,272 bytes. Local evidence is in
`artifacts/backup-restore-20261115/backup-result.json` and `restore-result.json`.
The snapshot and restored test data remain in the separate Docker volumes
`generative-radio-backup-20261115` and `generative-radio-restore-20261115`.

This validates local consistency and queue continuity. These volumes are on the
same host and are not protection against host loss. A shipped operator command,
off-host copy/retention instructions and target-VPS restore drill remain open.
