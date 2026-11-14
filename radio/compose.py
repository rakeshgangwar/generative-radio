"""Slow A-minor arrangements and a small Standard MIDI File writer.

All segments share a tonal centre to keep arbitrary crossfades consonant.
Randomness changes phrasing/voicing; a four-chord arc supplies structure.
"""
import random
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class Note:
    start: float
    duration: float
    pitch: int
    velocity: int
    channel: int


def compose(seed: int, seconds: float, bpm: int = 60) -> list[Note]:
    rng = random.Random(seed)
    beat = 60 / bpm
    bar = 4 * beat
    # Am9, Fmaj7, Cmaj9, G6; common tones connect each voicing.
    chords = [(57, 60, 64, 71), (53, 57, 60, 64),
              (55, 60, 64, 71), (55, 59, 62, 64)]
    notes = []
    motif = [rng.choice([0, 1, 2, 3]) for _ in range(4)]
    for section, start in enumerate(_times(0, seconds - 4, 4 * bar)):
        chord = chords[section % len(chords)]
        length = min(4 * bar + beat, seconds - start - 2)
        for i, pitch in enumerate(chord):
            notes.append(Note(start + i * .12, length - i * .12,
                              pitch, rng.randint(35, 46), 0))
        notes.append(Note(start, min(3 * bar, length), chord[0] - 12, 38, 1))
        for phrase in range(4):
            at = start + phrase * bar + rng.choice([1, 2]) * beat
            if at < seconds - 4 and rng.random() < .78:
                pitch = chord[motif[phrase]] + 12
                notes.append(Note(at, min(2 * beat, seconds - at - 2),
                                  pitch, rng.randint(33, 49), 2))
    return notes


def _times(start, stop, step):
    while start < stop:
        yield start
        start += step


def _vlq(value: int) -> bytes:
    out = [value & 127]
    while (value := value >> 7):
        out.insert(0, (value & 127) | 128)
    return bytes(out)


def midi(notes: list[Note], seconds: float, bpm: int) -> bytes:
    ticks = 480
    tempo = round(60_000_000 / bpm)
    events = [(0, b"\xff\x51\x03" + tempo.to_bytes(3, "big"))]
    # GM warm pad, acoustic bass, electric piano; zero-based program numbers.
    for ch, program in enumerate([89, 32, 4]):
        events.extend([(0, bytes([0xC0 | ch, program])),
                       (0, bytes([0xB0 | ch, 91, 65])),
                       (0, bytes([0xB0 | ch, 10, [48, 64, 80][ch]]))])
    to_tick = lambda t: round(t * 1_000_000 / tempo * ticks)
    for n in notes:
        events.append((to_tick(n.start), bytes([0x90 | n.channel, n.pitch, n.velocity])))
        events.append((to_tick(n.start + n.duration), bytes([0x80 | n.channel, n.pitch, 0])))
    events.append((to_tick(seconds), b"\xff\x2f\x00"))
    body, previous = bytearray(), 0
    for at, event in sorted(events, key=lambda x: x[0]):
        body.extend(_vlq(at - previous) + event)
        previous = at
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks) + b"MTrk" + struct.pack(">I", len(body)) + body
