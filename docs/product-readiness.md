# Release readiness evidence

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
| Silent/hung broadcaster detection and recovery | Missing-stream/silent-audio/hung-child drills, bounded restart evidence | PR #3 merged after CI; isolated silence/hang/missing-mount drills passed; deployed locally |
| Bounded storage and resource use | More than one retention interval observed, longer unattended soak | One-hour variety and deployed-watchdog soaks passed; actual target deployment still needs validation |
| Repeatable validation of changes | Automated PR unit checks and short container integration checks | CI is on main: Python 3.11/3.14 plus real rendering/streaming checks |
| Safe operation on the target VPS | HTTPS, non-default credentials, restricted administration, startup/reboot verification | Target host/domain not yet provided; deployment package still needed |
| Backup and recovery | Consistent queue/audio backup and tested restore on isolated data | Repeatable create/verify/restore commands and off-host runbook validated locally; target-host/off-host exercise pending |
| Operator documentation | Install, upgrade, monitor, recover, back up and roll back commands | Local recovery/backup runbook implemented; production deployment runbook incomplete |
| Reviewed delivery | Scoped PRs with measured validation and resolved release findings | PRs #1–#7 merged after CI; backup tooling is the next reviewed iteration |

These are release readiness gates, not an exhaustive definition of the evolving
product goal. The [product journal](product-journal.md) records that direction.
A green unit suite alone is insufficient for a release. Local audio artifacts are referenced in HANDOFF.md
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
5. Resolve release findings through PRs. The user has authorized merging ready
   PRs after real CI passes; keep unfinished work in draft and revalidate changed
   merge candidates. Do not claim the release is finished before every gate passes.

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

## Acceptance-script correction and active soak — 15 November 2026

Found and reproduced a validation bug: the recording script returned success
after a one-second HTTP source ended during a requested five-second capture.
PR #4 adds a decoded-duration check, rejects invalid durations, removes stale
analysis and allows an explicit station URL. The exact controlled HTTP fixture
now returns failure as expected. Five new FFmpeg integration tests pass; combining
the fix with the musical-variety change in a temporary checkout passes 18 tests.
PR #4 is based on PR #1 and does not require the pending watchdog implementation.

A one-hour uninterrupted recording and resource/queue/health monitor started
at 01:12 on 15 November (Asia/Kolkata). Evidence was written under
`artifacts/soak-20261115/`. The active main-checkout script was not edited; the fix
was made in a separate worktree. Its completed duration was independently checked;
results follow. A soak of the eventual watchdog/deployment configuration is still
required.

## Interrupted-render storage regression — 15 November 2026

PR #5 fixes a second retention failure path: a renderer killed on its last
allowed attempt can leave raw/processed temporary WAVs behind. Existing cleanup
removed the expired failed row and its published/MIDI files, leaving the work
files permanently untracked. A regression exhausting all three real queue claims
through stale-lease recovery reproduced that leak. Cleanup now includes that
expired terminal job's two temporary audio paths. A safety test proves active
and recent work remains untouched.

The fix passes 10 tests on the integration base. A temporary combined checkout
with the variety and capture-duration updates passes 20 tests. PR #5 is based on
PR #1, independent of PRs #2–#4. It has not been deployed during the current soak.
The live stream now includes new-composer tracks (for example, track 59); fresh
listening feedback has been requested and remains pending.

## Completed one-hour variety soak and CI — 15 November 2026

The recording completed with exactly 3,600.000 seconds of decoded audio. No
silence at -50 dB lasting at least two seconds was detected; peak was -8.21 dBFS
and RMS -24.59 dBFS. All 64 monitoring samples were healthy, with zero restarts,
OOM kills or queue errors. Each container's identity/start time stayed unchanged.
Broadcaster RAM ranged from 226.8–232.0 MiB; composer 14.06–15.64 MiB, renderer
15.04–74.85 MiB including rendering, and Icecast 4.16–6.05 MiB. Full evidence is in
`artifacts/soak-20261115/`, including `summary.json` and `vitals.jsonl`.

PR #6 added actual CI and was merged after its checks passed. It enabled the same
checks on PR #1, which then merged to main. PRs #2/#4/#5 were retargeted/updated
against the integrated base and merged only after their Python and real streaming
checks passed. No draft watchdog work was merged as part of this sequence.

The integrated watchdog candidate passes 42 local tests, including real decoder timeout/
cancellation, rolling restart limits, process/descendant cleanup, signal handling
and health-report write failures. Independent review found a synchronous status
lookup outside the deadline; two failing regressions reproduced it, and owned
cancellable curl execution now shares the overall probe deadline. Curl was
already installed in the image. Runtime drills also exposed slow default FFmpeg
input analysis with short test thresholds; explicit analysis bounds reduced a
measured one-second probe from about 4.5 seconds to 0.3 seconds. Startup/transport
margin is still required; this timing comparison is not a latency guarantee.

Final isolated drills passed with explicit shortened thresholds (10-second grace,
one-second sample, eight-second deadline, two failures and two restarts per 60
seconds). A 60-second ordinary-playback baseline had 56 observations and zero
restarts. Killed and stopped/hung Liquidsoap children recovered. Missing mounts
and real encoded silence were detected, restart limits held at two, and restoring
the correct script recovered decoded audio after the rolling window permitted it.
The server-outage/native-reconnect case used a five-second probe interval to allow
Liquidsoap's native retry (production uses 30 seconds); the child PID and restart
count stayed unchanged through the outage and restoration.

Evidence is in `artifacts/watchdog-20261115/final-process-recovery.json`,
`final-audio-recovery.json`, `final-native-reconnect.json` and associated logs.
The final operator documentation/short-probe CI step still needs current-head CI
clearance before merge. The live broadcaster has not yet been updated.


## Watchdog rollout and repeatable backups — 15 November 2026

PR #3 passed current-head CI, was marked ready, then passed its readiness-triggered
CI run and merged. All four local services are healthy. The broadcaster now runs
the supervisor with production defaults; decoded audio is healthy with zero
failure/recovery counters. A 30-second post-rollout capture completed with no
silence at -50 dB lasting two seconds. Icecast retained its container identity.
The separate one-hour watchdog recording/monitor completed successfully; full results follow.

The new backup module uses no new dependencies and reads the source volume
read-only. Actual create captured 43 jobs and 89 files (920,879,096 bytes), verified
and restored to a separate volume. Restored track 117 passed analysis at 120
seconds; the queue allocated ID 128 after snapshot maximum 127 and rendered a
new 20-second segment in 0.906 seconds with no queue errors. Source/restore
volumes were never mounted together during the restore/render test. Evidence:
`artifacts/backup-tools-20261115/{create,restore,round-trip}.json`.

The full 58-test local suite includes snapshot/manifest/restore tests and an
exclusive concurrent-restore regression. [Operator commands](operations.md)
cover off-host export, encrypted transfer, fresh-volume restore, validation and
volume switch/rollback. An actual off-host transfer/target-VPS recovery remains
unverified until those destinations exist. The software does not claim a
same-host backup volume protects against host loss.


## Listener experience — local validation

The optional page at localhost:8080 provides explicit start/pause, volume,
truthful buffering/retry feedback, bounded automatic reconnection and native
no-JavaScript fallback. Only the static page and /radio.mp3 are proxied; actual
admin/status/data-path requests returned404. Ten seconds of proxied audio decoded
successfully. Core container identities and the active watchdog soak are preserved.

Nineteen deterministic JS/presentation tests pass. Isolated headless Chrome tests
passed actual play/keyboard/volume/pause/resume, failed-request reconnection,
390px/320px layout, reduced motion and native fallback. Desktop/mobile screenshots
were visually inspected. Native browser tooling lacked a display server, so QA
uses a temporary headless Chrome profile; no user browser/profile was changed.
Physical iOS/Android devices and public HTTPS remain unverified. CI is being
extended to cover controls, non-root proxy config, restricted paths, decoded
proxied audio and browser behavior against the real stack.


## Completed deployed-watchdog soak — 15 November 2026

Both recording and monitor processes exited0. The recording contains exactly
3,600 seconds. No silence at -50dB lasting two seconds was detected; overall peak
was -7.9912dBFS and RMS -24.5169dBFS. All 114 samples from 21:34:32 to 22:35:32UTC
(03:04–04:05 Asia/Kolkata) had healthy core services and decoded-audio reports.
There were zero container/recovery restarts, OOM kills or queue errors. Container
identities/start times and the Liquidsoap child PID stayed unchanged.

| Core service | Observed memory range (MiB) |
| --- | --- |
| Broadcaster, including supervised probes | 240.3–263.4 |
| Renderer | 14.69–72.43 |
| Composer | 14.07–27.55 |
| Icecast | 4.13–6.00 |

Broadcaster quarter averages were 243.43, 243.24, 244.54, 243.91 MiB; first/last samples
were 240.6/241.1 MiB. No continuing rise is evident in this hour. Worker heartbeat
ages stayed at or below 2 s. Post-run SQLite quick_check returned ok; 11 tracks ready,
31 retained dispatched, work directory empty, 907,415,726 data bytes. The optional
web service was added during this run: 62 partial-run observations measured
14.06–24.64 MiB. It is not claimed as a full-hour web soak.

Local evidence: `artifacts/watchdog-soak-20261115/summary.json`, `vitals.jsonl`,
`broadcast-60min.wav`, `analysis-60min.log`, and `retention-after.json`. This proves
local observed behavior while development/browser QA ran on the host. Target-VPS
capacity/reboot/HTTPS and subjective listening acceptance remain open.

PR #9 merged the listener after all four checks passed, including browser tests
against the actual stack. Native-pause cancellation and no-JS/description fixes
were regression-tested before merge. Musical-memory work has not changed the
live station; its baseline score sample is recorded in the product journal.
