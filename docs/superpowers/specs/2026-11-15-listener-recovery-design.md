# Listener recovery across a short station interruption

Standing autonomous iteration authority applies; brainstorming questions/design
approval were previously opted out. Keep main music running during development.

The chapter feature is merged/deployed at ab7b601. Its three streaming roles were
replaced while both music workers and all eleven ready-file hashes were preserved.
Fresh Chromium playback/context passes. A previously connected maintenance observer
failed to return to playing after service restoration. It did not save state samples
on failure, so it cannot prove its exact final player state. Current code has only
1/3/8-second backoffs: immediate failures exhaust it in twelve seconds, while
transport replacement alone took about twenty-nine seconds.

Reproduce that boundary with deterministic media faults and actual Chromium requests
failing for thirty seconds before forwarding to the real stream. The existing policy
must fail the new acceptance before changing it. Preserve diagnostic state/request
timestamps even on failed acceptance.

Extend the fixed retry schedule to 1/3/8/15/15/15 seconds. This covers a thirty-second
immediate-failure outage and caps wait between attempts at fifteen seconds. Six
retries remain finite:57 seconds of scheduled backoff plus at most seven15-second
connection deadlines (162 seconds in the all-hung case). Thirty seconds of stable
playback still resets the budget; brief playing/drop loops do not. No unbounded
polling, online-event listeners, settings or backend changes. An exhausted budget
still requires explicit Try again. Browser permission rejection still requires a
gesture. Pause, disposal and sleep-timer expiry cancel all owned work.

Keep initial user-intent gating, actual playing events, source generation guards,
volume, metadata controller and sleep-timer behavior unchanged. No new UI design
is needed: existing attempt text derives its maximum from the schedule.

Verify deterministic thirty-second recovery, finite hanging/drop-loop exhaustion,
late cancellation, all listener tests and real-browser thirty-second request failure
then advancing real MP3 and an armed sleep timer. CI retains the full media/browser/
hardened TLS checks. One fresh whole-branch review and real final-head/current-base
CI precede merge. Only the web gateway needs a later targeted rollout.

Document the completed chapter rollout and its failed maintenance auto-resume
separately from the new controlled-fault recovery proof. Neither proves gap-free
playback, physical-device acceptance or human musical quality. Public hosting and
actual off-host recovery still require destinations.
