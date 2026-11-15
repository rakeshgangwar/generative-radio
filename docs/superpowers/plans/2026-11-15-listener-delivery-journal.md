# Listener Delivery Journal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline; one fresh factual documentation review.

**Goal:** Record actual PR29 local delivery and refresh the journal's opening/current handoff.

**Architecture:** Documentation and a source-linked receipt only, using immutable raw acceptance evidence. Preserve historical entries and distinguish proposed ideas from shipped features.

**Tech Stack:** Markdown, JSON, existing Git/CI; no application changes.

**Spec:** docs/superpowers/specs/2026-11-15-listener-delivery-journal-design.md

## Global Constraints

- No application, runtime, music or deployment changes.
- Source every measured claim from actual CI/merge/rollout/Firefox artifacts.
- Recovery confirmation includes health waiting; no gapless/exact audible interruption claim.
- Direct loopback core recording is not independent-host or human acceptance.
- TimGM/version2 remains live; volume memory is proposed, not implemented.
- Public/offhost/device/Safari/AT/human gates remain open; preserve historical entries.

## Review Focus

- Summary must describe currently deployedPR29, not olderPR25 or unshipped ideas.
- Core identity preservation is scoped to the measured web-only replacement.
- Confirmation timing and audio thresholds must match raw artifacts without overclaim.
- Receipt hashes, CI/head/base and source assets must identify the actual delivery.
- Proposed volume memory must not read as implemented or change sleep/autoplay behavior.

### Task 1: Publish the factual delivery and current direction

**Files:** Create docs/evidence/native-listener-polish-delivery-20261115.json; update HANDOFF.md, docs/product-journal.md, docs/product-readiness.md and completed native-polish plan; add this spec/plan.
**Interfaces:** No app interfaces change; receipt names exact CI/head/base/merge, before/after services,60s corecapture, recovery scope, liveFirefox and8asset hashes.

- [x] Validate raw artifacts and build the delivery receipt with explicit scope/limits.
- [x] Refresh opening/current summaries and append a dated delivered entry; preserve history.
- [x] Validate Markdown relative links, JSON/receipt equivalence and gitdiffcheck; do not add mirrored tests for factual prose.
- [ ] One fresh documentation-only review; fix Important/Critical claims in one pass with raw proof, defer Minor with costs. No rereview of app code.
- [ ] Scoped docs PR, require allfour actual latest final-head/current-base CI jobs with actualFirefox success; mergeonlyonclearance. No runtime redeployment.
