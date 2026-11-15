#!/usr/bin/env bash
# Encrypted backup of the ALMOVA database and media files.
#
# The dump and the archives are streamed into age, so no unencrypted copy
# touches the disk. The server only holds the public key(s): restoring needs
# the private key, kept elsewhere (see README.md).
#
# Environment:
#   BACKUP_AGE_RECIPIENTS  age public keys (age1...), separated by spaces or commas
#   BACKUP_DIR             where the encrypted files go
#   BACKUP_KEEP_DAYS       delete backups older than this (default 30, 0 keeps all)
#   PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE   the database (libpq variables)
#   BACKUP_MEDIA_DIRS      folders to archive, separated by spaces, e.g. the
#                          media root and DJANGO_PRIVATE_MEDIA_ROOT
set -euo pipefail
umask 077

: "${BACKUP_AGE_RECIPIENTS:?set BACKUP_AGE_RECIPIENTS to the age public key(s)}"
: "${BACKUP_DIR:?set BACKUP_DIR}"
: "${PGDATABASE:?set PGDATABASE}"
KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"

recipients=()
for key in ${BACKUP_AGE_RECIPIENTS//,/ }; do
  recipients+=(-r "$key")
done

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
name="almova-${stamp}"
mkdir -p "$BACKUP_DIR"
cd "$BACKUP_DIR"

# Written under a temporary name, renamed only when complete
pg_dump --format=custom --compress=6 --no-password \
  | age "${recipients[@]}" -o "${name}.db.age.part"
mv "${name}.db.age.part" "${name}.db.age"
files=("${name}.db.age")

if [ -n "${BACKUP_MEDIA_DIRS:-}" ]; then
  media=()
  for dir in $BACKUP_MEDIA_DIRS; do
    [ -d "$dir" ] && media+=("$dir")
  done
  if [ "${#media[@]}" -gt 0 ]; then
    tar --create --gzip --absolute-names --file=- "${media[@]}" \
      | age "${recipients[@]}" -o "${name}.media.tar.gz.age.part"
    mv "${name}.media.tar.gz.age.part" "${name}.media.tar.gz.age"
    files+=("${name}.media.tar.gz.age")
  fi
fi

sha256sum "${files[@]}" > "${name}.sha256"
echo "Backup written: ${files[*]} (${name}.sha256)"

if [ "$KEEP_DAYS" -gt 0 ]; then
  find "$BACKUP_DIR" -maxdepth 1 -type f -name 'almova-*' -mtime "+${KEEP_DAYS}" -print -delete
fi
