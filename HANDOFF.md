# Generative Radio — current handoff

Updated 15 November 2026 (Asia/Kolkata). Read this snapshot first; detailed history
and measured iterations are in the [product journal](docs/product-journal.md).

## Goal and standing instructions

Build an always-on original ambient station worth returning to. The user asked
for continued creative iteration, PRs for cohesive work and merges after real
current-head CI passes. The release checklist does not exhaust that product goal.
Keep the journal current on main. Routine implementation, validation, committing,
pushing and CI-cleared merges are already authorized.

The repository is public under MIT: https://github.com/rakeshgangwar/generative-radio.
Installed third-party tools/SoundFonts keep their separate licenses. No VPS,
public domain, off-host backup destination or alert destination has been supplied.
Do not invent a target, provision paid infrastructure or publish this machine.

## What is running locally

- Listener: http://localhost:8080; direct MP3: http://localhost:8000/radio.mp3.
- Five healthy Docker services: composer, renderer, broadcaster, Icecast, optional
  Caddy web gateway. Core remains CPU-only, without a generation API or GPU model.
- Music is composed/rendered ahead into a roughly 20-minute buffer, then streamed
  with crossfades. It is not note-by-note real-time model inference.
- Musical memory reconstructs three-to-five-segment chapters from saved seed/ID,
  balancing harmonic paths and developing a motif/register/palette. Ready audio
  remains immutable; skipped queue jobs can skip chapter stages. A served record
  means dispatched/prefetched, not exact on-air history.
- Version-2 source plans add chapter-shared 6/8/10-bar melodic phrases with a
  one-bar score/MIDI rest over sustained harmony. Workers rolled out at 08:53 IST;
  version-2 job 306 with phrase_bars=10 actually crossed in the broadcaster at
  09:17:28 IST. The queue now contains version-2 ready audio. SoundFont release/
  reverb can ring through MIDI rests. Explicit version-1/unplanned MIDI is unchanged.
- TimGM remains the default sound. Paired TimGM/FluidR3 previews are available in
  the audition artifacts; the asynchronous listening-preference question is open.
- The listener has explicit play/pause, bounded reconnection, native fallback and
  an optional 15/30/60-minute personal sleep timer with a 20-second fade where device
  volume control permits. The timer is page-local and cannot run while frozen.

The musical workers rolled out at 04:54 IST; all 11 ready file hashes were preserved.
Liquidsoap actually crossed into planned job 182 at 05:19:43 IST. The gateway-only
sleep-timer rollout at 06:34 IST left all four music-service IDs/restarts unchanged.

## Delivery and operator tools

Latest local listener delivery is PR #29 (`de1c460`): native-first fallback,
visible keyboard focus handoff and clearer basic-mode help are live. All four
final-head/current-base jobs passed on `1c0e79b`, run43719973080. Only web changed;
all four core identities/start/restart/OOM values were preserved. An existing
listener recovered without another gesture,60seconds of direct core audio decoded,
and fresh liveFirefox/all-eight-asset checks passed. The confirmation bound includes
health waiting; physical audibility and public access are not established.
See the [current delivery receipt](docs/evidence/native-listener-polish-delivery-20261115.json).
Detailed paragraphs below retain historical rollout scope.

Application changes through PR #29 merged after actual final-head/current-base CI. PR #16 (`a00557d`) records the completed
two-hour acceptance and replaces the stale first-laptop handoff. Generation source
is PR #17 (`d82bd17`), version-2 melodic phrasing. All four checks passed on final
head `84c9d33`, run 43671299403. Its candidate image matches all 17 runtime source files at the reviewed commit. Composer/renderer now use it; broadcaster/Icecast/web stayed unchanged.
PR #19 adds explicit offline backup recovery, with 136 real-media Python and 30
listener tests passing. The merged source is available in the local on-demand
CLI image; all five running containers kept their IDs/images/start times. Their
images need not be replaced for this backup-only tool.
PR #20 records the completed mixed 30-minute rollout capture: exactly 1800 seconds
of decoded audio, no silence at least two seconds, 59 healthy watchdog observations
and zero supervisor restarts. Only the final few minutes include version-2 output;
it is not a full 30-minute version-2-only audition or human musical acceptance.

PR #21 (`ab7b601`) adds broadcast chapter context and is deployed locally.
All four latest final-head checks passed on `8482583`, run 43682302746. Only
broadcaster, Icecast and web were replaced at 11:26–11:28 IST. Composer/renderer
kept their IDs/images/start times; all 11 ready-file hashes and the cached fallback
were preserved. Five services are healthy with no restarts/OOM, and ten seconds
of proxied MP3 decoded. At 11:29:24 IST the public chapter 94 bloom label matched
actual Icecast output metadata. Fresh Chromium playback/context/pause also passed.

An already-connected maintenance browser failed to return to playing after the
upgrade; its failed observer did not save state samples, so its exact final state
was not established. Separately, a controlled thirty-second request-failure test
reproduced the old three-retry budget exhausting at roughly twelve seconds.
PR #22 (`1c903de`) extends the fixed schedule to six retries (1/3/8/15/15/15
seconds), preserving finite exhaustion and cancellation. Its 46 listener tests,
eleven actual-browser scenarios and connected-listener three-role replacement
passed. All four final-head CI checks passed on `7001e09`, run 43685359464.
The new policy is deployed to the local gateway. Only web changed; all four music
roles retained their IDs/images/start times. The connected old page recovered, and
a fresh Chromium page loaded the exact policy, played audio, showed context and
released the stream on pause. Refresh once to load the new code on an existing page.
See the [delivery receipt](docs/evidence/listener-recovery-delivery-20261115.json).
One minor remains deferred: timestamped state snapshots in the controlled HTTP-fault
helper. Actual replacement and live rollout telemetry retained sampled states.

The main local core tag now contains PR #21, including the offline backup CLI.
Both music workers intentionally retain the version 2 image from PR #17; their
rendered buffer remains immutable. Retained streaming-role rollback images and a
verified same-host pre-upgrade backup (43 jobs, 89 files) are under local artifact
pointers. No off-host recovery or public deployment is implied.

PR #24 merged the offline melodic-connections audition as `7db3067` after all
four final-head CI jobs passed, including the actual audition render/browser step.
The local comparison at http://localhost:18091 uses the same TimGM font and matched
23m05s levels: current version 2 versus seven quiet connecting notes/five shortened
tails. A bounded tail can retain at least half its original duration and half a
beat; original attacks/pitches/velocities, pads/bass and phrase rests remain fixed.
The preview passed real Chromium playback/seeking/one-at-a-time controls and narrow
layouts. A read-only Caddy audition-only server provides 206 byte ranges; the initial
simple server failed seeking and was stopped. Main station containers/aliases are
unchanged. Independent review is resolved (one phrase-boundary fix), and delivery
is complete. Subjective preference and on-air adoption remain pending; the default
music is unchanged.
See the [audition runbook](docs/melodic-connections.md).

Source checkout is clean on main. Public decoded HTTPS monitoring remains an
operator command, without an installed independent schedule or alert target.

- [Architecture](docs/architecture.md): Python, SQLite WAL, FluidSynth, FFmpeg,
  supervised Liquidsoap, Icecast and optional static Caddy listener.
- [Operations/backup](docs/operations.md): verified create/verify/restore commands,
  exclusive fresh restores, off-host/archive and rollback instructions. Only
  same-host isolated recovery has been exercised; real off-host recovery is open.
- [Production deployment](docs/deployment.md): private random credentials,
  resolved Compose preflight, hardened non-root/read-only profile, persistent TLS,
  startup checks, upgrade/rollback. Package validated locally; no public deployment.
- [Public monitoring](docs/public-monitoring.md): standalone HTTPS+decoded-audio
  check and optional systemd examples. No schedule/notification is installed.
  It needs curl/FFmpeg on the monitoring host and normal or explicit CA trust.
- [Sound auditions](docs/sound-auditions.md): identical-score, attenuation-matched
  comparison CLI, optional isolated FluidR3 image, WAV/MP3/HTML/JSON outputs.
  Fifteen palette/stage cases and three complete chapters were actually compared.

Use isolated worktrees/images/volumes for experiments. Preserve current audio;
roll out only changed roles with explicit source/image and container-ID checks.
Keep existing data and rollback images; no force pushes/admin CI overrides.

## Completed listening-test evidence

The initial 30-minute acceptance, recovery/fallback/reconnect/lease-expiry drills,
one-hour variety baseline and one-hour deployed-watchdog soak passed. The watchdog
hour has 3,600 s audio, no −50 dB silence lasting 2 s, 114 healthy samples, zero restarts/OOM
and stable broadcaster quarter means around 243–245 MiB.

The first attempted two-hour musical rollout recorder ended 143 after about 90 min;
its partial 5,403.38 s is preserved with an unfinalized WAV tail. It is not a completed
two-hour test. Partial analysis: no detected 2 s silence, peak −7.37/RMS −24.62 dBFS,
167 healthy watchdog observations. Old recorder handle 21660 is terminal 143; old
monitor handle 84280 completed exit 0. Never restart or repoll those terminal handles.

The fresh full acceptance completed successfully on 15 November, with capture and
monitor exit 0. Exactly 7,200 s of stereo 44.1 kHz PCM audio has no detected −50 dB
silence lasting 2 s; peak −6.82 and RMS −24.65 dBFS. All 226 watchdog observations
from 06:19:46 through 08:20:46 IST were healthy, with zero recovery/container
restarts or OOM events and unchanged four music-service IDs / Liquidsoap PID 8.
A deliberate web replacement at 06:34 IST shipped the sleep timer; this is not a
full two-hour soak of one web container. Planned ready jobs stayed between 10–11.

Broadcaster memory ranged 246.5–263.5 MiB; quarter averages 249.87, 249.93, 249.39,
249.86 MiB. The post-run SQLite quick_check returned ok, with 11 ready/31 dispatched
jobs, no expired terminal rows, missing referenced audio or temporary work files,
and 907,409,376 data bytes. These observations cover two retention intervals, not
an indefinite leak guarantee or target-host capacity claim.

See the [tracked receipt](docs/evidence/musical-memory-two-hour-20261115.json) for
exact values, source hashes and the intentional web change. Supervisor/capture/
monitor PIDs 456169/456184/456185 are all terminal, verified absent in /proc after
final exit receipts. No acceptance process needs restarting. Other old terminal
handles 24627/77513 and 73227/15955 completed prior baseline/soak runs. CI/preview
handles from merged PRs are terminal.

## Current phrase rollout and live acceptance

PR #17's successful rollout at 03:23:52 UTC preserved all 11 ready WAV hashes and
broadcaster/Icecast/web IDs. Rollback is `generative-radio:before-phrase-breathing`.
An initial snapshot attempt stopped the workers, then failed before new code ran.
The original workers were explicitly restored; the second attempt replaced them.
This extra stop/start is intentional maintenance, not an absent event inferred
from Docker restart_count=0. Raw monitoring observed one exited-worker sample
and one replacement-composer starting sample. Decoded source health stayed good.

The error was reproduced on isolated data: a closed WAL database without sidecars
cannot initialize them on a fully read-only mount. The successful rollout used
SQL mode=ro through the existing data mount, where SQLite may initialize sidecars.
The backup source now provides `create --offline` for an already stopped station.
It recovers a private DB/WAL/journal copy; original source filenames/bytes remain
unchanged. All writers, including broadcaster, must be stopped by the operator;
the flag does not stop them. Non-root read-only mount/restore and actual rendered-
audio round trips pass. Use an image built from this source for the new CLI;
no worker rollout is needed. Never silently use immutable=1 to bypass WAL recovery.

The new live capture completed: both recorder and monitor exited 0. All three
supervisor/capture/monitor PIDs 596862/596863/596864 are terminal, verified absent
in the host process namespace. Never restart or repoll these terminal handles.

- Exactly 1,800 s of stereo PCM; no −50 dB silence lasting at least 2 s; peak
  −8.067364 dBFS, RMS −24.540843 dBFS.
- All 59 decoded-audio watchdog observations were healthy, restart count 0 / child
  PID 8. Broadcaster/Icecast/web identities stayed fixed. Raw monitoring records
  the intentional worker exits/warmup described above; it does not claim every
  worker was healthy during maintenance.
- Planned ready audio stayed at 10–11 tracks; the last observation had all 11 on
  version 2. Actual version-2 prepared/crossfade entries are job 306 at 03:47:28 UTC
  and job 307 at 03:49:23 UTC, within the nominal capture window.
- This is a mixed old-buffer-to-new-phrasing recording, not 30 minutes exclusively
  of version 2, confirmed individual listener history, or subjective acceptance.
- Broadcaster RAM ranged 247.1–262.8 MiB; quarter means 249.10, 249.16, 250.95,
  250.17 MiB. No continuing rise is evident in this observed window.
- Post-run SQLite quick_check ok: 11 ready/31 dispatched, no errors, expired
  terminal rows, missing referenced audio or work files; 907,408,579 data bytes.

The [completed receipt](docs/evidence/phrase-live-acceptance-20261115.json) ties
these values to the raw WAV, analysis, monitoring and transition logs with hashes.
The earlier two-hour recording remains version-1 evidence. Public target capacity,
physical devices, off-host recovery and subjective listening remain open.

## Evidence locations

All local recordings, logs, assets and snapshots are Git-ignored:

- `artifacts/watchdog-soak-20261115/summary.json`: completed watchdog hour.
- `artifacts/musical-memory-20261115/`: score benchmarks, paired rehearsals, worker
  origin/rollback tests, preserved-buffer hashes and first actual planned transition.
- `artifacts/musical-memory-rollout-20261115/partial-summary.json`: interrupted run.
- `artifacts/sleep-timer-rollout-20261115/`: source hashes, rollback/before/after IDs
  and actual delivered localhost:8080 browser playback/cancellation.
- `artifacts/sound-auditions-20261115/`: all palette/stage cases and paired 23m05s
  masters at −22.10 LUFS; provenance, CPU/memory trials and portable player.
- `artifacts/musical-memory-acceptance-20261115-004946/`: completed full acceptance.
- `artifacts/phrase-breathing-rollout-20261115/`: aborted/successful attempts, queued
  file hashes, source/image proof and isolated WAL/backup regressions.
- `artifacts/phrase-breathing-live-20261115-032105/`: completed mixed rollout capture/vitals.

`/tmp/generative-radio-continuation.json` holds convenient pointers, not proof of
liveness or completion. Prefer files/processes/CI/PR state as authoritative.

## Remaining work

Obtain real listening feedback on repetition, coherence and sound character.
When a host/domain is supplied, deploy and verify public DNS/ACME/reboot/capacity,
perform actual off-host recovery and install independent monitoring/alerting at a
chosen destination. Public/physical-device listening remains unverified.

Original architecture conversation reference:
https://chatgpt.com/share/6af89399-506c-83ee-a3cd-66072b4e141b


## Station observer delivered; half-hour observation complete

PR #25 merged at 09:15:30 UTC as `4f3ef70` after final head `a0ce9d0` passed all four
jobs in CI run 43697320412 on unchanged base `7db3067`. Local main is clean and
fast-forwarded. The real Docker-vitals step passed, as did browser playback and
production TLS/certificate recovery. There were two Important review findings;
both were reproduced and fixed in one pass. No Critical findings, deferred minors
or declined behaviors. Final full media suite: 179 tests pass, one explicit live
opt-in skipped; all 18 observer tests pass with that opt-in against Docker.

The host-only [recorder](docs/station-observer.md) was run without replacing any
station role. The one-minute recording passed six healthy samples/three retained
slots with unchanged five-service IDs/state; a corrected-source short recording
passed four healthy samples/two retained slots. Actual SIGTERM retained a cancelled
partial receipt. Failed initial template runs are preserved.

The finite observation completed: session 84456 is terminal exit 0, never restart
or repoll it. The checked run lasted 1800.000301 seconds with 60 healthy
samples and zero unknown/unhealthy observations. Source hashes matched in the
before/after snapshots. Every retained sample matched the initial five-service
identities, start times and restart/OOM state; the final snapshot matched too. All
60 watchdog-report observations were healthy with restart count 0. Broadcaster
RAM sampled 233.6–249.7 MiB, quarter means 236.56/236.49/236.28/236.60 MiB. This is sampled vitals plus
existing watchdog reports, not a new audio capture or independent listener probe.

The [half-hour receipt](docs/evidence/station-observer-half-hour-20261115.json)
contains raw SHA-256 fingerprints, ranges and process exit proof; the
[delivery receipt](docs/evidence/station-observer-delivery-20261115.json) records
exact-head/current-base CI and the merge. Raw local evidence remains ignored under
`artifacts/station-observer-20261115/`. The completed feature workflow is archived
in its `workflow-final` directory. Do not infer indefinite stability or public
capacity from this local observation.

PR #24's matched connecting-note candidate remains at http://localhost:18091 with
no on-air adoption. Public target/off-host recovery and human/device acceptance
remain open.


## Stock Firefox acceptance tool

PR #26 merged the completed observer/journal receipt as `2195b7a` after all four
checks passed. The source now makes the successful five-flow stock-Firefox probe
repeatable with `python -m radio.firefox_smoke`;
see [operator instructions](docs/firefox-check.md). It owns a private profile and
loopback driver process, enforces a wall-clock deadline, saves sanitized partial
reports and never controls station processes or existing browser sessions.

Actual installed Firefox 157.0.1
passed all five basic flows with cleanup. Raw evidence remains ignored under
`artifacts/firefox-check-20261115/`; the earlier exploratory probe is separately
in `artifacts/firefox-20261115/`. The full real-media suite passes 188 tests with one explicit live opt-in skip;
all 46 listener tests pass. The delivery gate is one fresh final review plus all
four actual final-head/current-base CI jobs. The new CI Firefox step must actually
pass, with no skipped-check clearance. Current music and audition adoption stay
unchanged. Physical/Safari/public-host/off-host and human acceptance remain open.


The sole fresh review found one Important acquisition/cancellation race. A real
SIGTERM/SIGINT/SIGALRM regression at Popen return failed for all three signals
before the fix. Signals now defer raising only until the owned process handle is
registered, then are honored immediately without changing the child's signal mask.
All nine focused tests and 188 real-media tests pass (one explicit observer
live-project skip). New actual success/cancel/deadline probes observed 23/7/21 owned
processes, none active afterward, with profiles removed. No Critical findings or
minors; no rereview. The [receipt](docs/evidence/firefox-check-20261115.json) links
these exact source hashes and raw proofs. OS process acquisition and filesystem
cleanup can extend elapsed time; the tool requires trusted installed binaries.


### 15 November: Firefox CI correction, still awaiting acceptance

PR #27 remains draft: runner 43708794835 failed during Firefox launch; three
other jobs passed and later integration steps were skipped. A CI-only virtual
audio sink is an investigated fixture, not a proven fix. No station rollout.
A valid 16-second session response exposed a hidden 15-second socket cutoff.
Session creation now uses the declared overall budget; the global deadline stays.
Only bounded numeric/enum diagnostics are retained from existing polls. A native
play-promise observer returns the original promise and records rejection before
application recovery clears the source. A private 404 drill retained
NotSupportedError/code 4 after the current error became null.
Latest source passed 11 focused tests and 190 real-media tests (one explicit live
observer skip). Actual Firefox passed all five playback flows; success/cancel/
deadline observed 26/9/25 owned processes, none active afterward, profiles removed.
The receipt links exact source hashes and raw proofs. These local results do not
establish CI acceptance: all four final-head/current-base jobs, including the
actual Firefox step, must pass before merging. No second review is requested.


CI run 43712569677 on 670beb7 passed the actual stock Firefox playback step
(12:17:33–12:17:49 UTC). The configured-budget correction and bounded diagnostics
have now reached the runner successfully. This is not proof of the earlier media
stall's root cause; physical sound remains unverified. Broader integration was
still running when recorded. This evidence/documentation update still needs all
four final-head/current-base checks before PR #27 can merge.


## Native-first listener fallback — candidate in progress

PR #27 merged as 5ab28f9 after all four jobs in CI 43713365978 passed on
27f70c6 against 2195b7a, including actual Firefox, Chromium, audition and TLS.
Main is fast-forwarded. No station role was replaced for that host-side tool.

Next branch feat/native-listener-fallback in the managed worktree adds ordinary
HTML native controls, keeping enhanced controls hidden until initialization ends.
A native session already unpaused or with played ranges is preserved for the visit;
no timer/chapter/app-retry enhancement is attached to that ongoing session.
This fixes JS-enabled module failures that bypassed the previous noscript fallback.

Candidate on loopback18092, container radio-native-fallback-preview, uses read-only
candidate assets and the existing stream proxy. No live station role changed.
Eight actual Chromium fallback scenarios pass; Node46 pass. Actual Firefox157.0.1
passed all five enhanced flows and native keyboard playback with JS disabled;
owned driver reaped and private profile removed. Full browser regression, final
fresh review, PR/CI clearance and a measured web-only rollout are still pending.
Raw proofs: artifacts/native-fallback-20261115. Design/plan record exact gates.

The candidate's full Chromium run now passed all19 scenarios (eight newfallback
flows), along with46Node tests and bothFirefox checks. The source-linked receipt
is docs/evidence/native-listener-fallback-20261115.json. Fresh observer baseline
reports all5healthy, no errors; review/CI/rollout gates still open.

The sole fresh review found0Critical/1Important/2Minor. The Important mixed-version
startup bug is fixed: an exact copy of previously deployed HTML (5ab28f9) with new
scripts first reproduced hidden/unusable controls, then passed real start and
pause/source release after guarding absent native markup. Corrected source passes
46Node tests, all20 Chromium scenarios (nine focused fallback/compatibility flows),
and refreshed enhanced/native Firefox checks with cleanup. Two Minor improvements
are deferred: move focus when an idle native control becomes hidden (Tab currently
recovers), and explain native limitations/reload more clearly on the page (README
already does). Their costs are a recoverable keyboard interruption and reduced
discoverability. No rereview. PR #28 still needs final-head/current-base CI and a
measured web-only rollout; no live role changed.


### 15 November: native fallback reaches the local listener

PR #28 merged as 41d2456 after all four jobs in CI 43716620329 passed on
31d9fb8 against main5ab28f9, including stock Firefox, full Chromium scenarios,
audition and TLS rehearsal. A web-only rollout now serves the exact eight verified
assets at localhost8080. Only web changed: composer, renderer, broadcaster and
Icecast retained IDs, images, start times, restart counts and OOM state.

An already playing Chromium listener reconnected without another click, with two
requests total and playback confirmed within27.623seconds of the restart. This
bound includes health waiting; it is not an exact audible interruption or gapless
web-update claim. The direct core recording started producing decoded data before
restart and completed60.000seconds, with no -50dBFS silence lasting two seconds,
RMS-24.4dBFS and peak-10.3dBFS. Fresh liveFirefox passed allfive flows and cleanup;
its eight asset hashes match the merged source. The redundant candidate preview
was removed; the melody audition preview remains. The source-linked delivery
receipt is docs/evidence/native-listener-delivery-20261115.json.

The next iteration addresses the two deferred Minor usability findings: transfer
focus from an idle native control when successful enhancement hides it, and explain
native-mode feature limits plus reloading on the page. This polish is planned,
not yet implemented or deployed. Current version2 music stays on air. Actual
public-host, off-host, physical-device and human listening gates remain open.


### 15 November: visible keyboard handoff — candidate locally verified

The delayed-script focus failure was reproduced before correction. The candidate
now transfers focus from idle native controls to the revealed play button, without
scrolling for focus; an unrelated header link keeps its focus. Real Space-key play
and pause/source release pass, with zero pre-play requests and one stream afterward.
Already started native sessions (playing, paused or pending) retain focus and source.
The fallback help now names full-player features and says reload can try them.

All46Node tests, all22 complete Chromium scenarios, five enhanced Firefox flows,
and Firefox native keyboard playback with JavaScript disabled pass. Focus/help
screenshots fit320px. The source-linked receipt is
 docs/evidence/native-listener-polish-20261115.json. One fresh review, real CI and a
verified web-only rollout remain; the live listener still runs PR28.

A fresh observer correctly reported unknown when the standalone preview inherited
main-project labels from a Compose-built image and appeared as a duplicate web
role. Only that owned preview was recreated with distinct labels. All five live
roles are healthy and match their PR28 delivery identities; the preview still
serves the same eight tested assets. Keep inventory strict. Standalone previews
made from Compose-built images need explicit project identity isolation.

The sole fresh review found0Critical/0Important/0Minor. It independently reran46
Node tests and diff checks, matched asset/proof hashes, and inspected the recorded
actual browser/Firefox evidence and320px screenshots. No correction pass or
rereview is needed. PR #29 is locally verified; final-head/current-base CI and a
separate measured web-only rollout remain required.


## Latest verified local rollout — PR #29

Merge de1c460, final head1c0e79b/base41d2456, CI43719973080 allfour jobs success.
New web ID dcb1fdd578b4, image e69f1155cbb8, started13:52:49.727UTC. Core IDs/images/
start/restart/OOM unchanged. Existing-listener confirmation within27.629seconds
includes health waiting; two requests, no second gesture. Direct core PCM60.000s,
no -50dBFS silence of two seconds, RMS-24.5 and peak-10.4dBFS. LiveFirefox5flows,
cleanup and all8asset fingerprints pass. Owned polish preview removed; melody
preview18091 remains available (root page200 rechecked). Raw evidence is under
artifacts/native-polish-20261115; tracked proof links are in the delivery receipt.
No new music, public deployment or off-host/device/human acceptance is claimed.

Proposed next comfort idea: remember chosen full-player volume across refresh with
no autoplay and no saved sleep timer. It is not implemented. Main current direction
is summarized first in the product journal; historical candidate entries are kept.


## Volume memory candidate — not deployed

Branch feat/listener-volume-memory is based on main `6518051`. The local full-player
candidate remembers canonical whole-percent preferences in browser storage, saves
only explicit range input, and preserves manual play, reset timers, unfaded user
level and ongoing-tab isolation. Storage errors remain optional; native sessions
and device-button fallback retain their existing behavior.

The original 37% → 65% refresh failure was reproduced before the implementation.
Node 46 and eight focused actual Chromium scenarios pass. Firefox 157.0.1 passes the
five-flow regression, native JS-off keyboard playback and a direct chosen 37% reload
with manual playback/timer reset. Final full 30 passed with the strengthened changed-volume-during-fade case. Source review and actual latest
four-job CI remain required, then an annotated measured web-only rollout. Current
live web remains dcb1fdd5/e69 (PR29); candidate is isolated at 18094 with distinct
project labels. The six-hour observer is running; no completed-window claim yet.


The final volume-memory suite passed all 30 Chromium scenarios, including eight
preference/error/fade/cross-tab cases plus the existing native, focus, legacy,
recovery and timer flows. The stronger fade-input case saves 40% while audio is
attenuated to 20%, then reloads at 40% with timer Off and manual play. The 46 Node
tests, five standard Firefox flows, native Firefox JS-off playback and direct
Firefox 37% refresh/manual-play check also passed. All eight asset hashes match
the candidate source; the 320px volume/readout view fits. See the
[local receipt](docs/evidence/listener-volume-memory-20261115.json).

The first requested six-hour observation was interrupted after 40 healthy samples;
its owned process was gone and the execution session exited143. Its raw running
summary is preserved and is not completion evidence. A fresh finite detached
wrapper/observer is alive by PID/start identity and reports healthy samples. The
previous partial window is not combined into continuous six-hour acceptance; the
exact external termination cause is unknown. The live listener remains PR #29.
One fresh source review, actual CI and an annotated web-only rollout remain pending.
