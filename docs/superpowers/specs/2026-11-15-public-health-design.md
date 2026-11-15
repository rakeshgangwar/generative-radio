# Verify what the public listener can hear

The production startup probe currently accepts4096 bytes labelled audio/mpeg.
Real private-TLS regressions prove it accepts both junk and an encoded silent MP3.
Internal source health cannot establish that the public proxy/listening path is
serving audible audio. Standing autonomous implementation/PR/CI-merge applies.

## Approach

Add `radio.listener_health` as a read-only, standalone HTTPS check usable from
another machine. Reuse it from `production.probe_https`; preserve existing result
keys and ProductionError mapping. No credentials, Docker, database or restart
control. No installed schedule/notification/public deployment without a target.

Alternatives: reuse internal watchdog URLs, which require private Icecast status,
or rely on HTTP/byte counts, which the regression disproves. Choose a public-path
probe with strict curl CA/hostname authentication followed by local-only decode.

## Contract

CLI `python -m radio.listener_health --url https://owned-host --timeout 20`;
optional explicit `--ca-file` for a private CA, never an insecure mode.
Only a plain ASCII HTTPS origin: no credentials, query, fragment, arbitrary path,
control/space characters or invalid port. Validate before subprocesses.

One shared monotonic deadline (default20s, configurable1–60s) covers page fetch,
MP3 prefix fetch and decoding; owned-process termination has at most1s additional grace. Curl config disabled, proxies bypassed, HTTPS-only,
no redirect. Page must be200 text/html with station brand. Stream must be200
 audio/mpeg, body bounded256KiB and headers64KiB. Download cap/timeout codes are acceptable only
when a sufficient authenticated sample is present; all TLS/HTTP failures fail.
Each command has a phase cap and owned process group; terminate/reap on timeout,
SIGINT/SIGTERM or other exits. Metadata stdout is small; decoder stderr discarded.

Decode the bounded local file explicitly as MP3 with file/pipe protocols only;
never let FFmpeg open a remote URL or interpret an embedded playlist. Decode at
most3s of8kHz mono PCM16. Reuse watchdog assess_pcm completeness/-50dB audibility
policy. Return actual decoded duration, RMS, elapsed time and existing verified
flags only after success. Junk, incomplete media, silence and hangs are unhealthy.

CLI emits JSON, exit0 healthy,1 unhealthy,130 cancelled; --help is normal help/exit0. Error kinds/details are
bounded public diagnostics, never bodies or credentials. API raises a typed
ValueError subclass. Normal trust store by default; private CA never installed.
The production wrapper retains its exception type. Scheduled units are examples
for operators to install on a separate host; no automatic emails/webhooks/restarts.

## Evidence

Keep RED junk/silence regressions with trusted positive and untrusted/wrong-host
controls. Cover URL rejection before network, invalid budget, real header hang,
CLI JSON/signal cleanup and bounded output. Existing full hardened TLS smoke must
now report decoded seconds/RMS. One final independent review and exact-head CI.
Preserve live services and acceptance supervisor456169/children456184/456185.
