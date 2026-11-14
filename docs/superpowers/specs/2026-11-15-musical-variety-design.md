# Reduce musical repetition

Status: approved by the user on 15 November 2026: "Go ahead. Implement it."

## Intent and constraints

The user enjoys the melody but reports that the station is too repetitive after
extended listening. Improve the development within each track and the variety
between tracks while retaining the calm ambient character.

Keep the existing Python/FluidSynth implementation, CPU-only rendering, seeded
reproducibility, queue, crossfades, and audio validation. Keep the current pad,
bass, and electric-piano instruments for this change. No dependencies, GPU,
external music service, new genre, or management UI are needed.

## Approaches

1. Rotate instrument programs. This changes the sound quickly but leaves the
   repeated harmony and phrase shape intact. Defer until arrangement changes
   have been evaluated by listening.
2. Develop the arrangement and melody. Select among several harmonic paths,
   develop related phrases, and change the texture over a track. This addresses
   the repeated musical structure directly and is the recommended approach.

The user approved the recommended arrangement and melody approach.

## Proposed behavior

- Replace the single repeating four-chord sequence with several curated
  progressions using notes from A natural minor / C major. Select a progression
  and a bounded chord-hold pattern from the seed.
- Build a small family of related melodic phrases. Vary the phrase ending,
  rhythm, rests, and register, and favor small pitch movements between phrases.
  Retain recognizable material within a track without repeating one pattern
  throughout it.
- Give each track a gentle introduction, development, and release. Vary melodic
  density and bass participation across these phases while sustained pads keep
  the texture continuous. Seed-selected profiles make different tracks sparser
  or more active without abrupt changes of character.
- Retain the existing public `compose(seed, seconds, bpm)` and MIDI interfaces.
  Keep note times within the requested duration, MIDI pitches within 36–84,
  velocities within 1–60, and all pitches in the existing seven-note scale.
- Handle the supported segment durations (20–600 seconds) and tempos (40–90 BPM).
  The same inputs must still produce identical notes and MIDI bytes.

The shared scale helps transitions, but does not guarantee that every overlap
sounds consonant. Rendered transition previews and listening remain necessary.

## Validation and rollout

- Add behavioral tests for harmonic diversity across a fixed set of seeds,
  phrase development, bounded density, reproducibility, and note constraints at
  duration/tempo boundaries. Tests should inspect musical structure rather than
  merely require different velocities or different random outputs.
- Run the full unit suite. Render several two-minute examples with the installed
  SoundFont and verify the existing audio gates and render speed. Produce a
  short sequence of examples with the normal crossfade for listening review.
- Leave the live broadcaster running while preparing examples. After validation,
  rebuild and update the composer/renderer image. Existing buffered tracks are
  retained and play first; the change should become audible after approximately
  the current 21-minute buffer. Avoid deleting the queue or audio volume.
- Update the README and handoff with measured results, preview paths, and the
  distinction between tested structural variety and subjective listening quality.

Persistent station-wide musical state, tempo automation, extra instruments,
watchdog implementation, and public deployment are outside this change.

Success requires the user to hear less repetition while still finding the music
pleasant. Unit tests alone cannot establish that outcome.
