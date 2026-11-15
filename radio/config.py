import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Config:
    data: Path
    segment_seconds: int
    buffer_seconds: int
    bpm: int
    seed: int
    soundfont: str
    musical_memory: bool = True

    @classmethod
    def from_env(cls, env):
        memory = env.get("MUSICAL_MEMORY", "1")
        if memory not in {"0", "1"}:
            raise ValueError("MUSICAL_MEMORY must be 0 or 1")
        c = cls(Path(env.get("RADIO_DATA", "data")),
                int(env.get("SEGMENT_SECONDS", "120")),
                int(env.get("BUFFER_SECONDS", "1200")),
                int(env.get("BPM", "60")),
                int(env.get("STATION_SEED", "20261114")),
                env.get("SOUNDFONT", "/usr/share/sounds/sf2/TimGM6mb.sf2"),
                memory == "1")
        if not 20 <= c.segment_seconds <= 600:
            raise ValueError("SEGMENT_SECONDS must be between 20 and 600")
        if not c.segment_seconds <= c.buffer_seconds <= 3600:
            raise ValueError("BUFFER_SECONDS must be between SEGMENT_SECONDS and 3600")
        if not 40 <= c.bpm <= 90:
            raise ValueError("BPM must be between 40 and 90")
        return c

    @classmethod
    def load(cls):
        c = cls.from_env(os.environ)
        c.data.mkdir(parents=True, exist_ok=True)
        return c
