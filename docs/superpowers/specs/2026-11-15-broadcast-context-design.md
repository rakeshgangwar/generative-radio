# Broadcast chapter context

Engineering design under standing autonomous creative iteration/PR/CI-cleared merge
authority. Preserve the buffered CPU-only station and its existing five roles.

## Purpose and evidence

Make musical chapters legible to someone listening: a quiet sentence such as
“Chapter 78 is unfolding. Warm keys.” This describes the broadcast programme,
not the exact samples a buffered listener is hearing or confirmed play history.

An isolated installed Liquidsoap/Icecast probe already forwarded an annotated
request through a five-second crossfade. Icecast title became
`Generative Radio - Chapter 78 is unfolding. Warm keys.` Raw evidence is in
`artifacts/broadcast-context-recon-20261115/metadata-forwarding.json`.

Use existing track metadata, not a queue-state approximation. A custom Icecast
XSL endpoint selects only /radio.mp3's current title; Caddy proxies only that
public response. This avoids new services, shared private data mounts and work
in the main audio callback. The earlier idea of an on_track publisher/public
volume is superseded: installed on_track runs in the streaming thread, while
existing output metadata already provides the required signal.

## Backend interface

Add `Store.next_track_info() -> dict | None`, with `path` and raw `analysis` from
one dispatch transaction. Move the existing ready-selection/missing-file/served
logic there unchanged. Legacy `next_track() -> str` wraps it and keeps empty-string
and canonical data/audio/<id>.wav behavior. No schema or PCM/MIDI changes.

New pure helpers in radio/labels.py:
- `title_for_analysis(analysis: str | None) -> str`.
- `annotated_request(path: str, analysis: str | None) -> str`.

Parse at most 8192 characters of analysis. Valid version1/2, positive integer
chapter (not bool, <=2**63-1) and known stage yield these sentences:
arrival “Chapter N is beginning.”; unfold “Chapter N is unfolding.”;
bloom “Chapter N is in bloom.”; settle “Chapter N is settling.”;
release “Chapter N is closing.” Append “ Warm keys.” for (89,32,4),
“ Halo keys.” for (94,32,4), “ Soft bells.” for (89,32,11).
Unknown palette omits its sentence. Invalid/legacy metadata yields
“Original ambient music.” Never copy arbitrary analysis text into public labels.

Annotation uses quoted/escaped title and fixed artist “Generative Radio”, followed
by the absolute audio path. Reject control characters or nonabsolute paths.
Only `radio next --annotate` selects annotation; plain next stays compatible and
the flag is rejected for other commands before loading data. The Liquidsoap
request callback uses it. Label cached fallback “A quiet interlude.” with the same artist using metadata.map
over its original single-file source. Annotated single URIs are fallible in2.1;
preserve the cached fallback's infallibility and prevent stale chapter labels.

## Public response

Ship deploy/broadcast-context-json.xsl into /usr/share/icecast2/web in the image.
Import the installed xml2json.xslt escape-string template; do not vendor it.
Select `/icestats/source[@mount='/radio.mp3'][1]` only. Emit exactly
`{"version":1,"available":true,"title":"..."}` when a nonblank title exists,
otherwise available=false/title="". Limit title to160 Unicode characters before
escaping. No listener counts, source IPs, paths, seeds, credentials or other mounts.

Caddy GET/HEAD /broadcast.json rewrites to that single private XSL path, sets
application/json and Cache-Control:no-store. Existing public admin/status/data
paths remain blocked. It is not an audio-health endpoint or sample alignment API.
No new volume, port, service or production privilege is needed.

## Listener behavior and visual design

Add web/public/broadcast-context.js with
`createBroadcastContext({fetcher,now,schedule,cancel,onChange})`, returning
`setEnabled(bool)` and `dispose()`. Defaults use native fetch, monotonic performance
clock and timers. Fetch only while the player is actually playing and document
visible. At most one current request, at least10000ms between starts (including
rapid pause/resume), a3000ms deadline and4096-byte streamed body limit. Validate
version/type/160-codepoint title bounds; unavailable/invalid/error hides context.
Strip only exact “Generative Radio - ” prefix for display. Render with textContent.

Pause, hidden, error, pagehide abort owned work, hide details and invalidate late
results. Resume/visibility refresh honors cooldown. BFCache pagehide is disable,
not permanent dispose. A response older than15000ms is not displayed when work
resumes. Metadata failure never pauses audio, retries playback or changes volume,
sleep timer or MediaSession's generic station identity. No autoplay/network work
before actual playback; no external assets or analytics.

Preserve existing mist #d8e3ed, ink #17344b, slate #4a6275, pale #c4d3e0,
sea #275a7c and paper #f6f9fb. Preserve system body and Palatino heading families.
Use a left-aligned sentence beneath playback status, followed by a small note:
“From the broadcast. Your audio may be a little behind.” No card, badge,
progress bar, extra animation or automatic screen-reader announcement.

Sketch (chosen over a separate footer panel, which would detach context):
Start listening / Pause       Live stream
Playback status
Chapter 78 is unfolding. Warm keys.
From the broadcast. Your audio may be a little behind.
Volume ...
Sleep timer ...

This is a musical programme sentence, not generic dashboard chrome. Keep it hidden
when no valid context exists; preserve keyboard flow, 320/390px fit and no-JS audio.

## Verification and delivery

Test default dispatch compatibility, malformed/large analysis, safe annotation and
stage/palette copies. Actual Liquidsoap/Icecast tests must show a prefetched job
can be marked served while the public label still belongs to the current output,
then changes on the subsequent output transition. Test fallback, missing mount,
quote/backslash/control/Unicode escaping,160-char bounds and other-mount exclusion.
Test browser request lifecycle/cancellation/cooldown/body bounds, optional failure,
XSS-as-text, timer/playback independence and real mobile/desktop screenshots.

Run full media/listener/browser/hardened-TLS checks. One independent final review,
real final-head/current-base CI and scoped PR precede merge. Develop in isolated
stack/images/volumes; keep main stream unchanged during development. Any later
broadcaster/Icecast/gateway rollout is a measured maintenance step with queue
preservation and reconnection checks, not an automatic full-stack recreation.
Public target/off-host/physical-device/listening acceptance remain separate gates.
