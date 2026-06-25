#!/bin/sh
set -euo pipefail

PGHOST="${PGHOST:-db}"
PGPORT="${PGPORT:-5432}"
# Required: PGUSER, PGPASSWORD, PGDATABASE must be set in the environment

export PGPASSWORD

OUT="/backups/assessment-$(date +%Y%m%d-%H%M%S).sql.gz"

pg_dump -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" "$PGDATABASE" | gzip > "$OUT"

find /backups -name 'assessment-*.sql.gz' -mtime +7 -delete

echo "$OUT"
