# Production deployment package

Engineering work under the active product goal and standing autonomous implementation/PR/merge policy. No separate human design approval claimed. Actual VPS/domain/access are missing: build and test the package, without publishing this machine, buying infrastructure or changing its credentials/trust store.

## Approach

Keep the existing Docker station and optional Caddy listener. Add an explicit production override plus `python -m radio.production {init,check,up,status}` on the repository host. This is simpler than choosing a cloud vendor or adding a management service before a deployment target exists. Local development remains HTTP/loopback; production is opt-in.

The generator validates an ASCII DNS hostname, rejects IPs/URLs/local/reserved example names, writes distinct random URL-safe source/admin credentials and a recoverable station seed. Atomic private temporary-file+exclusive hard-link publication gives complete mode600 output without overwriting an existing file/symlink. Generated `.env.*` files and temporary secrets are ignored by Git and Docker build contexts. Never print credentials.

Preflight validates the private regular env file, Compose>=2.24.4, resolved three-file Compose JSON and public/private boundaries. Do not parse/evaluate dotenv as shell. Reject missing/placeholder/weak/equal credentials, inconsistent source keys, unknown exposed services/ports, privileged/host namespaces, unsafe mounts, root users or missing read-only/cap-drop/no-new-privileges. Validate music/watchdog configuration using side-effect-free runtime parsers. Diagnostics identify the problem without including config/credential values. Check is read-only; no containers start before success.

## Runtime profile

All five production roles run UID/GID10001 with read-only roots, all capabilities dropped and no-new-privileges; writable station volume and bounded noexec/nosuid `/tmp` tmpfs support core processes. Web has only its own persistent certificate volume, never queue/audio/Docker mounts. Icecast remains loopback8000, with no admin/status path proxied. Only web publishes public TCP80/443, replacing dev8080 through Compose `!override` (minimum2.24.4).

Share static/audio routes between dev/prod Caddyfiles. Caddy uses unprivileged internal HTTP8080/HTTPS8443, mapped from external80/443, plus unpublished health8081. Automatic HTTPS, canonical443 redirects, admin off, config persistence off, h1/h2 only. `skip_install_trust` prevents internal-CA test trust installation. Create certificate directories owned by10001 before dropping image user; persist `/data` for renewal/restart. No system trust modifications.

Up builds/starts with health wait, then verifies public page and stream through bounded certificate-validating curl requests. If HTTPS fails, report incomplete verification and leave containers/data for diagnosis; no blind rollback/retry. Status reports Compose health without exposing env. No command emits resolved configuration or raw secret-bearing Docker diagnostics.

## Validation and delivery

Unit tests cover credentials/atomic refusal/permissions/safe diagnostics/domain, pure config parsing, resolved policy and validation-before-start. Real Compose config rejects missing secrets/domain. Isolated full production stack uses loopback test ports and localhost's internal CA, while a separately validated public model proves policy. Verify cert authenticity with explicit trusted test CA (no -k), HTTPS page/MP3, canonical HTTP redirect, admin/status404, all five non-root/read-only services healthy and certificate persistence after web recreation. Run the actual capture helper over trusted TLS and reject untrusted TLS; fix any verified transport issue rather than assuming certificate validation.

Maintain existing HTTP/browser tests; add production/TLS smoke checks to CI. Run one independent final security/correctness review and current-head CI before PR merge. Keep live station and active two-hour musical capture untouched in the primary checkout. Public DNS/ACME issuance, target capacity/reboot and off-host recovery remain unverified until the user supplies destinations.

Primary references: [Caddy global ports/trust options](https://caddyserver.com/docs/caddyfile/options), [automatic HTTPS/storage](https://caddyserver.com/docs/automatic-https), [Compose replacement rules/version](https://docs.docker.com/reference/compose-file/merge/).
