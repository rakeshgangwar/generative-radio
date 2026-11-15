# Resting-profile experiment

Compare at [localhost:18095](http://localhost:18095). Pause the live station or other
audio first, then play one version at a time. The page pauses its other player
when you start one. Native controls also work without JavaScript; in that mode,
pause the other track yourself. Compare a few minutes and chapter transitions,
then return later for a longer listen.

Both versions cover the same three complete chapters (seed 42, positions 1–12),
last 23m05s and use the current TimGM SoundFont. The resting candidate uses 52 BPM
instead of 60, the existing spare density profile throughout, and one fixed warm
pad/acoustic-bass/electric-piano palette. Motif and harmonic sequence remain, while
the slower pulse changes note and chord timing. This is a mood comparison, not an
identical-note or phase-aligned A/B. It tests a deliberately calmer profile rather
than claiming that slower music fixes repetition.

Both measured masters are −22.13 LUFS. Only attenuation was used for matching;
true peaks are −8.39 dBFS (current) and −8.50 dBFS (resting). Neither had silence
at −50 dB lasting two seconds. In a separate 256-position score sample, mean lead
attacks fell from 31.64 to 20.89 per two-minute segment; those counts are not a
listening verdict.

The read-only preview passed actual Chromium playback, seeking, one-at-a-time
controls, 320/390px layouts, byte ranges and JavaScript-disabled native playback.
The experiment used a separate CPU-limited container without networking or a live
station-data mount. All five live service identities/images/start/restart/OOM
values were preserved, and the post-render station sample was healthy.

This is a retained local prototype, not an installed profile CLI, a new station
channel, or automatic time-of-day scheduling. The source operator script and
measurements remain under the local evidence directory in the [receipt](evidence/resting-profile-experiment-20261115.json).
A reusable bounded audition command is a possible next implementation if this
direction proves useful. The v2 TimGM broadcast stays unchanged while listening
preference is unresolved. Physical-device, Safari, assistive-technology, public
and off-host acceptance remain open.
