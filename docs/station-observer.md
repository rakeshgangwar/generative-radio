# Record station vitals

From a Linux station host with Python 3.11+ and existing Docker CLI access:

```sh
mkdir -p artifacts
python -m radio.observer --expect-web --output artifacts/vitals-snapshot
python -m radio.observer --expect-web --duration 1800 --interval 30 \
  --max-samples 120 --output artifacts/vitals-half-hour
```

Use a new output directory each time. Its parent must already exist. Omit
`--expect-web` for the four-service core deployment. Set `--project NAME` when
Compose uses a project name other than `generative-radio`. The observer uses your
Docker context; host metrics always describe the machine running this command.
There is no new service, Docker socket mount, dashboard, or privileged container.

`summary.json` reports cumulative healthy/unknown/not_healthy sample counts and
running/complete/cancelled/failed state. `sample-0000.json` and the other fixed
slots retain only the most recent `--max-samples` observations; use their sequence
and timestamps to order them. Older failures remain in summary counts after their
samples rotate out. Files are atomically replaced; the new directory is private
(mode 0700). At most 4096 slots and one summary are retained, with at most one
32 KiB temporary JSON during a write. Copy evidence you want to retain elsewhere.
A running summary by itself does not prove that its process still exists.

An omitted duration makes one snapshot. Otherwise duration is 1..86400 seconds,
interval 1..600 seconds, and max-samples 1..4096. Reads are sequential and can take
several seconds; samples never overlap and there are no missed-interval bursts.
A slow final sample can finish after the requested window. Ctrl-C or SIGTERM stops
only the observer and its owned Docker CLI process groups, leaving partial evidence.
Exit 0 means completed with all samples healthy, 1 means some unknown/unhealthy
observations, 130 means cancellation, and 2 means invalid arguments or report I/O.

Each Docker read has a five-second deadline and a 64 KiB output cap. Inventory is
limited to 16 containers in the selected Compose project. Reports contain selected
service IDs, image IDs, state/health, starts, restart/OOM values, approximate memory,
CPU percentage and PIDs. Unknown means missing, malformed or unavailable evidence;
not_healthy means a required service is absent or a known unhealthy state was seen.
Known unhealthy evidence takes precedence if another measurement is unavailable.
Raw Docker diagnostics, environment and watchdog detail are never saved.

The broadcaster's existing decoded-audio report is copied as a small tar stream
and read in memory, without extracting files or running commands inside containers.
It must be fresh within 90 seconds. This is station-provided audio evidence, not a
new independent listener probe. The observer never restarts services, opens the
SQLite database, changes music, installs timers, sends alerts or creates a port.

Observer-host metrics cover Linux RAM available/total, swap, CPU/load and the report
filesystem's free/total bytes. A sample is not an atomic system snapshot. Docker
memory numbers are approximate CLI display values. Healthy samples do not prove
subjective music quality, absence of a future leak, public capacity, or off-host
recovery. Use [listener health](public-monitoring.md) for independent decoded probes.

Tests include synthetic malformed and unavailable Docker inputs, secret canaries,
real bounded child processes, and report rotation/cancellation. To run the optional
actual selected-template check against an already healthy five-role station:

```sh
RADIO_OBSERVER_LIVE_PROJECT=generative-radio \
  python -m unittest discover -s tests -p test_observer.py -v
```

That opt-in is read-only. Unit-test fixtures alone cannot validate Docker's Go
format templates; the first live run caught malformed template output, retained as
unknown-state evidence, and the actual regression was repeated after correction.
