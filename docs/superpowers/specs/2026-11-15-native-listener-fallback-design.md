# Native listener fallback

## Problem and product direction

The station should remain easy to join when optional page code fails. Today native
controls exist only inside noscript. With JavaScript enabled, failure of app.js or
any imported module leaves both players unavailable, although the footer stream
link remains. Slow script delivery can also arrive after someone starts native
playback. Preserve that listening session rather than replacing its connection.

The user authorized autonomous iteration and opted out of repeated design approval.
This is an author-selected recovery improvement using the existing static HTML/JS.

## Design

Render one visible, labelled native fallback audio element in ordinary HTML with
controls, preload=none, src=/radio.mp3, no autoplay, and a direct stream link. Keep
the existing enhanced #stream element separate, initially source-free, with custom
controls hidden. Remove the duplicate noscript-only player.

Run optional app initialization inside a function. Before binding the enhanced
player, inspect the native element: if it is unpaused or has played ranges, retain
the native player for this page visit and do not initialize a second player. This
covers pending playback and a previously started then paused listener. Otherwise
prepare all existing enhanced controls, timer, media-session and lifecycle binding.
Only after successful initialization, release the unstarted native source, hide
the fallback and reveal enhanced controls. A module-load failure or initialization
exception before that commit leaves the independent native player available.
A native session that has started is not silently enhanced later; reload can opt
into the usual enhanced player. Native mode uses browser controls and has no custom
sleep timer, chapter polling or app reconnection. Explain that honestly in the page.

## Invariants

- Keep static HTML/CSS/JavaScript, existing Caddy proxy and local-only deployment.
- No autoplay or MP3 request before explicit user playback in either mode.
- Never stop/reload/replace an already started native session on late enhancement.
- Exactly one usable player; enhanced mode releases the unused native source.
- Keep enhanced recovery, timer, volume, chapter context and pause/source release.
- Native playback must work when app.js fails, an imported module fails, or JS is off.
- No external assets, accounts, storage or new runtime dependencies.
- No station role replacement until verified web-only rollout with identity receipts.

## Mixed-version compatibility and review decisions

The actual previous deployed HTML (main5ab28f9) has no native-stream element.
The new app must initialize its enhanced player on that HTML without dereferencing
missing native markup; guard both ownership checking and native cleanup. The
regression fixture is byte-identical to the previous index.html and must exercise
real playback and pause/source release with candidate scripts.

The sole fresh review deferred two Minor items: moving keyboard focus from an idle
native element when it becomes hidden, and fuller on-page explanation of native
limitations/reload. Tab currently reaches enhanced play; README explains native
limitations. Costs: one interrupted keyboard interaction and reduced discoverability.
These are explicit deferred improvements, including the design-copy shortfall.

## Acceptance and limits

Real Chromium blocked-app and blocked-import flows must play advancing MP3 through
trusted native controls. A delayed app response must preserve a real native session,
its source, advancing clock and request count, including after an earlier native
pause. Normal enhancement must have no pre-click audio request and one active source.
The existing full browser suite plus stock Firefox five-flow check must pass; verify
native keyboard playback in actual Firefox separately. Check 320px layout and no-JS
native controls. Physical devices, Safari, public hosting and human musical taste
remain explicit open gates. One final fresh reviewer, one author fix pass for
Important/Critical findings, defer Minor findings with their costs.
