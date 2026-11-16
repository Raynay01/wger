#!/usr/bin/env bash
# Restores an encrypted ALMOVA backup into a NEW database (never over an
# existing one) and, optionally, its media files into a separate folder.
#
#   restore.sh <backup dir> <backup name, e.g. almova-20261115T030000Z> <new database>
#
# Environment:
#   BACKUP_AGE_IDENTITY   file with the age private key
#   PGHOST, PGPORT, PGUSER, PGPASSWORD   a role allowed to create databases
#   RESTORE_MEDIA_TO      empty folder for the media files (optional)
set -euo pipefail
umask 077

dir="${1:?backup dir}"
name="${2:?backup name}"
target="${3:?name of the new database}"
: "${BACKUP_AGE_IDENTITY:?set BACKUP_AGE_IDENTITY to the private key file}"

cd "$dir"
echo "Checking the checksums"
sha256sum -c "${name}.sha256"

if psql --no-password --dbname=postgres --tuples-only --no-align \
  --command="SELECT 1 FROM pg_database WHERE datname = '${target//\'/}'" | grep -q 1; then
  echo "Database ${target} exists. Restoring only goes into a new database." >&2
  exit 1
fi

createdb --no-password "$target"
age --decrypt -i "$BACKUP_AGE_IDENTITY" "${name}.db.age" \
  | pg_restore --no-password --dbname="$target" --no-owner --no-privileges --exit-on-error
echo "Database restored into ${target}"

if [ -n "${RESTORE_MEDIA_TO:-}" ] && [ -f "${name}.media.tar.gz.age" ]; then
  mkdir -p "$RESTORE_MEDIA_TO"
  if [ -n "$(ls -A "$RESTORE_MEDIA_TO")" ]; then
    echo "${RESTORE_MEDIA_TO} is not empty." >&2
    exit 1
  fi
  age --decrypt -i "$BACKUP_AGE_IDENTITY" "${name}.media.tar.gz.age" \
    | tar -xzf - -C "$RESTORE_MEDIA_TO"
  echo "Media files restored into ${RESTORE_MEDIA_TO}"
fi
