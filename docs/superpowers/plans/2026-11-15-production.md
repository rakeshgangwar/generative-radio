# Production Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Secure, repeatable production setup with locally verified TLS and a complete operator path.
**Architecture:** Host stdlib CLI, strict resolved Compose preflight, optional hardened production profile, shared Caddy routes and persistent certificate volume. No cloud/provider coupling.
**Tech Stack:** Python>=3.11, Docker Compose>=2.24.4, existing Caddy/FFmpeg/curl.
**Spec:** `docs/superpowers/specs/2026-11-15-production-design.md`

## Global Constraints

No public deployment/purchase/current-machine credential or trust-store changes. Generated env files private/never overwritten/never logged or built. Five known roles UID10001/read-only/cap-drop/NNP; only web public80/443, Icecast loopback8000, no web queue/Docker mounts. Internal ports8080/8443, health8081. Preserve primary live station and same active musical capture/monitor. Public target and listening remain open. Native execution, one final independent review, CI-cleared PR merge.

## Review Focus

- Dotenv interpolation/host overrides must be checked in resolved config, not guessed from file text.
- Existing/broken-symlink env files must never be overwritten; failures must not disclose secrets.
- Read-only/non-root/certificate persistence must work in real containers, not just YAML.
- TLS verification must validate hostname/CA and reject untrusted certs; probes must bound DNS/stream time.
- Deployment failure must leave data/services inspectable and never start after failed preflight.

### Task 1: Deliver production configuration and operator commands

**Files:** Create `radio/production.py`, `compose.production.yaml`, `web/{Caddyfile.production,site.caddy}`, `tests/test_production.py`, `scripts/production-smoke.py`, `docs/deployment.md`; modify dev Caddyfile/Dockerfile, Config/watchdog pure parser access, ignore files, CI/docs/journal, capture TLS checks if reproduced.
**Interfaces:** `initialize(env_file,domain,station_seed=None)`, `validate_config(config)`, `preflight(env_file,repo,project=None)`, `probe_https(base_url,ca_file=None)`. CLI init/check/up/status. `Config.from_env(mapping)` pure, existing load still creates data; `Options.load(env=None)` backward compatible/pure.

- [x] Write failing generator/domain/private-file/policy/order/diagnostic tests and capture existing behavior; expected missing module RED. Define a representative resolved model for policy tests.
- [x] Implement host commands, pure parsers and production/shared Caddy configuration; unit suite GREEN. Validate real resolved config without exposing secrets.
- [x] Build separate candidate tags; run full isolated production/TLS smoke with loopback ports/internal CA, capture/decode audio and persistence/restart, inspect hardening. Keep core live IDs unchanged. Reproduce/fix transport trust defects with RED→GREEN if found.
- [x] Update CI and deployment runbook with exact setup, DNS/ports, health/TLS checks, reboot, upgrade/rollback/backup and recovery commands. Journal records actual musical rollout plus package evidence/limits.
- [ ] Independent whole-branch security/correctness review, one fix pass with regressions; current-head CI then merge. Keep actual target deployment and active musical soak completion as separate work. Primary checkout's running capture script remains unchanged until its process completes.
