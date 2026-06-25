@echo off
REM ============================================================================
REM  Candidate Assessment Platform - local launcher
REM  Starts Postgres + backend (Docker Compose) and the Vite frontend dev server.
REM ============================================================================
setlocal
cd /d "%~dp0"

echo(
echo ===  Candidate Assessment Platform - local launch  ===
echo(

REM --- 1. Check Docker is available and running ---------------------------------
where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker was not found on PATH. Install Docker Desktop and try again.
    pause
    exit /b 1
)
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Desktop is not running. Start Docker Desktop, then re-run this.
    pause
    exit /b 1
)

REM --- 2. Ensure a .env exists --------------------------------------------------
if not exist ".env" (
    echo No .env found - creating one from .env.example ...
    copy /y ".env.example" ".env" >nul
    echo(
    echo [NOTE] A default .env was created. For a real deployment set strong
    echo        ENCRYPTION_KEY / SESSION_SECRET / INITIAL_ADMIN_PASSWORD in it.
    echo(
)

REM --- 3. Bring up Postgres + backend (migrations auto-run on boot) -------------
echo Starting Postgres + backend containers (this builds on first run) ...
docker compose -f compose.local.yaml up -d --build
if errorlevel 1 (
    echo [ERROR] docker compose failed to start the backend stack.
    pause
    exit /b 1
)

REM --- 4. Wait for the backend health endpoint ---------------------------------
echo(
echo Waiting for the backend to become healthy ...
set /a tries=0
:waitloop
curl -s -o nul http://localhost:8000/api/health
if not errorlevel 1 goto backend_ready
set /a tries+=1
if %tries% geq 40 (
    echo [WARN] Backend did not report healthy after 40s. Check: docker compose -f compose.local.yaml logs backend
    goto frontend
)
timeout /t 1 /nobreak >nul
goto waitloop
:backend_ready
echo Backend is up at http://localhost:8000

REM --- 5. Frontend dependencies -------------------------------------------------
:frontend
echo(
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH. Install Node.js to run the frontend.
    echo         The backend is still running at http://localhost:8000
    pause
    exit /b 1
)
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies - first run only ...
    pushd frontend
    call npm install
    popd
)

REM --- 6. Open the app and start the Vite dev server ----------------------------
echo(
echo ============================================================================
echo   App:      http://localhost:5173
echo   Backend:  http://localhost:8000
echo   Admin login at /admin/login  (username + password from your .env)
echo(
echo   Backend keeps running in Docker. Press Ctrl+C here to stop the frontend.
echo   Run stop.bat to shut the backend containers down.
echo ============================================================================
echo(
cd frontend
REM Open the browser (Vite needs a second or two to bind - refresh if it's early).
start "" "http://localhost:5173"
call npm run dev

endlocal
