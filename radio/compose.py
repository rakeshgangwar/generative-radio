"""Seeded, evolving A-minor arrangements and a Standard MIDI File writer."""
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
    # Separate bass roots from pad inversions; all harmony shares one scale.
    chords = {
        "Am": (45, (57, 60, 64, 71)), "F": (41, (53, 57, 60, 64)),
        "C": (36, (55, 60, 64, 71)), "G": (43, (55, 59, 62, 69)),
        "Dm": (38, (53, 57, 62, 65)), "Em": (40, (55, 59, 64, 67)),
    }
    progression = rng.choice([
        ("Am", "F", "C", "G"), ("Am", "Dm", "F", "Em"),
        ("F", "C", "Dm", "Am"), ("Am", "C", "G", "Dm", "F", "Em"),
        ("Dm", "Am", "F", "C"),
    ])
    holds = rng.choice([(2, 4, 3, 4), (4, 6, 4, 2), (3, 3, 6, 4)])
    profile = rng.randrange(3)
    harmony, start, section = [], 0., 0
    while start < seconds - 2:
        end = min(start + holds[section % len(holds)] * bar, seconds - .75)
        root, voicing = chords[progression[section % len(progression)]]
        harmony.append((start, end, root, voicing))
        start, section = end, section + 1

    notes = []
    for section, (start, end, root, voicing) in enumerate(harmony):
        # Never overlap a pad pitch on the same MIDI channel: the earlier
        # note-off would also silence a later retrigger of that pitch.
        for i, pitch in enumerate(voicing):
            at = start + i * .12
            duration = end - .08 * beat - at
            if duration > 0:
                notes.append(Note(at, duration, pitch, rng.randint(34, 44), 0))
        central = .2 <= start / seconds < .8
        if central or section % 2 == 0:
            notes.append(Note(start, min(2.5 * bar, end - start - .1),
                              root, rng.randint(32, 39), 1))

    # A two-bar phrase family develops through inversion and changed endings.
    scale = [p for p in range(60, 85) if p % 12 in {0, 2, 4, 5, 7, 9, 11}]
    motif = rng.choice([(0, 1, 2, 0), (0, 2, 1, -1), (0, -1, 1, 2)])
    rhythms = [(.5, 2.5), (1., 3.), (1.5,), (.5, 2., 3.)]
    rng.shuffle(rhythms)
    melody, previous, anchor, section = [], 69, scale.index(69), 0
    for bar_index, start in enumerate(_times(0, seconds - 2, bar)):
        central = .2 <= start / seconds < .8
        if not central and bar_index % 2:
            continue
        phrase = bar_index // 2
        if bar_index % 2 == 0:
            anchor = max(2, min(len(scale) - 3, scale.index(previous) + rng.choice([-1, 0, 1])))
        slots = rhythms[(phrase + profile) % len(rhythms)] if central else (1.5,)
        if central and profile == 0:
            slots = slots[:2]  # Spare: omit the third attack of busy phrases.
        elif central and profile == 2 and len(slots) == 1:
            slots = (.5, 2.5)  # Active: answer the otherwise isolated note.
        for slot_index, slot in enumerate(slots):
            at = start + slot * beat
            if at >= seconds - 2:
                continue
            while section + 1 < len(harmony) and at >= harmony[section][1]:
                section += 1
            voicing = harmony[section][3]
            interval = motif[(bar_index % 2 * 2 + slot_index) % len(motif)]
            if phrase % 3 == 1:
                interval = -interval
            elif phrase % 3 == 2 and slot_index == len(slots) - 1:
                interval += 1
            target = scale[max(0, min(len(scale) - 1, anchor + interval))]
            candidates = [p for p in scale if p % 12 in {v % 12 for v in voicing}
                          and abs(p - previous) <= 7]
            pitch = min(candidates, key=lambda p: (abs(p - target), abs(p - previous), p))
            duration = (0.75, 1.5, 2.5)[(phrase + slot_index) % 3] * beat
            melody.append(Note(at, min(duration, seconds - at - .75), pitch,
                               rng.randint(31, 44) if central else rng.randint(27, 35), 2))
            previous = pitch
    # Give successive melodic notes room to release, even when rhythms change.
    for i, note in enumerate(melody):
        end = melody[i + 1].start - .1 * beat if i + 1 < len(melody) else seconds - .75
        notes.append(Note(note.start, min(note.duration, end - note.start),
                          note.pitch, note.velocity, note.channel))
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
