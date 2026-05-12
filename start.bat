@echo off
REM ==========================================================================
REM  Bhav launcher — opens three terminal windows (API, worker, frontend)
REM  and then opens the dashboard in your default browser.
REM
REM  Each window is independent. Close any of them to stop just that service.
REM  Run stop.bat to clean up all three at once.
REM ==========================================================================

setlocal
set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%"

REM --- sanity: did install run? ----------------------------------------------
if not exist "services\api\.venv\Scripts\python.exe" (
  echo Bhav isn't installed yet. Run install.bat first.
  pause
  exit /b 1
)

REM --- bring up Docker if it isn't already -----------------------------------
echo Ensuring Postgres + Redis are running...
docker compose up -d >nul 2>&1
echo.

echo Launching three windows... watch the titlebars.
echo.

REM --- API (window 1) --------------------------------------------------------
start "Bhav API" cmd /k "cd /d ""%REPO_DIR%services\api"" && call .venv\Scripts\activate && uvicorn main:app --port 8765"
echo   [1/3] Bhav API     → http://localhost:8765
timeout /t 4 /nobreak >nul

REM --- Worker (window 2) -----------------------------------------------------
start "Bhav Worker" cmd /k "cd /d ""%REPO_DIR%services\api"" && call .venv\Scripts\activate && arq workers.WorkerSettings"
echo   [2/3] Bhav Worker  → background scan + commentary jobs
timeout /t 3 /nobreak >nul

REM --- Frontend (window 3) ---------------------------------------------------
start "Bhav Frontend" cmd /k "cd /d ""%REPO_DIR%apps\web"" && pnpm dev"
echo   [3/3] Bhav Frontend → http://localhost:3000
echo.

echo Waiting 10s for the frontend to boot, then opening the dashboard...
timeout /t 10 /nobreak >nul
start "" "http://localhost:3000"

echo.
echo  ===============================================
echo    Bhav is running.
echo.
echo    Dashboard:  http://localhost:3000
echo    API:        http://localhost:8765/v1/health
echo.
echo    To trigger a fresh scan (in any new terminal):
echo      curl -X POST http://localhost:8765/v1/scans ^
echo        -H "Content-Type: application/json" -d "{}"
echo.
echo    To stop everything:  stop.bat
echo  ===============================================
echo.
pause
