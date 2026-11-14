# Supervise the broadcaster and detect silent output

Status: proposed; awaiting user design approval.

## Intent

The product must run unattended. Compose currently restarts exited containers,
but the broadcaster health check only observes an Icecast mount. A hung
Liquidsoap process or a connected source emitting silence can remain unhealthy
indefinitely. Recover these cases without giving an application the Docker socket
or restarting the entire station.

## Approaches

- An external container or host controller can restart services, but needs host
  Docker privileges and broader recovery authority.
- A non-root supervisor inside the broadcaster can monitor decoded audio and
  restart only its Liquidsoap child. This is the recommended approach: the
  existing queue, Icecast and workers keep running during recovery.

This is a small, focused addition to the existing broadcaster container. It does
not introduce a fifth long-running container or a new runtime dependency.

## Proposed behavior

- The broadcaster command runs a Python supervisor which starts Liquidsoap as a
  child process, forwards termination signals, and reaps the child on shutdown.
  Probes and restart waits must be interruptible; shutdown must not leave orphan
  processes. Use the existing Python standard library and installed FFmpeg.
- After a 90-second startup grace, periodically decode 12 seconds from the actual
  internal Icecast MP3 mount. Bound each probe with network/subprocess timeouts;
  downsample to mono 8 kHz PCM16 to keep memory and CPU overhead small.
- Treat undecodable, missing, stalled, or continuously silent audio as unhealthy.
  Silence means all measured audio windows remain below -50 dBFS for the sample.
  Ordinary short fades or pauses must not trigger recovery.
- Require three consecutive failed probes before restarting a live Liquidsoap
  child; reset the count after a healthy probe. Check approximately every 30
  seconds. A missing/dead child should be restarted without waiting for three
  audio failures, using bounded backoff.
- If Icecast itself is unavailable, report that condition and allow Liquidsoap's
  existing reconnection behavior to recover. Do not repeatedly restart Liquidsoap
  for an unavailable server; once Icecast returns, resume decoded-audio checks.
- Limit automatic child restarts to three in a rolling 15-minute window. When the
  budget is exhausted, remain visibly unhealthy and wait for the window to allow
  another attempt. Shutdown remains responsive during this wait.
- Publish health based on recent successful audio probes and child liveness,
  rather than mount presence alone. A stale or missing monitor report must fail
  health checks. Health state must be written atomically and stay bounded in size.
- Log the probe failure reason, recovery attempt, suppressed restart/cooldown,
  and successful recovery. Reuse Docker's existing rotating logs.

## Boundaries and rollout

Preserve CPU-only rendering, the non-root user, existing audio volume, queue,
crossfades and four service roles. Do not expose a new port, mount the Docker
socket, delete buffered tracks, restart workers, or add public administration.
The monitor checks the internal stream; public DNS/HTTPS availability still needs
separate deployment monitoring. It cannot repair a failed VPS or host kernel.

Validate first in a separate Compose project/data volume on another localhost
port. Test healthy music, ordinary fades, silent audio, a stalled probe, absent
mount, child crash/hang, unavailable/restored Icecast, restart-rate limiting and
termination. Re-run the full suite and render/decode an integration sample. After
review, update the live broadcaster alone and verify output, health and resource
use. Publish a PR with the test evidence and remaining deployment limitations.
