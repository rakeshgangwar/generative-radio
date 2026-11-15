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
stream="${RADIO_STREAM_URL:-http://localhost:8000/radio.mp3}"
transport_log=""
show_transport_error() {
  if [ -n "$transport_log" ] && [ -s "$transport_log" ]; then
    cat "$transport_log" >&2
  fi
}
record() {
  ffmpeg -hide_banner -y -i "$1" -t "$duration" -c:a pcm_s16le artifacts/broadcast.wav
}
case "$stream" in
  [Hh][Tt][Tt][Pp][Ss]://*)
    # FFmpeg TLS defaults/backends differ. Curl authenticates both CA and hostname.
    transport_log=$(mktemp)
    trap 'rm -f "$transport_log"' 0
    transport_limit=$(awk -v seconds="$duration" 'BEGIN { printf "%.3f", seconds + 30 }')
    set -- --disable --silent --show-error --fail --noproxy '*' \
      --proto '=https' --proto-redir '=https' --location --max-redirs 5 \
      --connect-timeout 10 --speed-time 15 --speed-limit 1024 --max-time "$transport_limit"
    if [ -n "${RADIO_TLS_CA_FILE:-}" ]; then
      set -- "$@" --cacert "$RADIO_TLS_CA_FILE"
    fi
    # A complete capture intentionally closes the pipe; suppress that curl write error.
    if ! curl "$@" "$stream" 2> "$transport_log" | record pipe:0; then
      show_transport_error
      exit 1
    fi
    ;;
  *) record "$stream" ;;
esac
recorded=$(ffprobe -v error -show_entries format=duration \
  -of default=noprint_wrappers=1:nokey=1 artifacts/broadcast.wav)
# FFmpeg can return success when a finite source ends before -t is reached.
if ! awk -v expected="$duration" -v actual="$recorded" 'BEGIN {
  difference = expected - actual
  if (difference < 0) difference = -difference
  exit !(actual ~ /^[0-9]+([.][0-9]+)?$/ && actual > 0 &&
         difference <= 0.05 && actual >= expected * 0.95)
}'; then
  show_transport_error
  printf 'Capture incomplete: requested %s seconds, recorded %s seconds.\n' "$duration" "$recorded" >&2
  exit 1
fi
ffmpeg -hide_banner -i artifacts/broadcast.wav \
  -af 'silencedetect=noise=-50dB:d=2,astats=metadata=1:reset=0' \
  -f null - 2> artifacts/analysis.log
echo 'Recording: artifacts/broadcast.wav; analysis: artifacts/analysis.log'
