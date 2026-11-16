#!/usr/bin/env bash
# Restore test: backs up a database, restores it into a new one and compares
# every table, row by row, and every media file. Runs against a database you
# name (e.g. a staging copy) and never changes it.
#
#   test-restore.sh
#
# Environment: the same as backup.sh, plus BACKUP_AGE_IDENTITY (private key)
# and RESTORE_TEST_DB (name of the temporary database, dropped at the end).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
: "${RESTORE_TEST_DB:?set RESTORE_TEST_DB}"
work="$(mktemp -d)"
trap 'rm -rf "$work"; dropdb --no-password --if-exists "$RESTORE_TEST_DB"' EXIT

table_digests() {
  # One line per table: name, rows and the md5 of all rows in a fixed order
  local db="$1"
  psql --no-password --dbname="$db" --tuples-only --no-align --command="
    SELECT format('SELECT %L || '' '' || count(*) || '' '' || coalesce(md5(string_agg(t::text, '','' ORDER BY t::text)), ''-'') FROM %I.%I t;',
                  table_schema || '.' || table_name, table_schema, table_name)
    FROM information_schema.tables
    WHERE table_type = 'BASE TABLE' AND table_schema NOT IN ('pg_catalog', 'information_schema')
    ORDER BY 1" \
  | psql --no-password --dbname="$db" --tuples-only --no-align
}

BACKUP_DIR="$work/backups" BACKUP_KEEP_DAYS=0 "$here/backup.sh"
name="$(basename "$(ls "$work"/backups/*.sha256)" .sha256)"

# The files are age-encrypted, with no readable data
for file in "$work"/backups/*.age; do
  if [ "$(head -c 21 "$file")" != 'age-encryption.org/v1' ]; then
    echo "FAIL: $file is not an age file" >&2
    exit 1
  fi
done

RESTORE_MEDIA_TO="$work/media" "$here/restore.sh" "$work/backups" "$name" "$RESTORE_TEST_DB"

table_digests "$PGDATABASE" > "$work/original.txt"
table_digests "$RESTORE_TEST_DB" > "$work/restored.txt"
if ! diff -u "$work/original.txt" "$work/restored.txt"; then
  echo "FAIL: the restored database differs" >&2
  exit 1
fi
echo "OK: $(wc -l < "$work/original.txt") tables identical ($(awk '{s+=$2} END {print s}' "$work/original.txt") rows)"

for dir in ${BACKUP_MEDIA_DIRS:-}; do
  [ -d "$dir" ] || continue
  original="$(cd "$dir" && find . -type f -exec sha256sum {} + | sort)"
  restored="$(cd "$work/media/${dir#/}" && find . -type f -exec sha256sum {} + | sort)"
  if [ "$original" != "$restored" ]; then
    echo "FAIL: media files in $dir differ" >&2
    exit 1
  fi
  echo "OK: $(echo "$original" | grep -c . ) files identical in $dir"
done

# A wrong key can't open the backup
age-keygen -o "$work/other.key" 2>/dev/null
if age --decrypt -i "$work/other.key" "$work/backups/${name}.db.age" > /dev/null 2>&1; then
  echo "FAIL: another key opened the backup" >&2
  exit 1
fi
echo "OK: another key can't open the backup"

# A damaged file is caught before restoring
printf 'x' >> "$work/backups/${name}.db.age"
if (cd "$work/backups" && sha256sum -c "${name}.sha256") > /dev/null 2>&1; then
  echo "FAIL: a damaged backup passed the checksum" >&2
  exit 1
fi
echo "OK: a damaged backup is refused by the checksum"
