@echo off
REM ==========================================================================
REM  Stop everything Bhav started: the 3 terminal windows + Docker containers.
REM ==========================================================================

setlocal
cd /d "%~dp0"

echo Stopping Bhav...

REM Close the three terminal windows opened by start.bat (along with the
REM processes they're hosting — /T kills the whole tree). The /FI WINDOWTITLE
REM filter matches the titles we set in start.bat.
taskkill /F /FI "WINDOWTITLE eq Bhav API*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Bhav Worker*" /T >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq Bhav Frontend*" /T >nul 2>&1

echo   service windows closed (if they were open)

REM Stop Postgres + Redis. Leaves data volumes intact, so next start is fast.
docker compose down

echo.
echo Bhav stopped. Run install.bat or start.bat to bring it back.
echo.
pause
