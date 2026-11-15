# Native listener focus and help

The native-first listener is deployed after PR28. Its sole review left two Minor
usability issues: delayed enhancement hides the focused idle native audio control,
and the basic-mode page does not explain missing features or how to retry full UI.
The user authorizes autonomous iteration and opted out of repeated design approval.

When an unstarted native fallback is successfully replaced, remember whether the
current focus is inside that fallback. After hiding fallback and revealing enhanced
controls, move that focus to the Start listening button with preventScroll. Do not
move focus if it belongs elsewhere. Preserve started native sessions, including
paused and pending play, before any handoff; their focus/source stay native. The
legacy HTML path without native markup remains valid and never steals focus.

In the visible native fallback, say that the sleep timer, station details and
application reconnection are unavailable, and reloading can try the full player.
Keep a direct audio-stream link. Do not promise reload succeeds or imply native
browser controls provide the custom timer/retries. Existing layout/visual style
and ordinary HTML fallback remain; show the help only while that mode is visible.

Invariants: static stack/no dependencies; no autoplay or pre-click stream request;
never replace started native playback; preserve unrelated keyboard focus; keep old
HTML/new-script compatibility; keep enhanced timer/retry/volume behavior. No music
or core role change. Only verified web-only deployment after PR/actual CI clearance.

Acceptance: actual delayed-module keyboard regression fails before correction;
focused native control hands off to visible enhanced play and Space starts one real
advancing stream, no pre-click request. Unrelated link focus stays put. Existing
native playing/paused/pending preservation and all prior browser scenarios pass.
Review native help at320px and check exact served assets, stockFirefox flows and
native playback. One fresh final review; one author Important/Critical correction
pass, Minor findings deferred with costs. Physical/Safari/public/offhost/human
acceptance stay open. Include the measured PR28 delivery receipt and current journal.
