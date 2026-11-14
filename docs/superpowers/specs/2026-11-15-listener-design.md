# A listener's front door

Engineering design under the active product goal, creative delegation and journal direction. No separate human approval claimed. Local-only delivery first; no new hosted Site or paid infrastructure.

## Purpose and approach

Turn a bare stream URL into an inviting, accessible place to listen. One station, one obvious start/stop control, volume, and honest connection/recovery feedback. No accounts, invented track metadata, automatic playback, decorative audio meters or administrative controls.

Use buildless HTML/CSS/ES modules and the browser's native audio element. A static page alone would require a cross-origin/configured stream URL; choose a small optional Caddy service that serves the page and proxies only `/radio.mp3` from existing Icecast. A framework/application server is unnecessary for this interaction. Existing four core roles/volumes remain unchanged. Optional web binds 127.0.0.1:8080, runs non-root/read-only without Docker access. Public HTTPS/domain deployment is a later iteration.

## Visual direction

A quiet blue-and-silver radio dial, restrained typography and one memorable circular line illustration. Palette: mist #d8e3ed, ink #17344b, slate #4a6275, pale blue #c4d3e0, sea #275a7c, paper #f6f9fb. Large book-style system serif for the short headline, system sans for controls/body. No external fonts/assets/analytics. Desktop two-column listening space; mobile stacks heading/dial/controls with no horizontal overflow at 320px. Geometry is atmosphere, not a visualization of measured audio. Motion only during playback and disabled for reduced-motion preference. Controls have visible keyboard focus, comfortable targets, real labels and status announcements.

```
Generative Radio                        About the station

A little room                  [quiet radio-dial artwork]
for listening.
Original ambient music,
continuously unfolding.

[Start listening]   Ready when you are
Volume [--------------]

About: join where the station is now; new arrangements rendered ahead.
Product journal / Source / Open audio stream
```

Review against brief: a generic dashboard/card layout does not fit long listening. Keep the page centered on playback, with no feature grid, counters or invented activity. The blue dial grounds it in radio while leaving the music room.

## Behavior

No stream request until explicit intent. Player states: idle, connecting, playing, buffering, retrying, paused, error. Playing requires the real media playing event; promise resolution alone is not proof. Pause stops/relinquishes the current live connection and cancels all recovery work. Resume joins live with a fresh URL. Connection/buffering deadline 15s. Lost/ended/error streams get three automatic attempts after 1s,3s,8s; exhaustion offers explicit retry. A stable playing connection resets the retry budget only after 30s, so rapid connect/drop loops remain bounded. Permission rejection requires another user gesture rather than automatic retries. Handle late play promises/events, remote pause, disposal and offline failures without reviving paused audio.

Volume is 0–100%, with a labeled control. Detect platforms that ignore programmatic volume and explain using device volume; do not imply a broken slider works. Media Session play/pause/stop when available; no fabricated progress for an endless live stream. Keep source/journal and direct stream links usable; no-JS gets native audio controls.

## Evidence

Test controller behavior with native Node tests/fake media and deterministic timers, including cancellation/races/bounded recovery and stable reset. Test actual page via browser against the proxy: play, pause, volume, dropped connection/retry, small viewport, keyboard/a11y, reduced motion and console errors. Validate actual Caddy config/non-root image and decoded proxied MP3. The local core station and active hour soak must not be recreated. CI includes JS tests and a real web proxy smoke test. One independent final reviewer before PR readiness; merge only actual current-head green CI. Update the product journal with what exists and remaining public deployment/musical work.
