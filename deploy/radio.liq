log.file.set(false)
log.stdout.set(true)

# A local command and shared disk keep playback independent of the composer.
def next_track() =
  lines = process.read.lines("python -m radio next")
  request.create(list.hd(default="", lines))
end

music = request.dynamic(id="generated", next_track)
security = single("/data/audio/fallback.wav")
# Finish the current fallback before switching back to new music.
radio = fallback(track_sensitive=true, [music, security])
radio = crossfade(duration=5., radio)

output.icecast(
  %mp3(bitrate=128, samplerate=44100, stereo=true),
  host="icecast", port=8000,
  password=environment.get("ICECAST_SOURCE_PASSWORD"),
  mount="/radio.mp3", name="Generative Ambient Radio",
  description="Original algorithmic ambient music", genre="Ambient",
  radio
)
