# Postgres Restore Procedure

## Overview

Dumps are written to the `backups` Docker named volume as gzip-compressed plain-SQL files:
`assessment-YYYYMMDD-HHMMSS.sql.gz`

Dumps older than 7 days are pruned automatically by the backup sidecar.

---

## On-Demand Backup

Run a one-off backup at any time (without waiting for the daily cycle):

```sh
docker compose run --rm backup sh /backup.sh
```

---

## Restore Steps

### 1. Stop the application

Quiesce the app to avoid writes during restore:

```sh
docker compose stop backend caddy
```

### 2. Locate the dump

List available dumps:

```sh
docker run --rm -v backups:/backups postgres:16 ls -lh /backups/
```

### 3. Restore the dump

**Option A — via a one-off container (recommended):**

```sh
docker run --rm \
  -v backups:/backups \
  --network <compose_network> \
  -e PGPASSWORD=<password> \
  postgres:16 \
  sh -c 'gunzip -c /backups/assessment-YYYYMMDD-HHMMSS.sql.gz | psql -h db -U <user> -d <database>'
```

Replace `<compose_network>` with the compose project network (e.g. `assessment_default`), and supply the correct credentials.

**Option B — from the host (if `psql` is installed locally and the DB port is exposed):**

```sh
gunzip -c assessment-YYYYMMDD-HHMMSS.sql.gz | psql -h localhost -U <user> -d <database>
```

### 4. Restart the application

```sh
docker compose start backend caddy
```

---

## Security Notes

- Dumps contain **sensitive data**: encrypted keys, password hashes, and all user data.
- Store and transfer dumps using secure channels only.
- Restrict access to the `backups` volume and any exported dump files.
- Delete dump files securely when they are no longer needed.
