# Check the public listening path

An internal watchdog can hear Icecast while a public proxy, certificate or route
is broken. Run this read-only check from another Linux machine to sample the
same HTTPS origin listeners use. It requires Python 3.11+, curl and FFmpeg, with
a readable checkout of this repository. It needs no Docker access, station
credentials, SoundFont or data volume.

```sh
python3 -m radio.listener_health --url https://radio.your-owned-domain.tld
```

Replace the hostname with the actual station origin. HTTP, URL credentials,
queries, fragments and arbitrary paths are rejected. System CA/hostname validation
is mandatory; there is no insecure mode. An explicit private CA is supported for
local/private deployments without installing it in the system trust store:

```sh
python3 -m radio.listener_health --url https://localhost:18443 --ca-file /path/to/root.crt
```

A successful JSON result includes `healthy`, `page_verified`, `stream_verified`,
`decoded_seconds`, `rms_dbfs` and `elapsed_seconds`. Exit status is 0 for healthy,
1 for unhealthy and 130 for cancellation. Invalid configuration and network/tool
failures also return unhealthy JSON. The result does not contain response bodies
or URL credentials. SIGINT/SIGTERM request cooperative cancellation and reap owned curl/FFmpeg processes.
Argument errors also return safe JSON/exit 1; `--help` retains normal help/exit 0.

The default 20-second shared deadline covers both HTTPS requests and decoding;
`--timeout` accepts 1–60 seconds. It checks the branded 200 HTML page, stores and processes at
most 256 KiB of authenticated MP3 and decodes up to three seconds locally as 8kHz
mono PCM16. The existing watchdog's completeness and −50 dB audibility policy is
used; `rms_dbfs` is the strongest one-second window, not whole-recording loudness.
The working deadline is followed by at most one second of process-termination grace.
The application enforces 64KiB header and 256KiB stream-prefix limits rather than depending on curl's
version-specific unknown-length size behavior. FFmpeg is restricted to MP3 and
local file/pipe protocols, so the sample cannot instruct it to fetch a playlist.

This is a short sample, not proof of uninterrupted or musically satisfying audio.
Use repeated failures in your existing alerting before paging an operator. It
never restarts the station or sends an email/webhook. A local probe cannot prove
independent Internet reachability; the remote host and real public domain remain
required for that acceptance gate.

## Schedule on an independent host

Examples live in `deploy/monitoring/`. They are not installed or enabled by any
application command. Before installation, configure the service's actual URL,
checkout location/Python executable and an existing unprivileged monitor account.
The example `/opt/generative-radio` must be readable by that account. No private
`.env.production` belongs on the monitoring machine.

Copy the configured service/timer to the host's systemd unit directory, then:

```sh
sudo systemd-analyze verify /etc/systemd/system/generative-radio-listener-check.service /etc/systemd/system/generative-radio-listener-check.timer
sudo systemctl daemon-reload
sudo systemctl start generative-radio-listener-check.service
sudo systemctl status generative-radio-listener-check.service
sudo systemctl enable --now generative-radio-listener-check.timer
systemctl list-timers generative-radio-listener-check.timer
journalctl -u generative-radio-listener-check.service --since today
```

The timer runs about once a minute. The oneshot has an explicit 25-second start
limit and two-second stop limit; systemd controls the whole cgroup as an additional
cleanup boundary. It has a private temporary directory, read-only system/home
protection and no added privileges. Use `TimeoutStartSec` for a oneshot: systemd's
`RuntimeMaxSec` does not limit this service type. Integrate its exit state with
your own alerting and log retention; no notification destination is assumed.
To stop only the monitoring schedule, disable that timer.

The actual target/DNS, independent monitoring host and alert destination have not
been supplied. These templates and local TLS tests do not establish public
monitoring deployment or permission to provision infrastructure.

## Diagnosing failures

`tls` means certificate trust/hostname validation failed. `transport` or `timeout`
can indicate DNS, connectivity, headers or a stalled response. `response`/`page`
means the expected origin/routes were not served. `decode`, `incomplete` and
`silent` mean authenticated bytes did not yield a complete audible sample. Check
public DNS/TLS/proxy logs and the internal watchdog before choosing a recovery
step; network trouble alone does not justify restarting a healthy music source.

Production `up` uses the same audible check after container health, so a 200
`audio/mpeg` label or 4096 arbitrary bytes no longer imply verified playback.
The isolated production smoke uses an explicit local CA and asserts decoded
duration/RMS as well as the existing trust, route and certificate-persistence gates.
Actual junk, encoded silence, short MP3, certificate mismatch, hanging headers,
unknown-length body overflow and signal cancellation have regression coverage.

Primary references: [curl size-limit version semantics](https://curl.se/docs/manpage.html#--max-filesize),
[systemd service timeouts](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html),
[systemd timer semantics](https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html).
