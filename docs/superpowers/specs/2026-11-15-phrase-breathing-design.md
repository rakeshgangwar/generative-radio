# Melodic phrases with room to breathe

Engineering choice under the user's standing creative iteration and autonomous
implementation authorization. This is an experiment, not a listening-quality
claim. Keep the live station unchanged until paired media, review and CI support
shipping the candidate.

## Evidence and choice

Across 256 current positions at 120 seconds / 60 BPM, arrival/release leave full-bar
melodic rests. Unfold, bloom and settle leave none within the central 72 seconds.
The bloom stage averages 40.53 melodic attacks in that window and a longest rest
of only 1.44 seconds. This can make development feel like an unbroken repeating
figure even when harmony/palette changes. Baseline source and version-1 MIDI
hashes are in ignored `artifacts/phrase-breathing-20261115/baseline.json`.

Choose periodic phrase endings over key modulation or simply adding more
instruments. Modulation would require new transition constraints; more voices
could obscure the same repeated rhythm. Leave harmony, palettes, chapter stages,
render-ahead architecture and crossfades intact for this comparison.

## Behavior

Append `phrase_bars: int = 0` to Arrangement without breaking existing positional
arguments. Keep its constructor's version default 1; version-1 plans must produce
identical MIDI. New `arrangement_for` plans are version 2 with a chapter-shared
phrase length of 6, 8 or 10 bars, chosen by the existing bounded balanced scheduler
under a new `phrasing` label. Existing progression/motif/palette scheduling stays
identical; the new choice must not consume shared randomness.

For version-2 plans, omit melody attacks in the last bar of every phrase, in every
stage. End preceding MIDI note durations at least 0.1 beat before that
bar. Instrument release envelopes/reverb may continue; this is a score/MIDI rest,
not a guarantee of acoustic silence in an isolated melodic stem. Sustained pads/bass continue through these melodic rests. Existing sparse
stage gaps and quiet segment edges still apply; a new rest may coincide with an
existing one. Do not require a complete phrase in a short 20-second clip. Do not
change note velocity or harmony in this iteration.

Legacy `compose(..., arrangement=None)` stays byte-identical. Version-1 explicit
plans ignore the added field and stay byte-identical. Version-2 plans accept only
integer phrase_bars in {6, 8, 10}; unsupported plan versions or invalid version-2
lengths fail clearly rather than producing accidental rhythmic behavior.
Versioned metadata is already serialized with rendered jobs and audition reports.
`MUSICAL_MEMORY=0` remains the existing legacy operator rollback. Old ready WAVs are
immutable; only future renders use new plans after a deliberately scoped rollout.

## Evidence and delivery

Test deterministic constant-work planning at arbitrary/huge/out-of-order positions,
chapter-shared balanced phrase lengths, old planned/legacy MIDI compatibility,
full-bar rests without melody tails in all stages at 40/60/90 BPM, and safe finite
notes at 20/120/600 seconds. Existing pad/voice/note-off safety must remain green.
Compare 256-position rest/density properties to the preserved baseline. Those
measure structure, not emotional quality.

Run actual all-palette/stage renders and quality gates, then an identical-seed
three-chapter crossfade comparison against the current image. Preserve metadata,
render cost, loudness/headroom and silence measurements; export concrete MP3s for
listening. Do not infer a SoundFont preference or switch fonts. Independent final
review, all tests and actual current-head CI precede merge. Any live rollout is
worker-only with queue hashes/IDs preserved, rollback images retained and decoded
audio verified. Do not interrupt/restart broadcaster, Icecast or listener.
