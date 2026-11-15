import argparse
from dataclasses import replace
import json
import logging
import signal
import threading
import time

from .config import Config
from .arrangement import arrangement_for
from .render import render
from .store import Store
from .labels import annotated_request

log = logging.getLogger("radio")
stop = threading.Event()


def main():
    parser = argparse.ArgumentParser(description="Generative ambient radio")
    parser.add_argument("command", choices=["composer", "renderer", "next", "status", "health", "preview"])
    parser.add_argument("--role", choices=["composer", "renderer"])
    parser.add_argument("--seconds", type=int, default=120)
    seeds = parser.add_mutually_exclusive_group()
    seeds.add_argument("--seed", type=int, default=42, help="Individual preview seed")
    seeds.add_argument("--station-seed", type=int, help="Preview a planned station sequence")
    parser.add_argument("--position", type=int, help="Positive queue position for --station-seed")
    parser.add_argument('--annotate', action='store_true', help='Attach safe broadcast labels to next request')
    args = parser.parse_args()
    if args.annotate and args.command != 'next':
        parser.error('--annotate is for next only')
    planned = args.station_seed is not None or args.position is not None
    if planned and args.command != "preview":
        parser.error("--station-seed and --position are for preview only")
    if args.command == "preview":
        if not 20 <= args.seconds <= 1800:
            parser.error("preview --seconds must be between 20 and 1800")
        if (args.station_seed is None) != (args.position is None):
            parser.error("preview requires both --station-seed and --position")
        if args.position is not None and args.position < 1:
            parser.error("preview --position must be positive")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = Config.load()
    store = Store(config.data)
    if args.command == "next":
        if args.annotate:
            info = store.next_track_info()
            print(annotated_request(info['path'], info['analysis']) if info else '')
        else:
            print(store.next_track())
        return
    if args.command == "status":
        print(json.dumps(store.status(), indent=2))
        return
    if args.command == "health":
        age = store.status()["heartbeats"].get(args.role, float("inf"))
        raise SystemExit(0 if age < 450 else 1)
    if args.command == "preview":
        arrangement = arrangement_for(args.station_seed, args.position) if planned else None
        seed = args.station_seed + args.position if planned else args.seed
        stem = f"preview-{args.position}" if planned else "preview"
        path, metrics = render(config, seed, args.seconds, stem, arrangement=arrangement)
        print(json.dumps({"path": str(path), **metrics}, indent=2))
        return
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if args.command == "renderer":
        fallback = config.data / "audio" / "fallback.wav"
        if not fallback.exists():
            log.info("Preparing independent fallback")
            render(config, 101, 60, "fallback")
    while not stop.is_set():
        store.heartbeat(args.command)
        try:
            if args.command == "composer":
                store.cleanup()
                while not stop.is_set() and store.enqueue(config):
                    pass
            else:
                job = store.claim()
                if job:
                    try:
                        started = time.monotonic()
                        # A queued job retains its originating seed even if .env changes.
                        arrangement = (arrangement_for(job["seed"] - job["id"], job["id"])
                                       if config.musical_memory else None)
                        path, analysis = render(replace(config, bpm=job["bpm"]), job["seed"],
                                                job["seconds"], job["id"], arrangement=arrangement)
                        store.finish(job, path, analysis)
                        log.info("Rendered segment=%s seed=%s in %.1fs metrics=%s", job["id"], job["seed"], time.monotonic()-started, analysis)
                    except Exception as exc:
                        store.fail(job, exc)
                        log.exception("Render failed segment=%s", job["id"])
                    continue
        except Exception:
            log.exception("Service iteration failed; retrying")
        stop.wait(2)


if __name__ == "__main__":
    main()
