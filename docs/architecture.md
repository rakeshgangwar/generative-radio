# MVP architecture decisions

The shared conversation selects one software-only ambient station with Python,
FluidSynth, Liquidsoap, Icecast and Docker Compose. It prioritizes coherence,
buffered generation and recovery before management UI, additional genres or AI.

Three independent roles share a local SQLite WAL queue and audio volume. The
streaming server is a fourth container. SQLite avoids adding PostgreSQL before
there is a multi-user management API. No remote service is needed to schedule or
render music. Files are visible to playback only after audio validation and atomic
rename. Completed dispatches are retained long enough for Liquidsoap prefetch.

FluidSynth uses fast file rendering rather than a sound device. FFmpeg applies
loudness control and boundary fades; Liquidsoap supplies five-second crossfades
and an infallible local fallback. The fallback shares the tonal centre of generated
music. The renderer creates it before broadcaster startup, and it survives process
restarts in the data volume.

Current limits: dispatch is at-most-once, not confirmed playback; no live control
panel, multi-station scheduling, exact on-air history, hardware FM-1 integration,
AI generation, or silence-triggered broadcaster restart. Initial accepted behavior
must include a 30-minute recorded broadcast and human listening review. Production
also needs a longer soak, backup/restore practice and external stream monitoring.

Technical references:

- https://www.fluidsynth.org/wiki/UserManual/
- https://www.liquidsoap.info/doc-2.1.4/quick_start.html
- https://www.icecast.org/docs/icecast-latest/config-file.html
