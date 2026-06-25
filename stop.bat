@echo off
REM Stops the backend + Postgres containers started by start.bat.
REM (Data is kept in the Docker volume; add -v below to also wipe the database.)
setlocal
cd /d "%~dp0"

echo Stopping backend + Postgres containers ...
docker compose -f compose.local.yaml down
echo Done. (The Postgres data volume is preserved. Use "docker compose -f compose.local.yaml down -v" to wipe it.)
endlocal
