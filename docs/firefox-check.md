# Check stock Firefox playback

Use an installed Linux Firefox and a trusted Mozilla GeckoDriver. The tool does
not download them, install a service, or attach to an existing browser profile.
Mozilla publishes compatibility information and driver releases:
[GeckoDriver support](https://firefox-source-docs.mozilla.org/testing/geckodriver/Support.html).
Playwright's Firefox needs its own patched build, so this check uses the W3C
interface to test the installed branded browser instead.

```sh
mkdir -p artifacts
python -m radio.firefox_smoke \
  --driver /path/to/geckodriver --firefox /path/to/firefox \
  --output artifacts/firefox-check
```

The default target is http://127.0.0.1:8080/. `--url` accepts only HTTP loopback
roots without credentials, query or fragment. The browser navigation must stay on
that origin before controls are clicked. This local check does not test public
DNS, TLS or an independent listening path; see [public monitoring](public-monitoring.md)
for that separate probe.

The five actual flows are idle without a media source, manual start with advancing
MP3, keyboard volume adjustment of the native audio element, pause releasing the
source, and resume advancing playback. Success writes `result.json`, a playback
PNG and hashes of eight known public assets. Hashes identify the delivered bytes;
compare them to a checkout separately before claiming that checkout was served.
Browser name/version/platform are recorded; raw capabilities, browser logs and
remote error messages are discarded. Failure reports retain fixed kinds/stages and
only allowlisted last-known media state: readiness/network codes, paused/time,
volume values and numeric media errors. An error listener records the numeric code
before normal recovery clears the source. There are no diagnostic requests after
the deadline; these fields come from already completed polls.

Output must be a new private directory (0700) with an existing parent, outside
station-data ancestors containing radio.sqlite. `--timeout` defaults to 120 seconds
and accepts 1..300. Session creation can use that overall budget rather than a
separate short transport cutoff. The POSIX deadline bounds browser/network work, including
stalled/dripping responses; response bodies are capped at 1 MiB and asset bodies
at 256 KiB. The JSON report is capped at 32 KiB. SIGINT/SIGTERM preserve a cancelled
receipt, terminate/reap the owned driver process group and remove its private
profile root. Existing profiles and station processes are never controlled. Shutdown waits and
profile deletion follow the deadline, so elapsed time includes cleanup. Signals
received during driver acquisition are honored as soon as its process handle is
registered, ensuring cancellation cannot lose ownership of an already started child.
Hard process/host termination cannot provide a graceful receipt; a `running`
result by itself proves no liveness.

Exit 0 means all five checks and cleanup succeeded; 1 means a failed check/deadline,
130 cancellation, and 2 invalid options or report I/O. Partial checks never mean
success. Driver/profile cleanup is performed on handled failure too. Reports and
the screenshot stay local and Git-ignored. New runs need new output paths.

The current Ubuntu GitHub runner provides Firefox and GeckoDriver; the existing
integration job now invokes this exact tool and requires its actual success while
retaining Chromium's larger scenario suite. Browser versions are recorded each
run, rather than assuming the runner's versions remain fixed. The CI runner also
prepares FFmpeg and a virtual PulseAudio sink for headless browser playback. This
is test infrastructure, not a new station service or a bypass of MP3 progress.
Startup/failure diagnostics run only after a failed acceptance check. An absent binary or
failed Firefox flow fails CI; it is not silently skipped.

The first exploratory Firefox 157.0.1 check passed the five flows. The tracked
version then passed again with the installed /usr/bin/firefox wrapper, recorded
actual MP3 progress, removed its profile and closed its driver port. A real short
deadline also checks process cleanup separately. These are Linux headless results,
not physical-device, Safari, long-outage/sleep-timer Firefox coverage, perceived
audibility or human musical acceptance. The station remains on version 2 TimGM.
