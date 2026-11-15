# A repeatable sound comparison

The next musical question is whether a fuller instrument library improves the
station over long listening. Build a concrete comparison rather than silently
changing the live stream. Standing creative/PR/CI-merge authorization applies.

## Approach

Keep composition, instruments, seeds and chapter positions identical. Render two
to four explicitly supplied local SoundFonts with the existing renderer, verify
identical MIDI hashes at each position, and generate matched-level WAV/MP3
listening sequences plus a portable HTML report and machine-readable manifest.

Alternatives: add moving MIDI expression to existing patches, or introduce a
synthesis/model path. Compare actual instrument libraries first: it isolates the
sound palette and provides a bench those later experiments can also use. No live
queue/config/default-SoundFont change and no new production dependency. An opt-in
lab Dockerfile adds FluidR3 to the existing image for this experiment only.

## Contract

`python -m radio.audition --output NEW_DIRECTORY --font label=FILE --font label=FILE
--station-seed 42 --positions 1 2 3 --seconds 120 --bpm 60`.
Labels are unique lowercase ASCII identifiers,2–4 fonts,1–24 distinct positive
positions,20–1800seconds each and at most1800 nominal seconds per font,40–90BPM.
Reject invalid inputs before creating output. Font paths must resolve to readable
regular sf2/sf3 files. Fingerprint content/size; check it again after rendering.
No font binary is copied/published. No Store, Config.load, station volume, network
or service mutation. Pure Config.from_env supplies an isolated root for each label.

Output directory is exclusively created, never reused/overwritten (including
symlinks). An atomic report.json starts as running and is complete only after all
renders/identity/quality/level checks pass. On caught failures mark failed and
preserve artifacts for diagnosis; do not erase output or report false completion.
The renderer cleans its own temporary files. A hard kill may leave running status;
that is incomplete, never accepted as a finished comparison.

Each variant retains its segment WAVs/MIDI and metrics, render wall time, font
fingerprint and engine versions. Join segments with identical5second linear
crossfades; the expected sequence duration isN*seconds-(N-1)*5. Measure integrated
loudness/true peak through FFmpeg loudnorm analysis. Choose one shared level no
louder than-22LUFS or the quietest input, lowering further if needed for-3dBTP.
Apply static attenuation only; never boost/limit to make a candidate seem better.
Verify final integrated levels within0.2LU and true peaks<=-2.9dBTP, duration and
existing PCM quality gates. MP3 is a convenient copy; WAV is the measured master.

The HTML report uses native audio controls, safe escaped labels/relative paths,
no network assets, and states that metrics do not establish listening preference.
The operator chooses one track at a time and can compare the same musical moment.
No generated audio/font binaries enter Git or the production web image.

## Evidence and delivery

Unit tests cover invalid/bounded inputs, fresh-output refusal, escaping and shared
attenuation math/nonfinite measurements. A real-media integration test compares
the installed font against itself as an identity control, checking MIDI equality,
sequence lengths/level matching, report state and playable MP3. Actual local
TimGM/FluidR3 trials cover all three current palettes, a multi-segment rehearsal,
measured time and independently observed memory. Keep library licenses/provenance.
One final independent review, current-head CI and a scoped PR; journal records
measured results, listening questions and unchanged on-air defaults.

Primary references: FFmpeg filter documentation (loudnorm/acrossfade), FluidR3
README and Debian copyright. The live two-hour capture remains untouched.
