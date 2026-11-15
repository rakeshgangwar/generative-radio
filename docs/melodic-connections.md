# A matched melody audition

This offline experiment compares the current version 2 score with a few quiet,
stepwise connecting notes. Original attacks, pitches and velocities stay fixed;
a selected melody tail may be shortened while retaining at least half its duration
and half a beat. Pads, bass, arrival/release profiles and explicit phrase rests stay
unchanged. Workers do not call this transform; the station continues on version 2.
SoundFont release/reverb can ring through a MIDI rest.

The current local comparison is at http://localhost:18091. Pause other audio, play
one version at a time and compare the same moment. Start near 2:20; the page lists
all seven changed moments. Both 23m05s masters use TimGM and measure -22.07 LUFS.
This is deliberately a small audition, not a claim that more notes improve music.

## Generate a fresh comparison

Run from the repository root. These separate image tags preserve live aliases.
The container mounts only a new audition parent, with no station-data volume.

```sh
docker build -t generative-radio:melody-lab .
mkdir -p artifacts/melodic-connections
docker run --rm --network none --read-only --cap-drop ALL \
  --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,size=64m,mode=1777 \
  --mount "type=bind,source=$PWD/artifacts/melodic-connections,target=/auditions" \
  generative-radio:melody-lab python -m radio.melody_audition \
  --output /auditions/pair --station-seed 20261114 \
  --positions 1 2 3 4 5 6 7 8 9 10 11 12 --seconds 120 --bpm 60
```

The default font is `/usr/share/sounds/sf2/TimGM6mb.sf2`; `--soundfont` accepts a
local sf2/sf3 path in the container. Both variants use the same file and verify its
fingerprint. The CLI supports at most 24 unique positive positions and 1800 nominal
seconds total, 20–1800 seconds per segment and 40–90 BPM. Output must be fresh and
outside any directory tree containing `radio.sqlite`. No database is opened.

Require CLI exit 0 and `report.json` status `complete`. Running/failed output is
partial evidence. The report contains engine/source/font hashes, exact MIDI hashes,
added-note and shortened-tail counts, phrase-time guides and audio measurements.
A zero-addition pair is described as identical rather than a musical improvement.

Each variant includes measured `listen.wav` and a 128 kbps `listen.mp3` convenience
copy. Segments use the station's existing fades and five-second crossfades. Final
levels use attenuation only and must match within 0.2 LUFS with true peak at most
-2.9 dBFS. Timing guides are score times; rendered releases and MP3 timing can differ.

## Serve only the completed audition

Use a static server with byte-range support so long-track seeking works. The
initial Python server on this machine returned 200 for Range requests and failed
actual browser seeking. This Caddy command returned 206 with the requested bytes.
Choose a free loopback port; the current session uses 18091.

```sh
docker build -t generative-radio-web:audition-preview web
docker run --rm --name radio-melody-preview \
  --read-only --cap-drop ALL --security-opt no-new-privileges:true \
  --publish 127.0.0.1:18091:8080 \
  --mount "type=bind,source=$PWD/artifacts/melodic-connections/pair,target=/srv,readonly" \
  generative-radio-web:audition-preview caddy file-server --root /srv --listen :8080
```

Open http://localhost:18091. Audio has native controls, no autoplay/preload and
one-at-a-time playback. The server sees only the audition directory. Stop that
preview when finished; retain any comparison evidence you want to keep.

## What has been verified

The first pair has 12 positions, 1385 seconds per master, seven added connections and
five shortened tails. Both exact PCM frame counts and the absence of a silence
lasting at least two seconds below -50 dB were checked independently. Chromium played
and sought both tracks to the same phrase, paused the other track automatically,
and fit 320/390px and desktop widths. This is not physical-device/Safari acceptance
or a human musical preference. No on-air version change follows from the metrics.
