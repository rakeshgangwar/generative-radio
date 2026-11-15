# MVP architecture decisions

The shared conversation selects one software-only ambient station with Python,
FluidSynth, Liquidsoap, Icecast and Docker Compose. It prioritizes coherence,
buffered generation and recovery before management UI, additional genres or AI.

Three independent roles share a local SQLite WAL queue and audio volume. The
streaming server is a fourth core container. An optional non-root/read-only Caddy
service serves the listener page and proxies only the audio mount. SQLite avoids adding PostgreSQL before
there is a multi-user management API. No remote service is needed to schedule or
render music. Files are visible to playback only after audio validation and atomic
rename. Completed dispatches are retained long enough for Liquidsoap prefetch.

FluidSynth uses fast file rendering rather than a sound device. FFmpeg applies
loudness control and boundary fades; Liquidsoap supplies five-second crossfades
and an infallible local fallback. The fallback shares the tonal centre of generated
music. The renderer creates it before broadcaster startup, and it survives process
restarts in the data volume.

Musical context is reconstructed in the renderer from each saved job's seed and
queue ID. Bounded shuffled schedules avoid equal harmonic paths at consecutive
positions; three-to-five-segment chapters share a motif, register and palette.
Version-2 plans also share a 6/8/10-bar melodic phrase length within each chapter.
The final bar of each phrase has no new melody attacks or held MIDI notes,
while sustained harmony continues. SoundFont releases/reverb can ring through it. Version-1 plans and unplanned legacy MIDI remain unchanged.
The versioned arrangement is saved in render analysis. This requires no history
database/migration; legacy composition remains available through MUSICAL_MEMORY=0.
The schedule describes queue order. Skipped jobs can skip chapter stages.

The broadcaster's non-root supervisor owns Liquidsoap and probes decoded Icecast
audio with bounded subprocess deadlines. Consecutive failures trigger child
recovery within a rolling restart budget; unreachable Icecast permits native
reconnection. Fresh atomic PID/audio reports replace mount-only health checks.

Current limits: dispatch is at-most-once, not confirmed playback; no management
control panel, multi-station scheduling, exact on-air history, hardware FM-1
integration or model generation. Local recovery drills, 30-minute recording,
separate one-hour variety/watchdog runs and isolated backup/restore have passed.
Physical-device/public HTTPS/target-VPS capacity and subjective listening
acceptance remain open. Off-host/end-to-end monitoring and actual target recovery
still need deployment destinations. The product journal records the evolving
ambition beyond these release checks.

Technical references:

- https://www.fluidsynth.org/wiki/UserManual/
- https://www.liquidsoap.info/doc-2.1.4/quick_start.html
- https://www.icecast.org/docs/icecast-latest/config-file.html
