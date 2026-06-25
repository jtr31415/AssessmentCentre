#!/bin/sh
# postgres:16 (Debian bookworm) /bin/sh is dash 0.5.12+, which supports
# `pipefail`, so the pg_dump|gzip pipe fails the script if pg_dump errors.
set -euo pipefail

PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
# Required env vars — fail clearly (rather than with an opaque unbound-variable
# error) if the operator forgot to set them.
: "${PGUSER:?set PGUSER}"
: "${PGDATABASE:?set PGDATABASE}"
: "${PGPASSWORD:?set PGPASSWORD}"

export PGPASSWORD

OUT="/backups/assessment-$(date +%Y%m%d-%H%M%S).sql.gz"

# Write to a temp file and only rename to the final name on full success, so a
# failed/interrupted dump never leaves a truncated .gz that rotation would keep.
pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE" | gzip > "$OUT.tmp"
mv "$OUT.tmp" "$OUT"

find /backups -name 'assessment-*.sql.gz' -mtime +7 -delete

echo "$OUT"
