# Backup and recovery

These commands use the existing Docker image and run backup/restore without networking or Docker access inside the container. They assume the default Compose project/volume, `generative-radio_radio-data`. For another project, substitute its actual data volume. Run from the repository root. Build the image from the commit you intend to operate (`docker compose build`); do not recreate running services just to make a backup.

## Create and verify an online backup

The source volume is read-only. SQLite's backup API captures committed WAL data while the station keeps playing. The bundle contains the snapshot database, cached fallback, completed queued/dispatched WAVs and available MIDI for snapshot jobs. Incomplete renders, health reports, logs and credentials are excluded. Retention races retry a fresh snapshot up to three times. A missing file after all attempts fails the backup.

```sh
RADIO_SNAPSHOT=station-$(date -u +%Y%m%dT%H%M%SZ)
docker volume create radio-backups
docker run --rm --network none \
  --mount type=volume,source=generative-radio_radio-data,target=/source,readonly \
  --mount type=volume,source=radio-backups,target=/data \
  generative-radio:local python -m radio.backup create \
  "/data/$RADIO_SNAPSHOT" --data /source

docker run --rm --network none \
  --mount type=volume,source=radio-backups,target=/data,readonly \
  generative-radio:local python -m radio.backup verify "/data/$RADIO_SNAPSHOT"
```

The image's non-root UID 10001 owns `/data`, including a newly initialized named volume at that path. Existing backup volumes/bind mounts must be writable by that UID. Each snapshot needs a new name: an existing destination is never overwritten. Allow approximately the current retained audio size per snapshot (about 1 GB in local tests), plus space for a restore. The final `manifest.json` marks completion; a directory without a successfully verified manifest is not a backup. If a container/host is killed mid-copy, use a new snapshot name and investigate the incomplete directory rather than treating it as complete.

Verify checks all SHA-256 hashes/sizes, file paths, absence of symlinks/unlisted files, SQLite integrity/schema/job sequence and audio required by the snapshot queue. It returns nonzero on a damaged/incomplete bundle. Never schedule deletion of older verified copies merely because a new backup directory exists.

On a Python host with access to an offline data directory, the same interface is:

```sh
python -m radio.backup create /backups/unique-name --data /path/to/station
python -m radio.backup verify /backups/unique-name
python -m radio.backup restore /backups/unique-name --data /path/to/empty-station
```

## Keep a copy off-host

A named volume on the same machine does not protect against host loss. Export only your own completed snapshot, then transfer it over SSH to storage you control:

```sh
docker run --rm --network none \
  --mount type=volume,source=radio-backups,target=/data,readonly \
  generative-radio:local tar -C /data -czf - "$RADIO_SNAPSHOT" \
  > "$RADIO_SNAPSHOT.tar.gz"
sha256sum "$RADIO_SNAPSHOT.tar.gz" > "$RADIO_SNAPSHOT.tar.gz.sha256"
# Replace backup-user@backup-host and the path with your actual destination.
rsync -av --partial "$RADIO_SNAPSHOT.tar.gz" "$RADIO_SNAPSHOT.tar.gz.sha256" \
  backup-user@backup-host:/private/radio-backups/
```

Check the archive checksum after transfer; run bundle verification after importing it on the recovery host. Store copies on encrypted storage with restricted access. Checksums detect damage, not malicious replacement; protect the manifest and the archive as well as the audio. No storage provider or automatic upload is configured by these commands.

Record the repository commit and exact image ID beside the backup (`git rev-parse HEAD` and `docker image inspect generative-radio:local --format '{{.Id}}'`). Preserve the deployment `.env`/secrets separately in an encrypted secret store; they are intentionally absent from this bundle. Preserve any custom SoundFont and its license/provenance separately. A queue backup alone is not a full server backup.

Keep several independently verified recovery points (for example seven daily and four weekly copies), monitor free space, and practice a restore. Choose retention for your storage budget; this tool does not delete backups automatically.

## Restore into a new volume

Use a fresh volume; never restore over a running station's data. Existing nonempty destinations are rejected. An exclusive `.restore-in-progress` reservation prevents concurrent restores from writing into the same empty volume. The backup is mounted read-only and is never edited. Already-dispatched jobs remain dispatched; interrupted renders become pending with a fresh retry budget. Stale worker heartbeats are removed; job IDs/seeds continue rather than repeating old segments. Saved paths are rewritten to the new data root.

If importing one of your own exported archives on a new host, first create the backup volume and unpack it without networking or privileged mounts:

```sh
docker volume create radio-backups
docker run --rm -i --network none \
  --mount type=volume,source=radio-backups,target=/data \
  generative-radio:local tar -xzf - -C /data < "$RADIO_SNAPSHOT.tar.gz"
# Run the verify command above before continuing.
```

Then restore:

```sh
docker volume create radio-restored
docker run --rm --network none \
  --mount type=volume,source=radio-backups,target=/backups,readonly \
  --mount type=volume,source=radio-restored,target=/data \
  generative-radio:local python -m radio.backup restore \
  "/backups/$RADIO_SNAPSHOT" --data /data

docker run --rm --network none \
  --mount type=volume,source=radio-restored,target=/data \
  generative-radio:local python -m radio status
```

Verify a ready track's audio and render a new preview using this isolated volume before switching playback. `python -m radio next` consumes a ready job; do this only on the isolated restore when testing. Rendering `python -m radio preview --seconds 20` verifies the toolchain without contacting Icecast. The module resets leases for recovery; it does not merge queues or reconstruct exact on-air history.

A copy/validation error exits nonzero. Caught errors remove staged/published restore files; a hard kill may leave the `.restore-in-progress` reservation and/or `.restore-*` staging. Do not start services against an interrupted restore. Keep the source backup and use another fresh volume, or inspect and clear only the failed restore volume before retrying. Keep the old live data until successful recovery has been verified.

To switch Compose to the verified volume, create an override such as `/tmp/radio-restored.compose.yaml`:

```yaml
volumes:
  radio-data:
    external: true
    name: radio-restored
```

Check `docker compose -f compose.yaml -f /tmp/radio-restored.compose.yaml config --quiet`. In an announced maintenance window, stop the station and start with that override:

```sh
docker compose stop
docker compose -f compose.yaml -f /tmp/radio-restored.compose.yaml \
  up -d --wait --wait-timeout 180
```

Expect listeners to reconnect. Check every service's health, `python -m radio status`, the broadcaster health report, logs and a fresh decoded recording. Keep using the override in subsequent commands; otherwise Compose targets the original volume again. Store the chosen override alongside deployment configuration when making it permanent. Never run `down -v` as a recovery step: it can remove the data you need for rollback.

For rollback, stop services using the restore override, then start with the original Compose configuration and the preserved old volume/image. Image upgrades and public VPS/HTTPS deployment will have a separate runbook; no target host has yet been selected.
