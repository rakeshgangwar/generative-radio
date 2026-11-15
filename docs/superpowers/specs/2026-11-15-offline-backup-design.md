# Back up a stopped station without writing its source

Engineering design under standing implementation/PR/CI-cleared merge authority.
The default online backup remains a consistent SQLite backup of the live source.

## Observed failure and safe boundary

A closed WAL database can have no -wal/-shm files while retaining WAL mode in its
header. The shipped create command on a fully read-only source mount then fails
`unable to open database file`, because SQLite cannot initialize its sidecars.
A tiny actual station-schema fixture reproduced this in the current image. The
live musical rollout recovered without changing broadcaster/Icecast/web; this
fix must not require touching live station containers or volumes.

Never silently retry with immutable=1: that can ignore committed WAL data. Do not
make the original source writable to make a backup. Keep normal online behavior;
add an explicit offline path for data whose writers the operator has stopped.

## Interface and behavior

`create_backup(data, destination, *, offline=False)` preserves current callers.
Only `radio.backup create` accepts `--offline`. Help/runbook require all database
writers stopped, including composer, renderer and broadcaster (dispatch writes
the queue). The flag is an operator assertion, not a command that stops services.
Do not claim that unchanged file stats prove an active station is offline.

Offline mode copies radio.sqlite and any present radio.sqlite-wal or
radio.sqlite-journal into a private temporary directory inside the staging area.
Reject symlink/nonregular source database or sidecars. Do not copy source -shm:
SQLite initializes private sidecars and performs recovery there. Open the private
copy writable, use SQLite's existing backup API into the normal final database,
then close/remove the private recovery area before manifest enumeration. Thus
committed WAL frames survive, and the final bundle stays in the existing format.

Compare source identity/size/mtime before and after copying to reject observed
concurrent changes, including appearing/disappearing sidecars. This is a safeguard,
not synchronization; the caller must ensure no writers. Original source names and
bytes remain unchanged; no source SHM is created. Existing exclusive destinations,
retry/manifest publication, quality/integrity checks, path safety and isolated
restore semantics remain intact. No partial failed bundle is reported successful.

Default online failure should remain nonzero and provide actionable guidance if
a read-only WAL source cannot open; never turn that failure into an unverified
success. Document mode selection rather than weakening SQLite recovery.

## Evidence

Test closed WAL sources without sidecars, a copied crash-like WAL with committed
rows absent from the main database, exact source file/hash preservation, optional
sidecars, symlink rejection, detected concurrent changes, CLI propagation/defaults,
exclusive destination cleanup and existing online backup/restore. Exercise actual
read-only mounts as non-root, verify/restore the bundle, and validate real rendered
audio from an isolated restored station. The live station/test stays untouched.
One independent final review and all four real current-head CI checks gate merge.
