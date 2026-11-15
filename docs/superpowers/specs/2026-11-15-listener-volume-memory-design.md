# Remember full-player volume

## Product intent

A listener who chooses a quiet level should return to that level after refresh,
without starting music automatically. Today the full player always resets to 65%.
The journal proposed volume memory; the user authorized autonomous product iteration
and opted out of repeated design approval. Use the existing static browser stack.

## Behavior and storage contract

After the native-session ownership guard, read one optional localStorage preference
before initializing requestedVolume. Key: `generative-radio.volume.v1`. Value:
canonical decimal integer string `0` to `100`, at most three characters, equal to `String(Number(value))`.
No leading zeros, whitespace, fractions, signs, exponents or arbitrary JSON. Invalid
or absent values keep the existing 65% HTML default. Accessor/read failures do the
same. Never display or log raw stored values/errors, clear unrelated storage or
write a preference just because a page loaded.

Persist only explicit range-input choices, using requested unfaded percent, never
audio.volume or sleep fade gain. Optional writes may fail; current control/audio
updates must still work. Where programmatic volume control works, a valid saved `0` remains muted and
`100` remains full scale; the readout/accessibility text agrees with the range. Programmatic-volume
unsupported devices keep their existing device-button fallback; do not overwrite
stored preference during capability checks. Native basic mode remains browser-managed.

Read once per full-player initialization. No storage-event live synchronization:
another tab's change affects a later refresh, not an already playing tab. Store no
playback intent, timer, identity, history or server/account state. Play remains
manual; the sleep timer resets on refresh. Started native sessions still return
before enhancement/pref access, preserving source, focus and browser controls.

## Implementation choice and constraints

Keep the small preference boundary in app.js; no new module/dependency/server/UI
settings panel. Catch optional storage access in initialization and explicit input
persistence. Existing player/timer/context APIs and eight-asset delivery manifest
stay unchanged. Keep native failover, legacy HTML, focus ownership, bounded retries
and hardware-volume behavior. Candidate remains isolated with explicit project
labels; core/music stay version 2 TimGM. A web-only rollout needs real CI and measured
core preservation, with maintenance annotated in the running six-hour observation.

## Reviewed capability correction

A saved maximum must not mistake an ignored setter/current getter of1 for working
volume control. Before any enhanced playback, use a distinguishable property
probe and restore the requested level without writing preferences. Retain evidence
of a successful distinct write separately from the last write outcome, so existing
transient mid-fade recovery still works. Matching an unchanged level alone cannot
establish capability. Never perform a distinguishable probe on active audio; native
ownership returns before this path. A failed initial probe at an unchanged maximum
can conservatively retain device fallback until refresh or a proven distinct write.

The sole review deferred a separate getItem-method-throws fixture as Minor. Its
call is already inside the read try/catch; residual cost is absent direct coverage.

## Acceptance

Real browser RED must show a chosen level resetting after reload, then GREEN with
valid zero/quiet/maximum preferences restored and no autoplay or restored timer. Invalid
canonical values and simulated denied reads/quota writes degrade without blocking
controls. Verify fading preserves requested preference, another tab cannot jump
live volume, and the hardware fallback retains saved data without claiming applied
volume. Existing full browser/native/focus/legacy flows and actual Firefox playback
must pass. Review a narrow viewport/readout. One fresh final whole-branch review,
one author Important/Critical correction pass, Minor defer with costs. Four actual
latest final-head/current-base CI jobs including real Firefox success are required.
Public/offhost/device/Safari/AT/human musical acceptance remain open; storage/error
fixtures are simulations, not proof of all private-browsing/device combinations.
