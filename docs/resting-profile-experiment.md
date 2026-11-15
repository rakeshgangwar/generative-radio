# Resting-profile experiment

Compare at [localhost:18095](http://localhost:18095). Pause the live station or other
audio first, then play one version at a time. The page pauses its other player
when you start one. Native controls also work without JavaScript; in that mode,
pause the other track yourself. Compare a few minutes and chapter transitions,
then return later for a longer listen.

Both versions cover the same three complete chapters (seed 42, positions 1–12),
last 23m05s and use the current TimGM SoundFont. The resting candidate uses 52 BPM
instead of 60, the existing spare density profile throughout, and one fixed warm
pad/acoustic-bass/electric-piano palette. Motif and harmonic sequence remain, while
the slower pulse changes note and chord timing. This is a mood comparison, not an
identical-note or phase-aligned A/B. It tests a deliberately calmer profile rather
than claiming that slower music fixes repetition.

Both measured masters are −22.13 LUFS. Only attenuation was used for matching;
true peaks are −8.39 dBFS (current) and −8.50 dBFS (resting). Neither had silence
at −50 dB lasting two seconds. In a separate 256-position score sample, mean lead
attacks fell from 31.64 to 20.89 per two-minute segment; those counts are not a
listening verdict.

The read-only preview passed actual Chromium playback, seeking, one-at-a-time
controls, 320/390px layouts, byte ranges and JavaScript-disabled native playback.
The experiment used a separate CPU-limited container without networking or a live
station-data mount. All five live service identities/images/start/restart/OOM
values were preserved, and the post-render station sample was healthy.

The [first prototype receipt](evidence/resting-profile-experiment-20261115.json)
retains that experiment. A reproducible offline command is now available below.
It does not create a live station channel or automatic time-of-day setting. The
v2 TimGM broadcast stays unchanged while preference is unresolved. Physical-device,
Safari, assistive-technology, public and off-host acceptance remain open.

## Generate a fresh pair

The reference is version-2 composition at 60 BPM; the resting candidate uses 52 BPM,
profile 0 and programs (89, 32, 4). The command does not read the running station's
configuration or database. Default seed 42 / positions 1–12 produce three complete
chapters at 120 seconds per segment, with five-second crossfades: 23m05s per master.

With FluidSynth, FFmpeg/ffprobe and the SoundFont installed locally:

```sh
python -m radio.profile_audition --output /path/to/new-pair
```

Or build a separate lab image from the current checkout, preserving live aliases:

```sh
docker build -t generative-radio:profile-lab .
mkdir -p artifacts/profile-comparisons
docker run --rm --network none --read-only --cap-drop ALL \
  --user "$(id -u):$(id -g)" --cpus 2 --memory 2g \
  --label com.docker.compose.project=radio-profile-lab \
  --label com.docker.compose.service=operator \
  --tmpfs /tmp:rw,nosuid,nodev,size=64m,mode=1777 \
  --mount "type=bind,source=$PWD/artifacts/profile-comparisons,target=/comparisons" \
  generative-radio:profile-lab python -m radio.profile_audition \
  --output /comparisons/first
```

Choose a fresh output name for each run. Existing files/directories and broken
symlink destinations are refused. Output cannot be under a station-data ancestor
containing `radio.sqlite`, including a broken symlink marker. `--soundfont` selects
one readable local sf2/sf3 for both versions; the default is TimGM. `--station-seed`,
`--positions` and `--seconds` select the score sample. At most 24 unique positive
positions and 1800 nominal seconds per variant are accepted; each segment is 20–1800
integer seconds. This limits audio size, not total wall-clock runtime. External
commands use the existing per-command deadlines. Allow approximately 2 GB for a
maximum-size pair and its intermediate audio; retain or remove your own outputs
manually.

Require process exit 0 and `report.json` status `complete`. Failed/cancelled runs
retain partial evidence and cannot be resumed or overwritten; use a fresh name.
The report records sources, engine/font/MIDI/audio fingerprints, intended tempo
and programs, duration, silence checks and matched levels. Only a successful run
publishes `index.html`. Each variant has a measured WAV and 128 kbps MP3 copy.

## Preview the completed pair

Use a static server with byte ranges. This example uses a separate image/name and
port 18097; the current command acceptance preview is at [localhost:18096](http://localhost:18096).
The server user matches the output owner because output directories are private.

```sh
docker build -t generative-radio-web:profile-preview web
docker run --rm --name radio-profile-preview \
  --read-only --cap-drop ALL --security-opt no-new-privileges:true \
  --user "$(id -u):$(id -g)" \
  --label com.docker.compose.project=radio-profile-preview \
  --label com.docker.compose.service=web \
  --publish 127.0.0.1:18097:8080 \
  --mount "type=bind,source=$PWD/artifacts/profile-comparisons/first,target=/srv,readonly" \
  generative-radio-web:profile-preview caddy file-server --root /srv --listen :8080
```

The [command validation receipt](evidence/profile-audition-20261116.json) records
a real three-chapter render, all 24 MIDI fingerprints matching the prototype,
matched masters and actual browser/native/seek/range/narrow checks. All five live
station roles were preserved. These checks do not establish listening preference
or public/physical-device acceptance.
