#!/bin/sh
set -eu

: "${DATABASE_URL:?DATABASE_URL must point to the source PostgreSQL database}"

backup_dir="${BACKUP_DIR:-./backups}"
mkdir -p "$backup_dir"
stamp="$(date -u +%Y%m%d-%H%M%S)"
backup_file="$backup_dir/automind-$stamp.dump"

pg_dump "$DATABASE_URL" \
  --format=custom \
  --no-owner \
  --no-privileges \
  --file="$backup_file"

pg_restore --list "$backup_file" >/dev/null
sha256sum "$backup_file" >"$backup_file.sha256"
printf 'Backup verified: %s\n' "$backup_file"
