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
| Backup and recovery | Consistent queue/audio backup and tested restore on isolated data | Not yet exercised |
| Operator documentation | Install, upgrade, monitor, recover, back up and roll back commands | Local startup/recovery documented; production runbook incomplete |
| Reviewed delivery | Scoped PRs with measured validation and resolved release findings | PRs #1 and #2 open; merges require user instruction |

The goal is not complete while any gate is missing or unverified. A green unit
suite alone is insufficient. Local audio artifacts are referenced in HANDOFF.md
and remain Git-ignored; measured results are recorded in tracked documentation.

## Work order

1. Add broadcaster supervision and decoded-audio monitoring, then run isolated
   failure drills. Keep the live station running while developing it.
2. Add automated PR validation and test a consistent backup/restore procedure.
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
