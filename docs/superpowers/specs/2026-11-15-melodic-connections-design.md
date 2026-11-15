# Offline melodic connections audition

Standing autonomous creative-iteration authority and brainstorming opt-out apply.
This is an audition experiment; the live version2 station stays unchanged.

## Why and direction

The score audit over1,024 segments/version found about46% repeated adjacent melody
pitches despite the new rests. This is a prompt for listening, not a defect threshold.
Test occasional quiet, stepwise connections between existing anchors. Keep every
original note, phrase breath and harmonic foundation. Do not optimize a repetition
number or make the station busier by default.

## Pure connector

Add radio/melodic_connections.py:
`connect_melody(notes, seconds, bpm, arrangement) -> list[Note]`.
Accept a list/tuple of at most4096 Note objects, finite numeric seconds20..1800,
integer BPM40..90, and a version2 Arrangement with phrase_bars6/8/10 and profile0/1/2.
Reject bools/nonfinite/range-invalid note fields: start>=0, duration>0, end<=seconds,
integer pitch0..127, velocity1..127 and channel0..2. Empty input returns empty.
Never mutate input or original Note values. Return originals in original order,
followed by inserted notes; midi() already orders events. Defaults compose/midi and
arrangement planning remain untouched. Profile0 returns originals only.

Sort original channel2 notes by start and examine consecutive pairs. An insertion
requires absolute pitch distance3 or4 semitones and the unique intermediate A-minor
scale pitch (pitch-class0/2/4/5/7/9/11), within two semitones of both anchors. Preserve
original anchors, including intentional repeats; do not replace or shorten them.
Set insertion start=target.start-.75 beat, duration=.5 beat, velocity=max(1,target.velocity-5),channel2.
Require start >= previous.end+.1 beat, end <= target.start-.1 beat, and the insertion
and target to fall within the middle20..80% of the segment. Require its fractional
beat to be between.2 and.8 (away from strong integer beats).

Use held channel0 notes to infer active pad pitch-class sets at insertion and target.
Both sets must match, contain at least3 classes and contain both anchor classes.
Thus the connection does not cross a harmony change or a partially assembled pad.
It may be a chord tone or a passing scale tone; no chromatic notes are introduced.

Reject insertion in the last bar of a6/8/10-bar phrase or across a phrase boundary.
At most one insertion per target phrase; profile1 uses even-numbered phrases only,
profile2 may use every phrase. No random state/new seed mapping. If no eligible gap
exists, preserve identical notes and report zero additions rather than forcing change.

## Offline rendering and comparison

Extract existing synthesis/normalization/atomic publication/cleanup into
`render_notes(config, notes, seconds, stem, *, arrangement=None)` in radio/render.py.
Existing render composes its exact current notes and delegates. Preserve default
MIDI bytes and all current render flags, analysis and failure cleanup. This helper
is only used by the offline bench for transformed scores; workers keep render().

New radio/melody_audition.py CLI:
`python -m radio.melody_audition --output PATH --soundfont PATH --station-seed INT --positions N... --seconds INT --bpm INT`.
Defaults seed42, positions1/2/3,seconds120,BPM60,TimGM installed path.
Use existing comparison input bounds and SoundFont validation: baseline/connections
intentionally share the same supplied font; positions unique positive<=24, nominal
total<=1800s,seconds20..1800,BPM40..90. Validate before creating output. Reserve an
exclusive fresh output and reject an output under any ancestor containing radio.sqlite.
Never import/open Store/SQLite or mount live data. Do not overwrite existing output.

For each position use the existing version2 plan and seed=station_seed+position.
Render the baseline through render(), candidate through render_notes() with the
pure transformed list. Save source/baseline/candidate MIDI fingerprints and addition
counts. Verify baseline MIDI matches the untouched composer and both variants use
the same unmodified SoundFont fingerprint. Reuse existing crossfade/measurement/
attenuation-only level matching/check helpers.5s crossfades; exact expected duration,
within.2LUFS shared level, peak<=-2.9dBFS, no positive gain. Save measured WAV and
128kbps MP3 per variant, per-segment analysis and engine/source fingerprints.
Atomic running/failed/complete report; failed work never pretends to be complete.

HTML uses existing quiet blue/system-body/Palatino style, two explicit audio controls,
no autoplay/preload, one-at-a-time playback. Explain same font/matched level/different
notes, pause other audio, compare same moment, and metrics do not decide quality.
Report zero-addition comparisons honestly. No font binaries or large media in git.

## Verification and delivery

Pure tests cover a known clear gap, both directions, profile sparsity, unchanged
anchors/pad/bass, repeat/no-space/large-leap/harmony-change rejection, rests and phrase
cap, bounded invalid inputs and deterministic score matrix. Baseline golden MIDI
fingerprints are captured from merged main before editing render. Prove extraction
preserves default v1/v2/unplanned MIDI and existing cleanup with real render tools.
Bench tests cover validation/exclusive outputs/data guard/failed reports/escaping,
real same-font scores, levels/duration/fingerprints and no database creation.

Render a matched12-position,120s pair (23m05s each) with current TimGM; inspect
score/addition/level/peak/silence and transition evidence without human quality claims.
Actual browser check of the offline report at narrow/desktop sizes. No main role,
image tag, service or queue change. One fresh final review, real final-head/current-base
CI and scoped PR before merge. No on-air deployment for this audition-only experiment.
