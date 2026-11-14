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
    def load(cls):
        memory = os.getenv("MUSICAL_MEMORY", "1")
        if memory not in {"0", "1"}:
            raise ValueError("MUSICAL_MEMORY must be 0 or 1")
        c = cls(Path(os.getenv("RADIO_DATA", "data")),
                int(os.getenv("SEGMENT_SECONDS", "120")),
                int(os.getenv("BUFFER_SECONDS", "1200")),
                int(os.getenv("BPM", "60")),
                int(os.getenv("STATION_SEED", "20261114")),
                os.getenv("SOUNDFONT", "/usr/share/sounds/sf2/TimGM6mb.sf2"),
                memory == "1")
        if not 20 <= c.segment_seconds <= 600:
            raise ValueError("SEGMENT_SECONDS must be between 20 and 600")
        if not c.segment_seconds <= c.buffer_seconds <= 3600:
            raise ValueError("BUFFER_SECONDS must be between SEGMENT_SECONDS and 3600")
        if not 40 <= c.bpm <= 90:
            raise ValueError("BPM must be between 40 and 90")
        c.data.mkdir(parents=True, exist_ok=True)
        return c
