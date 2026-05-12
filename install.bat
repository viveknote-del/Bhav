@echo off
REM ==========================================================================
REM  Bhav one-click installer (Windows).
REM
REM  Run from the repo root by double-clicking, or from a terminal:
REM      install.bat
REM
REM  Safe to re-run. Skips work that's already done.
REM  Stops on the first hard failure with a clear "what to install" message.
REM ==========================================================================

setlocal enabledelayedexpansion
set "REPO_DIR=%~dp0"
cd /d "%REPO_DIR%"

echo.
echo  ===============================================
echo    Bhav installer
echo  ===============================================
echo.

REM --- 1/9  prerequisites -----------------------------------------------------
echo [1/9] Checking prerequisites...
call :check_cmd docker     "Docker Desktop"   "https://www.docker.com/products/docker-desktop"
if errorlevel 1 exit /b 1
call :check_cmd python     "Python 3.12+"     "https://www.python.org/downloads/"
if errorlevel 1 exit /b 1
call :check_cmd node       "Node.js 20+"      "https://nodejs.org/"
if errorlevel 1 exit /b 1
call :check_cmd git        "Git"              "https://git-scm.com/downloads"
if errorlevel 1 exit /b 1
echo   ok
echo.

REM --- 2/9  git pull (if a git checkout) --------------------------------------
echo [2/9] Pulling latest code from GitHub...
if exist .git (
  git pull
) else (
  echo   not a git checkout, skipping pull
)
echo.

REM --- 3/9  .env --------------------------------------------------------------
echo [3/9] Configuring .env...
if not exist .env (
  copy /Y .env.example .env >nul
  echo   .env created from .env.example
) else (
  echo   .env already exists, leaving it alone
)
REM Force MARKET_DATA_PROVIDER=yahoo_direct (works without an API key on most
REM networks). Uses Python because PowerShell multi-line in .bat is fragile
REM and Python is already a prereq.
python -c "import pathlib,re; p=pathlib.Path('.env'); t=p.read_text(encoding='utf-8'); t = re.sub(r'^MARKET_DATA_PROVIDER=.*', 'MARKET_DATA_PROVIDER=yahoo_direct', t, flags=re.M) if 'MARKET_DATA_PROVIDER=' in t else (t.rstrip() + '\nMARKET_DATA_PROVIDER=yahoo_direct\n'); p.write_text(t, encoding='utf-8')"
echo   MARKET_DATA_PROVIDER=yahoo_direct  (no API key needed)
echo.

REM --- 4/9  docker compose up + wait for health ------------------------------
echo [4/9] Starting Postgres + Redis (Docker)...
docker compose up -d --wait
if errorlevel 1 (
  echo   ERROR: docker compose failed. Is Docker Desktop running?
  pause
  exit /b 1
)
echo   containers healthy
echo.

REM --- 5/9  apply migrations --------------------------------------------------
echo [5/9] Applying database migrations...
for /f %%i in ('docker compose ps -q postgres') do set "PG_CONTAINER=%%i"
if "%PG_CONTAINER%"=="" (
  echo   ERROR: postgres container not found.
  pause
  exit /b 1
)
for %%f in (packages\database\migrations\*.sql) do (
  echo    applying %%~nxf
  docker exec -i %PG_CONTAINER% psql -U postgres -d bhav -q < "%%f" >nul 2>&1
)
echo.

REM --- 6/9  Python venv + deps -----------------------------------------------
echo [6/9] Setting up Python virtual environment...
if not exist "services\api\.venv\Scripts\python.exe" (
  echo   creating venv at services\api\.venv
  python -m venv services\api\.venv
  if errorlevel 1 (
    echo   ERROR: failed to create venv. Is `python` on PATH?
    pause
    exit /b 1
  )
)
echo   installing Python dependencies ^(~2 min first time^)...
"services\api\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
"services\api\.venv\Scripts\python.exe" -m pip install --only-binary=:all: -r services\api\requirements.txt --quiet
if errorlevel 1 (
  echo   ERROR: pip install failed. Check requirements.txt vs your Python version.
  pause
  exit /b 1
)
echo   done
echo.

REM --- 7/9  seed universe ----------------------------------------------------
echo [7/9] Seeding NIFTY 50 universe...
pushd services\api
"%REPO_DIR%services\api\.venv\Scripts\python.exe" -m scripts.seed
popd
echo.

REM --- 8/9  pnpm + frontend deps ---------------------------------------------
echo [7b/9] Writing apps\web\.env.local (Next can't see the root .env)...
if not exist "apps\web\.env.local" (
  echo NEXT_PUBLIC_API_URL=http://localhost:8765> apps\web\.env.local
  echo   created
) else (
  echo   already exists, leaving it alone
)
echo.

echo [8/9] Installing frontend dependencies...
where pnpm >nul 2>&1
if errorlevel 1 (
  echo   pnpm not found, installing via npm...
  call npm install -g pnpm
  if errorlevel 1 (
    echo   ERROR: failed to install pnpm. Run manually: npm install -g pnpm
    pause
    exit /b 1
  )
)
pushd apps\web
call pnpm install
popd
echo.

REM --- 9/9  done --------------------------------------------------------------
echo [9/9] Installation complete.
echo.
echo  ===============================================
echo    Bhav is installed.
echo.
echo    Next:  run  start.bat  to launch the app.
echo  ===============================================
echo.
pause
exit /b 0

REM ==========================================================================
REM  helpers
REM ==========================================================================
:check_cmd
where %~1 >nul 2>&1
if errorlevel 1 (
  echo.
  echo   ERROR: %~2 is not installed or not on PATH.
  echo   Install it from %~3 and try again.
  pause
  exit /b 1
)
exit /b 0
