"""Bounded, recoverable musical context from a station seed and queue position."""
from dataclasses import dataclass
import hashlib
import random


PROGRESSIONS = (
    ('Am', 'F', 'C', 'G'), ('Am', 'Dm', 'F', 'Em'),
    ('F', 'C', 'Dm', 'Am'), ('Am', 'C', 'G', 'Dm', 'F', 'Em'),
    ('Dm', 'Am', 'F', 'C'),
)
HOLD_PATTERNS = ((2, 4, 3, 4), (4, 6, 4, 2), (3, 3, 6, 4))
MOTIFS = ((0, 1, 2, 0), (0, 2, 1, -1), (0, -1, 1, 2),
          (0, 2, 3, 1), (0, -2, -1, 1), (0, 1, -1, -2))
PALETTES = ((89, 32, 4), (94, 32, 4), (89, 32, 11))
REGISTERS = (64, 67, 69, 72, 76)


@dataclass(frozen=True)
class Arrangement:
    position: int
    chapter: int
    chapter_segment: int
    chapter_segments: int
    stage: str
    progression: tuple[str, ...]
    holds: tuple[int, ...]
    motif: tuple[int, ...]
    profile: int
    register: int
    programs: tuple[int, int, int]
    rhythm_order: tuple[int, ...]
    phrase_gap: int
    version: int = 1


def _permutation(seed, label, block, choices):
    digest = hashlib.sha256(f'radio-arrangement-v1:{seed}:{label}:{block}'.encode()).digest()
    values = list(choices)
    random.Random(int.from_bytes(digest, 'big')).shuffle(values)
    return values


def _choice(seed, label, index, choices):
    if len(choices) < 3:
        raise ValueError('Balanced scheduling requires at least three choices')
    block, offset = divmod(index, len(choices))
    values = _permutation(seed, label, block, choices)
    if block and values[0] == _permutation(seed, label, block - 1, choices)[-1]:
        # Only swap the first two: the previous block's last stays its raw last.
        values[0], values[1] = values[1], values[0]
    return values[offset]


def arrangement_for(station_seed: int, position: int) -> Arrangement:
    """Reconstruct a queue-order chapter in constant work, including after restore."""
    if type(station_seed) is not int or type(position) is not int or position < 1:
        raise ValueError('Station seed must be an integer and position a positive integer')
    block, offset = divmod(position - 1, 12)
    lengths = _permutation(station_seed, 'chapter-length', block, (3, 4, 5))
    for chapter_index, length in enumerate(lengths):
        if offset < length:
            break
        offset -= length
    chapter = block * 3 + chapter_index + 1
    stages = {3: ('arrival', 'bloom', 'release'),
              4: ('arrival', 'unfold', 'bloom', 'release'),
              5: ('arrival', 'unfold', 'bloom', 'settle', 'release')}
    stage = stages[length][offset]
    profile = {'arrival': 0, 'unfold': 1, 'bloom': 2, 'settle': 1, 'release': 0}[stage]
    holds = _choice(station_seed, 'holds', chapter - 1, HOLD_PATTERNS)
    rotation = offset % len(holds)
    return Arrangement(
        position=position, chapter=chapter, chapter_segment=offset + 1,
        chapter_segments=length, stage=stage,
        progression=_choice(station_seed, 'harmony', position - 1, PROGRESSIONS),
        holds=holds[rotation:] + holds[:rotation],
        motif=_choice(station_seed, 'motif', chapter - 1, MOTIFS),
        profile=profile,
        register=_choice(station_seed, 'register', chapter - 1, REGISTERS),
        programs=_choice(station_seed, 'palette', chapter - 1, PALETTES),
        rhythm_order=tuple(_permutation(station_seed, 'rhythm', chapter - 1, (0, 1, 2, 3))),
        phrase_gap=_choice(station_seed, 'breath', position - 1, (0, 1, 2, 3)),
    )
