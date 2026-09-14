#!/bin/sh
set -eu

: "${BACKUP_FILE:?BACKUP_FILE must name a PostgreSQL custom-format dump}"

test -f "$BACKUP_FILE"
test -f "$BACKUP_FILE.sha256"
sha256sum -c "$BACKUP_FILE.sha256"
pg_restore --list "$BACKUP_FILE" >/dev/null
printf 'Backup checksum and archive catalog verified: %s\n' "$BACKUP_FILE"
