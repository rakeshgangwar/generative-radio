# Release readiness evidence

This release's operational target is an unattended 24×7 CPU-only generative
ambient station on a single Linux VPS. The accepted architecture remains Python, FluidSynth,
Liquidsoap, Icecast, local SQLite and Docker Compose. No GPU, management UI,
multiple genres or external composition API is required for this release.

Historical sections below retain their original candidate/rollout status. Use the
latest dated receipt and [current handoff](../HANDOFF.md) for present state.

## Completion gates

| Requirement | Evidence required | Current state |
| --- | --- | --- |
| Original coherent, reproducible music | Note/MIDI tests, real SoundFont renders, user listening | Technical checks pass; listening acceptance of the variety update is pending |
| Buffered continuous output | Full-stack recording and queue replenishment evidence | Two-hour version-1 recording and mixed version-2 rollout capture passed; ready queue stayed at 10–11 |
| Recovery from interrupted generation and streaming | Failure drills and decoded audio after recovery | Fallback, restart, Icecast reconnect and real lease-expiry drills passed |
| Silent/hung broadcaster detection and recovery | Missing-stream/silent-audio/hung-child drills, bounded restart evidence | PR #3 merged after CI; isolated silence/hang/missing-mount drills passed; deployed locally |
| Bounded storage and resource use | More than one retention interval observed, longer unattended soak | Two-hour musical-memory soak/retention and 60 healthy half-hour observer samples passed locally; actual target capacity remains open |
| Repeatable validation of changes | Automated PR unit checks and short container integration checks | CI is on main: Python 3.11/3.14 plus real rendering/streaming checks |
| Safe operation on the target VPS | HTTPS, non-default credentials, restricted administration, startup/reboot verification | Production package validated locally; actual target host/domain not yet provided |
| Audible public listening path | Authenticated HTTPS fetch, bounded decode and audibility check on an independent host | Read-only command and local TLS rehearsal passed; independent deployment pending |
| Backup and recovery | Consistent queue/audio backup and tested restore on isolated data | Repeatable create/verify/restore commands and off-host runbook validated locally; target-host/off-host exercise pending |
| Operator documentation | Install, upgrade, monitor, recover, back up and roll back commands | Local recovery/backup runbook implemented; production deployment runbook added; target-host exercise pending |
| Reviewed delivery | Scoped PRs with measured validation and resolved release findings | Changes through PR #25 merged after final-head/current-base CI; recent work includes audible chapter context, deployed listener recovery, an offline melody audition and host-side vitals recording |

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
same host and are not protection against host loss. Repeatable operator commands
and off-host copy/retention instructions have since shipped (see below); actual
off-host transfer and a target-VPS restore drill remain open.

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


## Musical-memory candidate — isolated render validation

The planner uses saved job seed/ID and constant-work shuffled blocks; no queue
schema change. A 256-position score comparison has 0/255 equal adjacent harmonic
openings versus 54/255 in the baseline, and eight first melody pitches versus three.
A starts 65/256 rather than 198/256. These are score properties, not a subjective
acceptance claim. Queue skips can skip chapter stages; on-air history is not added.

All 15 palette/stage 20-second renders passed existing gates (maximum quiet fraction
0.025, peak at most -8.43 dBFS). Twelve planned 120-second renders took 3.648–3.819 s,
with peak at most -7.78 dBFS. Baseline and planned 12-segment offline crossfades are
1,385 seconds each; both have no -50 dB silence lasting two seconds. Planned sequence
RMS is -24.30 dBFS, peak -7.78 dBFS. Offline linear crossfades stress transitions;
actual live Liquidsoap/user listening remains separately required.

An actual renderer consumed two saved job origins 42/5000 while its environment
station seed was 9999, saved the expected plans, replenished two ready jobs and
kept fallback independent. Repeating with MUSICAL_MEMORY=0 produced legacy metadata
shape, no queue errors. Explicit planned preview CLI rendered valid 20-second audio.
Artifacts: `artifacts/musical-memory-20261115/` (baseline/planned-score JSON,
audio-report, worker-check, cli-preview, paired sequence WAVs/analysis). The lab
volume is isolated from live data. 74 backend and 19 listener checks pass locally;
final independent review/current-head CI and production worker rollout are pending.


## Completed two-hour musical-memory acceptance — 15 November 2026

The detached recorder and monitor both exited 0; their processes were verified
absent after the final receipt. The complete WAV contains exactly 7,200 seconds
(317,520,000 stereo frames, 16-bit PCM at 44.1 kHz). No silence at −50 dB lasting
at least two seconds was detected. Overall peak is −6.817653 dBFS and RMS
−24.645587 dBFS. This is a completed new recording; the earlier interrupted
90-minute WAV remains separate partial evidence.

All 226 monitoring observations between 00:49:46 and 02:50:46 UTC (06:19–08:20 IST)
succeeded. Every decoded-audio watchdog report was healthy, with restart count 0
and Liquidsoap child PID 8. All four music containers kept their identities and
healthy status, without container restarts or OOM kills. The web gateway changed
once for the deliberate CI-cleared sleep-timer deployment at 01:04 UTC; this test
does not establish two hours for a single web-container build. Planned ready tracks
stayed between 10 and 11, with no failed jobs observed.

| Service | Observed memory range (MiB) | Sampled mean CPU (% of one core) |
| --- | --- | --- |
| Broadcaster and probes | 246.5–263.5 | 10.43 |
| Renderer | 17.05–75.29 | 5.59 |
| Composer | 14.53–29.29 | 1.20 |
| Icecast | 4.11–11.65 | 0.53 |
| Web, across its deliberate replacement | 16.02–19.92 | 0.21 |

Broadcaster quarter means are 249.87, 249.93, 249.39 and 249.86 MiB; first/last
247.3/248.1 MiB. There is no continuing rise in this observed window. Docker CPU
samples are intermittent measurements, not integrated CPU cost or a load test;
the renderer's sampled maximum was 119.17%. Host available memory stayed above
20.88 GiB and disk free above 552.71 GiB while other development ran on this host.

After the recording, read-only SQLite quick_check returned ok: 11 ready and 31
retained dispatched jobs, no queue errors, expired terminal rows, missing
referenced audio or temporary render files. Data occupied 907,409,376 bytes.
Two retention intervals elapsed with the ready buffer replenishing. Broadcaster
logs record prepared/crossfade transitions through the run; dispatch remains
prefetch evidence, not exact listener playback history.

The [machine-readable receipt](evidence/musical-memory-two-hour-20261115.json)
contains exact aggregates, process exit receipts, retention state and SHA-256
hashes tying it to the local recording, analysis and raw monitoring sources.
The raw sources stay Git-ignored at
`artifacts/musical-memory-acceptance-20261115-004946/`.

PR #15 has also merged after all four checks passed on head `196747c`
([CI run](https://github.com/rakeshgangwar/generative-radio/actions/runs/43668429928)).
The standalone public monitor and production startup now decode an authenticated
HTTPS sample and test audibility; no independent schedule or alert destination
has been installed. Public host/domain/reboot/capacity, actual off-host recovery,
physical-device behavior and subjective musical acceptance remain open. A local
two-hour pass does not establish these requirements or indefinite 24×7 behavior.


## Completed mixed phrase-rollout capture — 15 November 2026

The new recorder and monitor both exited 0. Exactly 1,800 seconds of audio has no
−50 dB silence lasting two seconds; peak −8.067364 dBFS and RMS −24.540843 dBFS.
All 59 watchdog observations were healthy with restart count 0 and child PID 8.
Broadcaster/Icecast/web identities stayed unchanged; all ready-file hashes from
the successful worker replacement were preserved. Monitoring contains the
intentional original-worker exits in the aborted snapshot attempt and replacement
composer warmup. These are explicitly recorded maintenance, not uniformly healthy
worker observations or evidence of no manual starts/stops.

Actual broadcaster preparation/crossfade logs show version-2 jobs 306 and 307 at
03:47:28 and 03:49:23 UTC during the nominal capture window. The recording mostly
contains the preserved version-1 queue, then several minutes of new phrasing; it
is not a full version-2-only thirty-minute soak or confirmed listener history.
The ready queue stayed at 10–11 and ended with 11 version-2 tracks.

Broadcaster memory ranged 247.1–262.8 MiB; quarter means 249.10/249.16/250.95/250.17.
Post-run SQLite quick_check returned ok, with 11 ready/31 dispatched, no expired
terminal rows, missing referenced audio or temporary work, and 907,408,579 bytes.
The [tracked receipt](evidence/phrase-live-acceptance-20261115.json) includes raw
hashes and exact scopes. The earlier full two-hour test remains version-1 evidence.

Explicit offline backup recovery has also passed non-root read-only mount,
committed-WAL/hot-journal and actual rendered-audio restore checks, then final-head
CI before PR #19 merged. It is an on-demand tool; making its verified image available
changed no running service. Actual public-target/reboot/capacity, off-host recovery,
physical-device and subjective listening acceptance remain open.


## Completed reusable vitals observation — 15 November 2026

PR #25 merged as `4f3ef70` after all four actual final-head/current-base checks
passed, including its real Docker-vitals step. The host-only recorder then
completed a 1800.000301-second observation with 60 healthy samples,
zero unknown/unhealthy samples, and unchanged five-service identities/start times,
restart/OOM state and observer source hashes. Broadcaster RAM sampled
233.6–249.7 MiB; quarter means 236.56/236.49/236.28/236.60 MiB. It retained 60 samples plus one
summary within 120 configured slots. Actual rotation was tested separately in the
one-minute/six-sample acceptance with three retained slots.

The [measured receipt](evidence/station-observer-half-hour-20261115.json) includes
process exit 0, per-service ranges, host metrics and raw-file fingerprints; the
[delivery receipt](evidence/station-observer-delivery-20261115.json) records the
exact CI run, head/base and merge. This observes existing station decoded-audio
reports, not a new audio capture or independent probe. It does not establish
unsampled peaks, indefinite stability, subjective listening, physical devices,
public-target capacity or off-host recovery. Those release gates remain open.
