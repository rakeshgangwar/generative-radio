# Repeatable stock Firefox playback check

The exploratory stock Firefox 157.0.1 check passed five actual playback flows.
Make this repeatable and require it in CI without changing the music/player.

## Approach

Playwright's patched Firefox would share our existing test API but would not test
the installed branded browser. Selenium adds a client dependency for a small flow.
Choose Mozilla GeckoDriver's W3C HTTP interface with the Python standard library,
using the installed Firefox and a newly owned profile. This author choice follows
the user's autonomous/native iteration preference; no new approval gate.
Official references: https://playwright.dev/docs/browsers and
https://firefox-source-docs.mozilla.org/testing/geckodriver/Flags.html .

## Contract

`python -m radio.firefox_smoke --driver PATH --firefox PATH --output NEW_DIRECTORY
[--url http://127.0.0.1:8080/] [--timeout 120]` is a finite Linux-only acceptance
tool, not a background monitor. Timeout is finite 1..300 seconds. Require executable
files, a fresh private 0700 output directory with an existing parent, outside any
ancestor containing radio.sqlite. Never install/download software, use an existing
profile/session, call station admin APIs, or control station processes.

Allow only HTTP loopback roots (127.0.0.1, ::1, localhost), with no credentials,
query or fragment. WebDriver binds only 127.0.0.1 on a newly selected ephemeral
port. Use a profile root owned by this run. Never enable connect-existing or system
access; explicitly disable insecure certificate acceptance. Verify navigation did
not leave the selected origin before any clicks. No proxy environment routing.

Perform five actual flows: fresh idle with no stream source; trusted button click
leading to playing and MP3 currentTime >1; keyboard slider adjustment changes the
native audio volume; pause releases src and pauses audio; resume plays and advances.
Record only known check names and selected browser version/platform, not raw
capabilities, protocol error text, DOM content or browser logs. On failure permit
allowlisted last-known media state/readiness/volume/time and numeric error codes
collected during polling; capture numeric errors before normal recovery clears src.
Do not issue diagnostic requests after the deadline. Session creation may use the
configured overall budget instead of an independent short transport cutoff. Capture one bounded
PNG during playback and SHA256 of the eight known served public assets. These hashes
identify tested bytes; do not claim they match a checkout unless checked separately.

Browser/network work has a POSIX wall-clock deadline (including slow/dripping HTTP)
and cancellable SIGINT/SIGTERM. Bound each HTTP response to 1 MiB, assets to 256 KiB,
JSON report to 32 KiB. Driver stdout/stderr are discarded. On every outcome reap the
owned driver process group, terminate surviving group children and remove only the
owned profile root. Shutdown waits and profile deletion follow the deadline; elapsed
time includes cleanup. No network cleanup after deadline/cancellation. Save
an atomic result.json with complete/failed/cancelled state, pass flag, elapsed time,
completed checks and fixed failure kind/stage; partial checks never imply pass.
Exit 0 only on full success, 1 on failed check/deadline, 130 on cancellation, 2 on
invalid options/output/report I/O. A report alone is not proof of process liveness.

CI uses its installed Firefox/GeckoDriver inside the existing audio integration
job, retains the four required job names, and requires the new step's actual
success before merge. Existing Chromium coverage stays. This basic Linux headless
check does not cover Firefox's long-outage/sleep-timer behavior, Safari, physical
mobile devices, perceived audibility or subjective musical acceptance.
