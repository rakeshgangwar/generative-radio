# Musical memory and longer arcs

Engineering design under the active creative/product goal, standing implementation/PR/merge authorization and journal direction. No separate human design approval claimed. Preserve the CPU-only buffered architecture.

## Why and approach

The listener found the early station repetitive. The first variety iteration broadened harmony/phrasing, but a 256-seed score baseline still has54/255 adjacent equal four-chord openings and198/256 melody starts onA. These structural measures motivate an experiment, not a listening-quality claim.

Choose a deterministic session arrangement planner rather than a generation model or a new history database. Queued jobs already store seed and monotonic ID; their originating station seed is `job.seed-job.id`, independent of current environment. Reconstruct a plan from that origin and position, so cleanup/restart/backup restore preserve musical continuity without schema changes. A database of confirmed play history would be more precise but the existing queue records dispatch, not on-air completion; do not pretend otherwise.

## Planned behavior

`arrangement_for(station_seed, position)` returns a frozen version1 Arrangement. Position/chapter segment numbers are1-based. It includes chapter, chapter_segment, chapter_segments, stage, progression, holds, motif, profile, register, programs, rhythm_order and phrase_gap. Validate integer station seed and positive integer position; no process-global state or work proportional to station age.

Schedule each of the five existing harmonic paths once per shuffled block. Prevent adjacent repeats across block boundaries by swapping only the first two entries if the new first equals the previous raw last. With at least three choices this leaves the block's last entry invariant, so only two bounded permutations are needed, even after years of queue positions.

Chapters span3,4,5 segments, shuffled within12-segment groups. A shared motif (six families), initial register (E4/G4/A4/C5/E5), rhythm family order and one of three restrained GM palettes persists through each chapter. Arrival/release are spare, middle develops/blooms, and sparse sections leave occasional two-bar melodic breaths over sustained harmony. Harmony still changes between segments. Keep the natural A-minor scale, pitch36–84, velocity<=60, bounded melodic steps and safe note release. At default120-second segments a chapter lasts6–10minutes; this is a segment-order arc, not a wall-clock or confirmed-on-air schedule.

Palettes: warm pad/acoustic bass/electric piano(89,32,4), halo pad/bass/electric piano(94,32,4), warm pad/bass/vibraphone(89,32,11). Introduce no new asset/model/license dependency. Compare actual renders before rollout; retain the existing audio quality gates and crossfade behavior.

## Integration and rollback

`compose(..., arrangement=None)` and `midi(..., programs=None)` keep legacy defaults. `render(..., arrangement=None)` uses explicit plans and adds the full versioned arrangement metadata to returned analysis. Renderer reconstructs plans from saved job seed/ID. Cached fallback stays independent.

`MUSICAL_MEMORY=1` enables this for queued renders by default; `0` selects legacy independent arrangements for a quick operator rollback. Strict0/1 validation, no new schema. Existing ready WAVs remain immutable and play before new renders.

Preview keeps existing `--seed` behavior. Add mutually exclusive `--station-seed` with required positive `--position` for auditioning a planned segment. Its actual piece seed is station seed+position, with filename preview-position and arrangement metadata in output. This explicit preview mode can audition plans regardless of the renderer flag.

## Evidence and boundaries

Tests: determinism across out-of-order/huge positions and independent seeds, balanced/nonrepeating harmonic blocks, varying chapter boundaries/shared themes/stages, safe notes/MIDI palettes, legacy MIDI compatibility, Config toggle, renderer reconstruction from saved jobs and CLI validation. Compare actual composed score distributions over the same256 positions to the baseline. Render all palettes/stages, make a real multi-segment crossfade capture, inspect duration/peak/loudness/gaps/render cost, then roll out workers only after passing checks; preserve data/Icecast/broadcaster and keep rollback available.

One independent final reviewer; reproduce/fix Important/Critical findings, full green suite, scoped PR and real current-head CI before merge. Update journal with measured changes and limitations. No claim that a lower repetition metric proves better music; user listening acceptance remains open. Failures/skipped IDs can skip chapter parts and weaken consecutive-position guarantees on air. Public HTTPS/VPS/off-host recovery are separate remaining work.
