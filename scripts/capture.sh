#!/bin/sh
# Record a real-time acceptance run (30 minutes by default).
set -eu
duration="${1:-1800}"
if ! awk -v seconds="$duration" 'BEGIN { exit !(seconds ~ /^[0-9]+([.][0-9]+)?$/ && seconds > 0) }'; then
  echo 'Duration must be a positive number of seconds.' >&2
  exit 2
fi
mkdir -p artifacts
rm -f artifacts/analysis.log
ffmpeg -hide_banner -y -i "${RADIO_STREAM_URL:-http://localhost:8000/radio.mp3}" \
  -t "$duration" -c:a pcm_s16le artifacts/broadcast.wav
recorded=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 artifacts/broadcast.wav)
# FFmpeg can return success when a finite source ends before -t is reached.
if ! awk -v expected="$duration" -v actual="$recorded" 'BEGIN {
  difference = expected - actual
  if (difference < 0) difference = -difference
  exit !(actual ~ /^[0-9]+([.][0-9]+)?$/ && actual > 0 &&
         difference <= 0.05 && actual >= expected * 0.95)
}'; then
  printf 'Capture incomplete: requested %s seconds, recorded %s seconds.\n' "$duration" "$recorded" >&2
  exit 1
fi
ffmpeg -hide_banner -i artifacts/broadcast.wav \
  -af 'silencedetect=noise=-50dB:d=2,astats=metadata=1:reset=0' \
  -f null - 2> artifacts/analysis.log
echo 'Recording: artifacts/broadcast.wav; analysis: artifacts/analysis.log'
