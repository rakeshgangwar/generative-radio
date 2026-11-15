# Station vitals recorder

The listener can leave the station playing, but our measured RAM and health receipts
currently depend on temporary scripts. Ship a repeatable Linux host command that
records the same kinds of evidence without modifying station processes or data.
The operator uses existing Python 3.11+ and Docker CLI access; no dependencies.

## Approach

An app dashboard would require exposing host information and Docker access to the
application. A full metrics service adds deployment and retention machinery before
we have a public host. Choose a host-side finite recorder: scoped Docker reads,
observer-host RAM/load/disk, and bounded private JSON evidence. This is an author
choice under the user's autonomous iteration instruction. No installation, alerts,
restart decisions, music changes, new ports, or off-host monitoring claims.

## Contract

`python -m radio.observer --output NEW_DIRECTORY [--project generative-radio]
[--expect-web] [--duration 1800 --interval 30 --max-samples 2048]`.
Duration defaults to zero (one sample), otherwise 1..86400 seconds; interval 1..600,
max-samples 1..4096. Values must be finite; project is a Docker-compatible lowercase
slug, at most 63 characters. Output must be new, mode 0700, outside any ancestor
containing radio.sqlite. Do not read the database. Samples replace fixed ring slots
atomically; summary records total/retained counts, failures and complete/cancelled
state, requested versus elapsed duration. A running summary alone proves no liveness.
SIGINT/SIGTERM cancel the observer's owned CLI children and preserve partial evidence.
No overlapping samples or catch-up bursts. A command has a 5-second deadline and
64 KiB stdout limit; discard stderr and never persist command errors verbatim.

Inventory only the named Compose project's containers, max 16. Require exactly one
composer, renderer, broadcaster, icecast, and optionally web. Read selected inspect
fields (ID/image ID, service, state/health, starts, restarts, OOM) and selected stats
(CPU, approximate memory bytes, PIDs). Do not serialize full inspect, environment,
labels, names or arbitrary output. Failed/malformed/missing measurements cannot
produce healthy assessment. Known unhealthy state takes precedence over unknown.
Read only broadcaster-health.json via bounded Docker cp tar stream, without exec
or extraction. Persist allowlisted health fields, never diagnostic detail. Its
updated_at must be finite and within 90 seconds of observer wall time; decoded
audio evidence is a report from the station, not a new independent audio probe.

Read Linux MemTotal/MemAvailable/SwapTotal/SwapFree, load and CPU count and disk
capacity for the report filesystem. Label these observer-host metrics: Docker may
use a remote context. Do not declare memory leaks absent or choose RAM thresholds.
Reports are sequential observations, not an atomic snapshot across services. Exit 0
only for completed all-healthy runs, 1 for unknown/unhealthy samples, 130 if cancelled.
Private reports remain local and ignored; docs describe actual proof and limitations.
