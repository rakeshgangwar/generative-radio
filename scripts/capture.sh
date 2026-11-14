#!/bin/sh
# Record a real-time acceptance run (30 minutes by default).
set -eu
mkdir -p artifacts
ffmpeg -hide_banner -y -i http://localhost:8000/radio.mp3 \
  -t "${1:-1800}" -c:a pcm_s16le artifacts/broadcast.wav
ffmpeg -hide_banner -i artifacts/broadcast.wav \
  -af 'silencedetect=noise=-50dB:d=2,astats=metadata=1:reset=0' \
  -f null - 2> artifacts/analysis.log
echo 'Recording: artifacts/broadcast.wav; analysis: artifacts/analysis.log'
