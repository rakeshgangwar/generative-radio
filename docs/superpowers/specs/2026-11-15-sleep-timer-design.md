# A timer for settling in

Standing creative implementation/PR/CI-merge authorization applies; no new design
approval is claimed. The station is explicitly intended for rest and sleep as
well as focus. An optional listener timer lets a person leave the station gently.

## Approach

Use the existing static JavaScript player. A small sleep-timer controller owns a
wall-clock deadline and a gain envelope. A native select offers Off /15 /30 /60
minutes under volume. A countdown is visible but does not announce each second.
A separate polite status announces arming, cancellation and expiry.

Alternatives considered: a hard stop alone is simpler but abrupt; server-side
scheduling would affect other listeners and require new infrastructure. Choose a
client-only deadline with a20-second linear fade where programmatic volume works,
and a reliable pause/release where device volume is controlled externally. No
backend, cookie, storage, account, new dependency or host trust change.

## Behavior

Default Off. Selecting a duration while idle arms it for the next explicit start;
selecting during active playback/connection starts from now. Connection retries,
buffering and temporary reconnects do not reset the deadline. Manual/native/media
session pause, terminal playback error, pagehide and disposal cancel it. Changing
the duration restarts it; Off restores the listener's chosen volume immediately.
It never starts/resumes audio or changes the station's broadcast.

The final20seconds reduce effective gain against the current requested volume;
volume changes during the fade retain their relative attenuation. Cancelling,
pausing or expiry restores the requested volume for the next explicit play. On
expiry, pause clears retries/releases src, the select returns Off and status says
“Timer ended. Rest well.” Explicit play after expiry has no timer. No automatic
resume and no persisted deadlines across reloads.

Use Date.now deadlines, not accumulated timer ticks, so delayed/background ticks
catch up. Refresh on visibilitychange. A frozen/suspended browser cannot execute
JavaScript; document that the timer runs while this page is allowed to run and
does not act as a device alarm. No exact background guarantee.

## Visual fit and acceptance

Keep the existing mist#d8e3ed /ink#17344b /slate#4a6275 /sea#275a7c palette and serif
headline/system control type. One quiet row: “Sleep timer [Off v]”, then optional
“Stops in14:59”. A small status/hint below explains local playback. Native keyboard
select, readable focus, no motion, no per-second screen-reader announcements.
Retain320px layout, visible main play button and no-JavaScript native fallback.

Deterministic fake-clock tests cover arming/no autoplay, wall-clock jumps,
cancellation/late callbacks, retries, supported options, final fade/user volume,
unsupported volume and disposal. Actual isolated Chrome tests play real MP3,
advance the page clock through fade/expiry, verify pause/src release, retry
cancellation and full-volume manual resume. Review screenshots at mobile/desktop.
Use one final independent whole-branch review, scoped PR and current-head CI.
Preserve live core/capture21660 and monitor84280; only deploy the listener after
merge, and keep core IDs unchanged. Human/device listening remains separate.
