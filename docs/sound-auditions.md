# Compare the station's sound

The writing and the instrument library are different choices. This bench renders
identical planned scores with two to four local SoundFonts so a fuller library
can earn its place through listening. It never opens the station database or
changes its queue, default sound or services. Use a separate output location.

## Make a comparison

On a machine with Python 3.11+, FluidSynth and FFmpeg/ffprobe, supply labeled sf2/sf3
files you are entitled to use. The output's parent must exist; its final directory
must be new. Existing directories and symlinks are refused, as are locations
nested under station data containing `radio.sqlite`.

```sh
mkdir -p artifacts
python3 -m radio.audition --output artifacts/sound-session-1 \
  --font timgm=/usr/share/sounds/sf2/TimGM6mb.sf2 \
  --font fluidr3=/usr/share/sounds/sf2/FluidR3_GM.sf2 \
  --station-seed 20261114 --positions 1 2 3 --seconds 120 --bpm 60
```

Labels use lowercase ASCII letters, digits and hyphens, starting with a letter.
There must be two to four distinct labels. Positions are unique positive integers
in the order to be heard; nonconsecutive positions are useful for a coverage
matrix but skip the intervening musical development. Limits: 24 positions,
20–1800 seconds per clip, at most 1800 nominal seconds per font and 40–90 BPM.
The same font under two labels is allowed as an identity control.

Open `index.html`, or serve only that output directory on loopback:

```sh
python3 -m http.server 18084 --bind 127.0.0.1 --directory artifacts/sound-session-1
```

The page uses native audio controls and pauses the other version when one starts.
It has no network assets or autoplay. Compare the same musical moment, and keep
playback volume fixed. Download the measured WAV if you want the uncompressed
master; MP3 is a convenient listening copy. Consider twenty minutes as well as
first impressions: does the bass become tiring, does the melody remain clear,
and do the transitions feel welcome?

## What the measurements prove

Every output MIDI is checked against the same expected score hash. The report
records seeds, positions, arrangement metadata, engine versions, source hashes,
font byte size/SHA256 and per-segment wall time. Font content is checked again
after rendering. Keep stable input files and retain their license/provenance
separately; the bench does not copy or distribute the font binaries.

The existing renderer first applies its normal station processing. Segments join
with five-second linear crossfades. Expected duration is `N*seconds-(N-1)*5`.
FFmpeg measures integrated loudness and true peak; all complete sequences receive
static attenuation to one shared level no louder than the quietest input or
−22 LUFS, with −3 dBTP headroom. No variant is boosted to win a louder-is-better
comparison. Final WAVs must pass the normal PCM quality gate, match duration,
remain within 0.2 LU of each other and the target, and stay below −2.9 dBTP.
MP3 encoding can change true peaks slightly; WAV is the measured master.

A completed `report.json` is required. Caught failures mark it `failed` and leave
partial artifacts for diagnosis. A hard kill may leave `running`; neither state
is an accepted comparison. Never relabel an interrupted run as complete. Use a
new output name for another attempt. Loudness/peak checks and MIDI identity do not
establish musical preference or a better overall listening experience.

## Optional isolated FluidR3 lab

The production image remains small and uses TimGM. This optional image installs
Debian's `fluid-soundfont-gm`; it does not change host packages or station tags.

```sh
docker build -t generative-radio:audition-code .
docker build -f scripts/Dockerfile.audition \
  --build-arg BASE_IMAGE=generative-radio:audition-code \
  -t generative-radio:audition-lab .
docker volume create radio-auditions
docker run --rm --network none --memory 512m --cpus 2 \
  -v radio-auditions:/data generative-radio:audition-lab \
  python -m radio.audition --output /data/session-1 \
  --font timgm=/usr/share/sounds/sf2/TimGM6mb.sf2 \
  --font fluidr3=/usr/share/sounds/sf2/FluidR3_GM.sf2 \
  --station-seed 20261114 --positions 1 2 3 --seconds 120
```

Use a dedicated volume, never the live `radio-data` volume. To export a completed
run, create a stopped container attached to the lab volume, copy its output, then
remove only that container:

```sh
docker create --name radio-audition-export --network none \
  -v radio-auditions:/data:ro generative-radio:audition-lab true
docker cp radio-audition-export:/data/session-1 ./artifacts/session-1
docker rm radio-audition-export
```

Keep the lab volume until you have verified the export. Use a fresh container name
if an export container already exists; this is no instruction to remove another
operator's work. No font/audio binaries enter Git or the production web image.

FluidR3 is attributed to Frank Wen (2000–2002, 2008) and Toby Smithe (2008) under
MIT; Debian packaging has its own GPL-2+ terms. Inspect the installed
`/usr/share/doc/fluid-soundfont-gm/copyright`. The [upstream release
README](https://sources.debian.org/src/fluid-soundfont/3.1-5.2/README/) and
[Debian copyright](https://sources.debian.org/src/fluid-soundfont/3.1-6/debian/copyright/)
record provenance. TimGM retains the separate license described in the main README.
FFmpeg's [loudnorm and acrossfade documentation](https://ffmpeg.org/ffmpeg-filters.html)
describes the measurement and joining filters.

## Measured local experiment, 15 November 2026

Both libraries rendered all 15 current palette/stage combinations, then the same
12 consecutive two-minute segments (three full chapters). The long masters are
23m05s each, both −22.10 LUFS, with no detected −50 dB silence lasting two seconds.
TimGM true peak was −7.79 dBTP; FluidR3 was −5.23 dBTP. These are measured master
properties, not a claim that the larger library sounds better.

| Measure | TimGM | FluidR3 |
| --- | ---: | ---: |
| Font bytes | 5,969,788 | 148,398,306 |
| 120s render, isolated resource trial | 3.90s | 4.29s |
| Container memory peak, same trial | 108.8 MiB | 195.8 MiB |
| 120s renders across long comparison | 3.70–4.08s | 4.01–4.70s |

Resource trials had a two-CPU/512 MiB container limit. Memory is the kernel cgroup
peak, including file cache, during one planned 120s render; it is not a full-station
capacity guarantee. No GPU was used. Re-measure on the actual deployment host.
Local artifacts live under `artifacts/sound-auditions-20261115/`, including font
provenance, matrix/long manifests, MP3/WAV masters and silence analysis. The live
station's default remains TimGM while listening preference is open.
