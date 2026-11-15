# Broadcast chapter context implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show a truthful musical chapter sentence from actual broadcast metadata without changing the music or exposing private status.

**Architecture:** Annotate dispatched requests with safe labels; existing Liquidsoap output forwards metadata to Icecast. A filtered XSL response and exact Caddy route feed an optional bounded browser poller. Existing five-service architecture and private mount policy stay intact.

**Tech Stack:** Python/sqlite3, Liquidsoap2.1, Icecast/libxslt, Caddy, plain JS, existing Node/browser harness.

**Spec:** `docs/superpowers/specs/2026-11-15-broadcast-context-design.md`

## Global constraints

- Store.next_track() keeps its string/empty-string dispatch behavior; new next_track_info() returns path/analysis from the same transaction. No schema/PCM/MIDI changes.
- Analysis max8192 characters; controlled version1/2 chapter/stage labels only; quoted annotations/fallback and --annotate only for next.
- Public JSON has exactly version/available/title, selects only /radio.mp3, title max160 codepoints, properly escaped. No private mount/statistics exposure or extra service/port.
- Poll only playing+visible: >=10000ms between starts,3000ms deadline,4096 streamed bytes,15000ms display freshness. Hide/abort/invalidate on disable; never manipulate audio or timer.
- Preserve existing visual tokens/layout, textContent-only display, generic MediaSession/no-JS fallback; main audio unchanged during development.

## Review focus

- Dispatch prefetch must not masquerade as current output: Task1 actual two-track metadata timing test.
- Malformed/huge/private analysis must not become public text: Task1 pure-label and dispatch compatibility tests.
- Escaping/other mounts must not widen the public endpoint: Task1 real XSL server cases and Task3 proxy restrictions.
- Late aborted responses/rapid toggles/hidden pages must not leak polling or stale labels: Task2 fake-clock/readable-stream tests.
- Optional metadata failure must not interrupt playback/timer or break mobile UI: Task3 actual browser failure/XSS/layout checks.

### Task 1: Safe labels and existing-server public context

**Files:** Create radio/labels.py, deploy/broadcast-context-json.xsl, tests/test_broadcast_context.py, tests/test_context_stream.py. Modify radio/store.py, radio/__main__.py, deploy/radio.liq, Dockerfile, web/site.caddy.

**Interfaces:** Store.next_track_info()->dict|None path/analysis; legacy next_track()->str. title_for_analysis(str|None)->str; annotated_request(path:str,analysis:str|None)->str. CLI next --annotate. GET/HEAD /broadcast.json -> version1/available bool/title string.

- [x] Write failing tests for legacy dispatch path/empty/missing-file/served semantics, same-row saved metadata, exact stage/palette labels, invalid/bool/huge fields, default generic labels, absolute/control-safe quoted URI and CLI flag validation.
- [x] Add failing actual-tool tests: request prefetch vs output metadata timing, explicit fallback label, missing/other mount, quote/backslash/tab/newline/Unicode escaping and160-character truncation. Skip only unavailable host audio tools; full image must exercise them.
- [x] Run focused tests and inspect expected failures, then implement interfaces preserving old dispatch and note generation. Import installed escape-string, exact route, no new public/private mounts.
- [x] Run focused tests, actual media suite and Liquidsoap --check. Verify metadata probe/current request frames before committing the deliverable.

### Task 2: Bounded optional listener context

**Files:** Create web/public/broadcast-context.js, web/tests/broadcast-context.test.mjs; modify web/public/app.js,index.html,style.css and web/tests/unit.mjs.

**Interfaces:** createBroadcastContext({fetcher,now,schedule,cancel,onChange})->{setEnabled,dispose}; onChange receives string|null, URL fixed /broadcast.json.

- [x] Write failing deterministic tests using fake clock/Response streams for no idle requests, playing/visible enable, cooldown across pause/resume,3s timeout,4KiB limit, schema/Unicode bounds, unavailable/error hide,15s stale resume, abort cleanup and late-response generation guard.
- [x] Run RED tests; implement controller with one owned request/timer, bounded reader and exact prefix stripping. No audio/MediaSession actions. Disable on pagehide with resumable BFCache behavior.
- [x] Integrate hidden paragraph/title/note with textContent; preserve accessible focus and current palette/body type, no extra announcements/cards/animation. Run all listener tests and commit.

### Task 3: Full-stack experience and measured journal

**Files:** Modify web/tests/browser.mjs, .github/workflows/ci.yml, scripts/production-smoke.py as required for real public context; update docs/product-journal.md, docs/architecture.md, HANDOFF.md and an evidence receipt.

**Interfaces:** Existing private CI project and isolated TLS smoke. New exact proxy route must return only selected context while admin/status/data/raw-XSL paths remain unavailable publicly.

- [x] Extend actual stack tests to fetch context through Caddy/TLS, compare label transitions with Liquidsoap output rather than queue rows, and validate restricted routes. Exercise full five-role secure profile, no private data mounts.
- [x] Browser-test actual label, pause/hidden cancellation, failed/malicious metadata while audio/timer keep working,320/390px and desktop, no-JS/reduced-motion. Capture and visually inspect actual screenshots.
- [x] Build isolated backend/web candidate images; run full real-media/listener/browser and hardened TLS checks. Record concrete timing/privacy/behavior evidence and scope, with no listening/sample-alignment claims.
- [x] Update journal/current-state docs and commit the verified candidate. Keep current main stream intact; any later source/Icecast/gateway maintenance rollout gets its own preservation/reconnect evidence.

## Delivery gates

- [x] One fresh independent whole-branch review; one reproduced/verified Important/Critical fix pass; full green required checks.
- [ ] Scoped PR and all four actual final-head/current-base CI checks before merge; primary fast-forward and honest source-vs-live delivery state.
