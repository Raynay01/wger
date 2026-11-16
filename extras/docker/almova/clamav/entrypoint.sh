#!/bin/sh
# Downloads the virus database on the first start, keeps it updated in the
# background and runs clamd in the foreground
set -e
chown -R clamav:clamav /var/lib/clamav /run/clamav
if ! ls /var/lib/clamav/main.c?d >/dev/null 2>&1; then
    echo "First start: downloading the virus database"
    freshclam --foreground --stdout
fi
freshclam --daemon --checks=12 || echo "freshclam could not start, the database is not updated"
exec clamd --foreground
