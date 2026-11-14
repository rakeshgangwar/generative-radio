import array
from dataclasses import asdict
import math
import os
import subprocess
import sys
import wave
from pathlib import Path

from .compose import compose, midi


def run(args, timeout=180):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{args[0]} failed: {result.stderr[-1500:]}")


def analyze(path: Path):
    peak, squares, count, quiet, windows = 0, 0, 0, 0, 0
    with wave.open(str(path), "rb") as audio:
        if audio.getsampwidth() != 2 or audio.getnchannels() != 2 or audio.getframerate() != 44100:
            raise ValueError("Expected stereo 44.1kHz PCM16")
        duration = audio.getnframes() / audio.getframerate()
        while block := audio.readframes(4410):
            values = array.array("h", block)
            if sys.byteorder != "little":
                values.byteswap()
            power = sum(v * v for v in values)
            peak = max(peak, max(abs(v) for v in values))
            squares += power
            count += len(values)
            windows += 1
            quiet += power / len(values) < (32768 * .001) ** 2
    if not count:
        raise ValueError("Empty render")
    result = {"duration": duration, "peak": peak / 32768,
              "rms_dbfs": 10 * math.log10(max(squares / count, 1) / 32768**2),
              "quiet_fraction": quiet / windows}
    if result["peak"] >= .99 or result["rms_dbfs"] < -48 or result["quiet_fraction"] > .25:
        raise ValueError(f"Audio quality gate failed: {result}")
    return result


def render(config, seed, seconds, stem, *, arrangement=None):
    for directory in ["midi", "audio", "work"]:
        (config.data / directory).mkdir(exist_ok=True)
    mid = config.data / "midi" / f"{stem}.mid"
    raw = config.data / "work" / f"{stem}.raw.wav"
    temporary = config.data / "work" / f"{stem}.wav"
    final = config.data / "audio" / f"{stem}.wav"
    notes = compose(seed, seconds, config.bpm, arrangement=arrangement)
    programs = arrangement.programs if arrangement else None
    mid.write_bytes(midi(notes, seconds, config.bpm, programs=programs))
    try:
        run(["fluidsynth", "-ni", "-q", "-r", "44100", "-g", "0.5",
             "-T", "wav", "-O", "s16", "-F", str(raw), config.soundfont, str(mid)])
        # Conservative loudness target; limiter is a final guard against peaks.
        run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-t", str(seconds),
             "-af", f"loudnorm=I=-22:TP=-3:LRA=9,afade=t=in:d=2,afade=t=out:st={seconds-3}:d=3,alimiter=limit=0.8:level=false",
             "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(temporary)])
        analysis = analyze(temporary)
        if abs(analysis["duration"] - seconds) > .1:
            raise ValueError("Unexpected rendered duration")
        os.replace(temporary, final)
        if arrangement:
            analysis["arrangement"] = asdict(arrangement)
        return final, analysis
    finally:
        raw.unlink(missing_ok=True)
        temporary.unlink(missing_ok=True)
