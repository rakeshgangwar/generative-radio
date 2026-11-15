# Generative Radio — product journal

A living record of what we are building, what we have learned, and what we may try next. Updated 15 November 2026, Asia/Kolkata.

## The starting idea

An always-on station that composes its own ambient music. Press play and enter a continuous musical space: calm enough to work, read, rest or sleep with, but alive enough that an attentive listener hears development. The station should feel like a place worth returning to.

The first implementation uses musical rules and seeded probability to write original arrangements, FluidSynth to play them, and Liquidsoap/Icecast to broadcast them. It renders ahead into a buffer, so listening does not depend on every note being generated at playback speed. The core runs on a CPU without an external generation API. Available GPU compute is an opportunity for experiments, not a requirement for listening.

This journal is a working direction, not a definition of perfection or a promise that every proposed feature will ship. We will keep iterating based on listening, measured behavior and the ideas that prove worthwhile. Release checklists describe evidence for a release; they do not exhaust the product's ambition.

## What the listener has told us

The first melody was pleasant and listenable. After longer listening it became **too repetitive**. That is the most consequential product feedback so far: a station must sustain interest over hours, not merely produce one attractive short clip.

The listener also asked whether the music is generated live, wanted memory/system monitoring and recovery drills, and asked for continued implementation, PRs and CI-cleared merges. Reliability and musical development both belong in the product.

## What works today

- A local continuous MP3 station at `http://localhost:8000/radio.mp3`.
- Original seeded arrangements with several harmonic paths, variable chord holds, developed melodic phrases, changing texture and quieter openings/releases.
- A render-ahead queue, independent fallback music, crossfades, retries, cleanup and bounded retained audio.
- Decoded-audio supervision: it can detect persistent silent, missing or hung output and restart its owned Liquidsoap process within a rolling restart budget. Icecast outages allow native reconnection.
- Actual failure drills, a completed 30-minute test and a separate one-hour variety baseline. The hour contained 3,600 seconds of audio with no detected silence at −50 dB lasting at least two seconds; all 64 monitoring samples were healthy.
- Automated Python 3.11/3.14, rendering/streaming, browser and hardened HTTPS checks. PRs #1–#13 have merged after passing current-head CI.
- A local listening page with bounded reconnection, native fallback and an optional personal sleep timer.
- Recoverable musical chapters, verified backup/restore commands and an opt-in production deployment package.
- A public repository under the MIT software license. Bundled/installed third-party tools and the SoundFont retain their own licenses; attribution is in the README.

The stream is locally accessible, not a deployed public service. Objective audio analysis does not establish that the music is emotionally satisfying. Listening acceptance of the variety update is still open.

## Tonight's work — 15 November

### Recovery that an operator can repeat

The one-off backup/restore experiment worked. The new implementation provides `create`, `verify` and `restore` commands, with a consistent SQLite snapshot, completed audio, checksums and refusal to overwrite existing station data. A restore should carry the station to another machine, preserve its musical seed sequence, recover interrupted render jobs and replenish the queue.

The backup feature now has 16 tests; the full 58-test local suite passes. An actual read-only live-volume backup captured 43 jobs and 89 files (about 921 MB). An isolated restore dispatched valid two-minute audio and rendered a new 20-second segment in about 0.9 seconds while preserving job/seed continuity. Review also exposed a concurrent-restore race; an exclusive reservation and a failing-then-passing regression now protect the empty destination. Operator commands and off-host/fresh-volume instructions are included. Actual off-host storage and a recovery drill on the target VPS remain open.

### Completed: one hour with the watchdog deployed

The deployed watchdog configuration completed a fresh one-hour recording: exactly 3,600 seconds, no silence at −50 dB lasting at least two seconds, peak −7.99 dBFS and RMS −24.52 dBFS. All 114 samples were healthy. There were no container/recovery restarts, OOM kills or queue errors, and core container identities stayed unchanged.

Broadcaster memory ranged from 240.3–263.4 MiB; quarter-hour averages stayed near 243–245 MiB. After the run, SQLite integrity passed, 11 tracks were ready, temporary work was empty and the data volume used about 907 MB. The optional listener page was added and browser-tested during the run without recreating core services. Public-target soak and listening acceptance remain open.

### Built locally: an approachable listening experience

The first listener page now runs at `http://localhost:8080`: a quiet blue radio dial, an obvious play/pause control, volume and honest connection state. It opens no audio connection until you ask. Pause releases the stream; resume joins where the station is now. Network failures get three automatic reconnect attempts, then an explicit retry button. The page explains that new music is composed ahead of playback.

The page is static HTML/CSS/JavaScript with an optional non-root, read-only Caddy service. The proxy exposes the audio mount and page, with administration/status/data paths returning 404. It adds no account, external assets, analytics or Node server. JavaScript-disabled browsers get native audio controls.

Actual isolated Chrome tests have played and resumed the stream, adjusted volume by keyboard, recovered after a real failed media request, checked 390px/320px layouts and reduced motion, and verified the native fallback. Nineteen deterministic tests cover controller races, cancellation, bounded recovery and text contrast. Visual review led to darker secondary text to meet 4.5:1 contrast. Review found and fixed a native-pause-during-connection race; a real delayed-request browser test now proves it cancels automatic retries. Real mobile devices and public HTTPS still need validation. PR #9 merged after all four current-head checks passed, including real browser playback/recovery. It remains a local listening URL; public HTTPS still needs a target hostname.

![The local Generative Radio listening page](images/listener.png)

The product is now becoming a place to listen, rather than a stream address to copy. Next, the musical-memory and longer-arc experiments below should improve what it feels like to stay there.

### Next: an operable public station

Prepare HTTPS and a deployment/runbook with secure generated credentials, restricted administration, startup/reboot checks, monitoring, upgrades, backup and rollback. The actual VPS and hostname are still unspecified. I will prepare what can be tested locally without inventing a deployment target or silently purchasing infrastructure.

## Musical ideas worth developing

These are candidate experiments, in priority order. Their order may change when listening reveals something better.

### 1. Musical memory across segments

Today each segment has variation, but the station has little awareness of what it recently played. Track recent harmonic paths, phrase shapes, density and instrument combinations; discourage immediate repetition and schedule a change after an extended stable passage. The listener should hear continuity with occasional meaningful turns.

Test by rendering the same long session before and after, measuring repeated sequences and listening at transitions. Avoid turning anti-repetition into arbitrary novelty: repeated motifs can be comforting, and the point is development.

### 2. Longer musical arcs

Give the station a sense of chapters: an introduction, emergence of a motif, a more active middle, a retreat and a transition. Reuse a phrase in altered rhythm/register rather than constantly drawing unrelated notes. Let sections breathe; density and silence between notes are composition tools.

Keep a coherent tonal palette within an arc. Explore related modes or keys only when transitions are explicitly composed and listening supports them. A random key switch is not progress.

### 3. A more distinctive sound

Explore a few carefully chosen instrument combinations, register spacing, restrained ambience and evolving pad/bass balance. The current small General MIDI SoundFont is practical but places a ceiling on character. Compare legal, redistributable timbres or simple synthesis, measure CPU/render cost and check provenance before adopting assets.

Do not mistake more effects, more instruments or higher volume for richer music. Keep headroom and make every layer earn its place.

### 4. A station that can fit the moment

After the core music is convincing, try a small number of intentional energy profiles, such as focused and resting. Profiles would change density, pulse, brightness and development speed together. A gradual time-of-day arc could be useful, but should be optional and use a clearly chosen timezone.

Start with one coherent station before multiplying channels. Avoid genre labels that the output does not actually deliver.

### 5. Use the GPU where it earns its cost

Consider offline experiments in timbre or phrase generation, or musical similarity analysis to spot repetition. Compare results with the deterministic baseline on listening quality, latency, memory, licensing and reproducibility. Keep any model off the critical playback path until it proves useful and can fail without stopping the station.

The station does not need an AI badge. If rule-based composition sounds better for this purpose, keep it.

## How an iteration earns a place

For an audible change, retain reproducible seeds and make before/after renders long enough to expose repetition. Check duration, peaks, loudness, gaps and transition behavior, then listen. Explain what improved and what tradeoff appeared. Passing audio metrics is necessary evidence, not a substitute for taste.

For an operational change, reproduce the failure, verify recovery and preserve existing music/data. Ship cohesive PRs with concrete validation; merge only after current-head CI passes. Keep unfinished work in draft. Record real results here rather than rewriting proposals as accomplishments.

Useful listening questions: After twenty minutes, does the station still feel alive? Are changes welcome or distracting? Does a motif return with purpose? Would someone leave it on, and come back tomorrow?

## Open questions for future listening

- Does the current variety update solve enough of the repetition problem, or does the sound palette itself tire the ear?
- Is the station most compelling for focus, rest, active listening, or a deliberate combination?
- What should be recognizable about this station after hearing only thirty seconds?
- Which changes improve an hour of listening rather than a screenshot or a demo?

These are prompts for observation, not blockers to the work already underway.

## Evidence and continuation

Operational details and measured acceptance results live in [product-readiness.md](product-readiness.md), with implementation context in [HANDOFF.md](../HANDOFF.md). Local recordings, runtime logs and backup fixtures remain Git-ignored. This journal will gain dated entries as ideas are tested, shipped, revised or dropped.


## Iteration log

### 15 November: recovery tools landed; listening gets a front door

PR #8 merged verified backup/restore commands and the operator runbook after all current-head CI checks passed. An actual isolated recovery preserved 43 jobs/89 files, dispatched valid two-minute music and rendered the next segment in under a second. Off-host and target-VPS recovery still need real destinations.

The listener page landed in PR #9, including controller tests, browser checks and proxied-audio CI. The deployed watchdog completed its separate one-hour soak with all 114 samples healthy. No core service was recreated to add the page.

Compute check: the host can access an 8 GB RTX 3070 Ti. GPU experiments remain optional; the current station, player and recovery path remain CPU-only.


### 15 November: measure repetition, then give the music memory

A score-only sample of 256 consecutive seeds revealed that 54 of 255 adjacent pairs shared the same first four chords. The first melody note was A in 198 of 256 segments (77%). Only three first pitches appeared. These are structural measurements, not a listening verdict, but they explain why varied segments can still have familiar openings.

The next experiment is a deterministic session planner. Harmonic paths will be scheduled in shuffled groups that prevent immediate repetition at consecutive queue positions. Three-to-five-segment chapters will develop a shared motif, sound palette and register, with quieter arrival/departure and a more active middle. At the default two-minute segment length, a chapter spans roughly six to ten minutes.

I am choosing this over a generation model or a new history database: saved job seed/ID already give us a recoverable musical timeline. The planner can remain bounded, CPU-only and reproducible through cleanup, restart and backup restore. Queue position is not confirmed on-air history; failures/skipped jobs can skip parts of a chapter. Actual before/after renders, transition checks and listening will decide whether it earns its place. No musical-memory change is on air yet.


### 15 November: musical memory reaches the render bench

The session planner is implemented in the isolated worktree. It schedules different harmonic paths at consecutive queue positions, shares a motif/register/palette across three-to-five-segment chapters, and changes melodic density through arrival, development and release. Everything remains CPU-only. Saved seed/ID reconstruct the plan without a database migration; `MUSICAL_MEMORY=0` retains the legacy renderer behavior for rollback.

A repeat of the same score sample shows the structural change:

| Measure across 256 positions | Independent baseline | Planned candidate |
| --- | --- | --- |
| Adjacent equal four-chord openings | 54/255 | 0/255 |
| First melody note is A | 198/256 (77%) | 65/256 (25%) |
| Different first melody pitches | 3 | 8 |
| Melody attacks per two-minute segment | 36–48 | 26–48 |

These numbers describe the score. They do not establish that it feels less repetitive or more moving.

Actual FluidSynth/FFmpeg validation rendered all 15 palette/stage combinations at 20 seconds, plus twelve two-minute segments each for the baseline and candidate. Planned two-minute renders took 3.65–3.82 seconds here. Both 23m05s crossfade rehearsals have no detected -50 dB silence lasting two seconds; planned RMS was -24.30 dBFS and peak -7.78 dBFS, close to the comparison's listening level. An actual worker test preserved two saved job origins while its environment used a different station seed, and verified the legacy toggle.

The candidate has 74 backend tests, including bounded/out-of-order planning, no-repeat boundaries, safe notes/programs, legacy MIDI compatibility, preview validation and saved-job routing. Independent review found no defects, reran all 74 tests, confirmed 300 legacy MIDI comparisons against the base and checked 1,200 planned compositions across seeds/ages/durations/tempos. Current-head CI and a measured worker rollout come next. The live stream still contains the existing immutable buffer; no promise of improved listening quality is made before listening. Public HTTPS/target VPS work remains open.


### 15 November: musical chapters are on air; prepare a real deployment

PR #11 merged after all four current-head CI checks passed. Only the composer and
renderer were replaced at 04:54 IST; all eleven ready tracks kept their original
hashes. The broadcaster, Icecast and listener gateway stayed in place. Liquidsoap
actually crossed into the first planned segment (job182) at 05:19:43 IST. This is
on-air transition evidence, distinct from queue dispatch. A two-hour recording
and resource monitor are still running; their final result is not yet known.

The next product iteration packages a safe production installation: private
random credentials, resolved configuration checks, non-root/read-only services,
a persistent HTTPS gateway and an operator path for upgrades and recovery. It
uses the existing stack rather than adding a cloud dependency or control panel.
An isolated rehearsal is testing the actual five-container profile with local
certificates; no public deployment or host trust change is being made.

The rehearsal work also exposed a real transport defect: this FFmpeg build
accepted untrusted and wrong-host HTTPS certificates. The capture helper now
uses curl for CA/hostname authentication before decoding audio. Both rejection
cases and a trusted certificate pass in the real media image. Public DNS/ACME,
target-host reboot/capacity, off-host recovery and human listening remain open.


The production rehearsal completed successfully: all five services healthy under
UID10001/read-only/cap-drop/no-new-privileges, trusted HTTPS page and MP3, untrusted
CA rejection, canonical HTTP redirect, private routes returning404, a complete
five-second decoded TLS capture and the same CA after gateway replacement. Only
the disposable loopback project and its volumes were removed. Independent review
found two preflight bypasses via Compose configs/secrets mounts and alternate
networks; both now have failing-before/passing-after regressions and were rejected
through real Compose resolution. The actual media image passes94 Python tests;
listener tests pass19. This validates the package locally, not public deployment.

### 15 November: let listening end gently

PR #12 merged the production package after all four CI checks passed. CI also
caught a Compose-version difference: inherited security lists needed explicit
replacement. The fix passed a full local rehearsal with CI's exact Compose 5.1.3,
then the complete current-head pipeline. No public station has been deployed.

While the two-hour musical rollout recording continues, I am adding a small
listener feature for rest: an optional 15/30/60-minute sleep timer. It affects only
that browser, starts with explicit listening and keeps its deadline through
reconnects. Pause cancels it. The final 20 seconds fade where the device permits
volume control, then playback stops and releases the stream. Manual resume keeps
the listener's chosen volume and has no timer unless they choose one again.

The timer is implemented in an isolated worktree, not deployed yet. It has 30
passing listener tests and nine real-browser groups, including actual MP 3
playback/fade/expiry, changing volume during the fade, device-owned volume,
expiry during a failed-request retry and the existing mobile/native controls.
Screenshots retain the quiet page design at 390/320 px. No deadline is saved across
reloads. A suspended browser cannot run JavaScript: keep the page open, and do not
treat this as a device alarm. Independent review and current-head CI come next.


Independent timer review found and reproduced a transient-volume failure: one
throwing setter during a fade could leave manual playback attenuated afterward.
A bounded restoration attempt now recovers the chosen volume and slider when
control works again. A second regression keeps the expiry explanation visible
when returning to the page. Both failed before the fixes and pass afterward.
The full 94-test Python suite and 30 listener tests pass; nine actual browser groups
pass, including the injected transient fault. Physical-device testing remains open.

The original two-hour recorder terminated with signal 15 after about 90 minutes;
it is **not** a completed two-hour acceptance test. Its preserved decoded portion
contains 5,403.38 seconds, no detected -50 dB silence lasting 2 seconds, peak-7.37 dBFS
and RMS-24.62 dBFS. All 167 watchdog observations within that portion were healthy,
with no watchdog/container restarts or OOM events. The two intentional worker
replacements are distinguished from restarts. The WAV tail was interrupted, so
its final incomplete PCM frame and unfinalized header remain documented.

A fresh full two-hour capture began at 06:19:46 IST, using an immutable capture
script, a detached bounded supervisor and durable child/exit receipts. Audio and
vitals are confirmed arriving. This run contains planned music from its start.
No station process was restarted to replace the recorder. Its final result is
pending; source-stream continuity and recording-process lifetime are separate.

![The personal sleep timer, armed before listening](images/listener-timer.png)


### 15 November: the timer ships; compare the sound itself

PR #13 merged after all four current-head checks passed. The optional 15/30/60-minute
timer is deployed at the local listener. Only the gateway changed; all four music
service IDs/restart counts stayed unchanged. An actual browser decoded audio from
localhost:8080, armed without autoplay and cancelled/released correctly on pause.
Independent review's transient-volume and expiry-message regressions are fixed.

The next experiment isolates timbre from composition. A new offline listening
bench renders identical planned MIDI with several local SoundFonts, checks score
identity and generates a portable comparison page with MP3/WAV and measurements.
The final level matching only attenuates: a louder candidate cannot win by gain.
Outputs must be fresh and outside station data. Nothing changes the live sound.

The first real comparison is TimGM against FluidR3. FluidR3's upstream/debian
provenance identifies the font as MIT-licensed; its package and attribution stay
separate from our software license. The optional lab adds it only to an isolated
image. Its 148 MB file is much larger than TimGM's 6 MB, so render/memory cost matters.

Both libraries passed a 15-case palette/stage matrix and the same three-chapter
23m05s rehearsal. Both long masters measure −22.10 LUFS and have no detected silence
at −50 dB lasting two seconds. True peaks are −7.79 dBTP (TimGM) and −5.23 dBTP (FluidR3).
Single 120s render trials took 3.90/4.29 seconds, with kernel container-memory peaks
of 108.8/195.8 MiB under two-CPU/512 MiB limits. The larger library is computationally
feasible here; that does not establish that its tone is preferable or that a
small VPS can run the whole station with it. We now have concrete paired previews
to hear, not just a proposal to use a bigger asset.

The full new two-hour capture remains running under its bounded supervisor.
The earlier monitor completed normally; its interrupted recording is still only
90-minute partial evidence. New bench code has passed real-media identity/quality
checks; independent review and exact-head CI come next. The [audition runbook](sound-auditions.md)
explains reproduction, outputs, provenance and measured limits.

Independent review found no blocking findings in the listening bench. All106
Python/media tests and 30 listener tests pass. The exported page played the actual
MP3s in isolated Chrome, loaded no remote assets, stayed within390px and paused
the other variant when switching. The documented stopped-container export was
also exercised. Current-head CI and the PR merge are the remaining delivery steps.


### 15 November: verify what reaches the listener

PR #14 merged the sound comparison bench after all four current-head checks.
Matched 23-minute TimGM/FluidR3 previews are ready; listening preference remains
open and the current TimGM sound stays on air.

The next operational iteration closes a real verification gap. The public startup
probe accepted arbitrary bytes labelled audio/mpeg, including an encoded silent
MP3. Controlled private-TLS tests reproduced both false positives while valid
audio and certificate rejection controls behaved correctly.

The new read-only listener check fetches through authenticated HTTPS, bounds its
prefix/header storage, decodes locally and applies the watchdog's audibility
policy. Production startup reuses it. It can also run on a separate host and
report JSON/exit status without credentials, Docker access, restarting anything
or sending notifications. No monitoring host or destination is invented.

Testing exposed another boundary: old curl versions do not enforce max-filesize
on unknown-length streams. The actual station-image curl wrote 647,168 bytes during
a 262,144-byte-budget regression. A bounded application reader now enforces the
prefix limit and stops its owned downloader regardless of curl version. It also
handles the intentional end of a live sample instead of racing curl's time limit.

Header, body, local decode and cleanup remain bounded. Embedded playlists cannot
cause remote decoder fetches. The new full two-hour recording remains untouched;
public target/independent-host deployment still needs real destinations. Final
whole-branch review and current-head CI precede delivery of this iteration.


The full hardened local rehearsal passed the new audible check: three decoded
seconds at about −22.6 dBFS, with TLS trust, restricted routes and certificate
persistence still verified. Review caught a CLI argument-error path that bypassed
JSON and echoed input; it now returns bounded configuration JSON. A repeated
cancellation test exposed a process-startup race, addressed with cooperative
signal cancellation. Eight targeted cancellation runs passed after that fix.
The same live recorder has now passed its earlier 90-minute interruption point;
its full two-hour result is still pending.

After the review fixes, all 121 Python/media tests and 30 listener tests pass. The
standalone command's malformed-argument errors are JSON-safe, and normal help
still works. Current-head CI and merge are the remaining delivery steps; these
checks are not a claim of public deployment or a completed two-hour recording.


### 15 November: two hours of musical memory, measured end to end

The fresh long run completed: exactly two hours of decoded stereo audio, with no
−50 dB silence lasting two seconds and comfortable peak headroom (−6.82 dBFS).
All 226 audio-watchdog observations were healthy. No music-container restarts,
recovery restarts or OOM events occurred; the sleep-timer gateway deployment is
recorded separately. The planned ready queue stayed at 10–11 tracks. Broadcaster
quarter memory means stayed around 250 MiB; post-run SQLite and retention checks
passed with about 907 MB of data and no temporary render files.

The [readiness receipt](product-readiness.md#completed-two-hour-musical-memory-acceptance--15-november-2026)
records exact measurements and limitations. The earlier interrupted 90-minute
recording is still partial evidence, not silently relabelled as a success. The
current handoff now describes the running product rather than the first laptop's
unbuilt prototype.

PR #15 also shipped after all four current-head checks passed. We can now verify
that authenticated HTTPS delivers audible decoded music, rather than trusting a
successful HTTP response. This remains an operator command until an independent
monitoring host is chosen.

The next product decision is musical: hear whether the longer chapters actually
feel less repetitive, and compare the matched TimGM/FluidR3 previews. More notes
or a larger SoundFont alone do not establish a better station. TimGM stays on air
while that preference is open. Potential next experiments are broader harmonic
movement and more deliberate arrivals/rests within a chapter, measured against
the existing same-seed recordings. These are ideas, not shipped behavior or an
assumption that listening acceptance has passed. Public deployment and off-host
recovery also need their real destinations before they can be exercised.
