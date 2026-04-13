@echo off
setlocal

set "ROOT=%~dp0"
set "LOG=%ROOT%shutdown.log"
set "RUN_DIR=%ROOT%.run"
set "BACKEND_PID_FILE=%RUN_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%RUN_DIR%\frontend.pid"

cd /d "%ROOT%"

echo. > "%LOG%"
echo [%DATE% %TIME%] STOP.bat invoked >> "%LOG%"

echo.
echo ============================================================================
echo  SMART CITY SYSTEM - SHUTDOWN
echo ============================================================================
echo.

echo [1/5] Stopping tracked backend/frontend processes...
if exist "%BACKEND_PID_FILE%" (
    set /p BACKEND_PID=<"%BACKEND_PID_FILE%"
    if not "%BACKEND_PID%"=="" taskkill /PID %BACKEND_PID% /T /F > nul 2>&1
    del /f /q "%BACKEND_PID_FILE%" > nul 2>&1
)
if exist "%FRONTEND_PID_FILE%" (
    set /p FRONTEND_PID=<"%FRONTEND_PID_FILE%"
    if not "%FRONTEND_PID%"=="" taskkill /PID %FRONTEND_PID% /T /F > nul 2>&1
    del /f /q "%FRONTEND_PID_FILE%" > nul 2>&1
)
echo [OK] Tracked process stop attempted.

echo [2/5] Stopping titled service terminals (fallback)...
for %%T in ("SmartCity Backend" "SmartCity Frontend") do (
    taskkill /FI "WINDOWTITLE eq %%~T" /FI "IMAGENAME eq cmd.exe" /T /F > nul 2>&1
)
echo [OK] Terminal fallback stop attempted.

echo [3/5] Releasing common platform ports (3000, 5000, 8765)...
for %%P in (3000 5000 8765) do (
    for /f "tokens=5" %%A in ('netstat -ano ^| findstr /R /C:":%%P .*LISTENING"') do (
        taskkill /PID %%A /F > nul 2>&1
    )
)
echo [OK] Port cleanup completed.

echo [4/5] Stopping optional Docker infrastructure...
docker --version > nul 2>&1
if errorlevel 1 (
    echo [WARN] Docker not found. Skipping infrastructure shutdown.
    echo [%DATE% %TIME%] Docker not found >> "%LOG%"
) else (
    docker compose version > nul 2>&1
    if errorlevel 1 (
        echo [WARN] Docker Compose plugin not available. Skipping infrastructure shutdown.
        echo [%DATE% %TIME%] Docker compose missing >> "%LOG%"
    ) else (
        docker compose down >> "%LOG%" 2>&1
        if errorlevel 1 (
            echo [WARN] docker compose down failed or no stack was running.
            echo [%DATE% %TIME%] docker compose down failed >> "%LOG%"
        ) else (
            echo [OK] Docker infrastructure stopped.
            echo [%DATE% %TIME%] docker compose down OK >> "%LOG%"
        )
    )
)

echo [5/5] Done.
echo.
echo Shutdown complete.
echo Log: %LOG%
echo.
pause
exit /b 0
