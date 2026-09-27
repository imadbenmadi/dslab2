@echo off
setlocal EnableExtensions EnableDelayedExpansion

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

echo [1/3] Stopping tracked backend/frontend processes...
if exist "%BACKEND_PID_FILE%" (
    set /p BACKEND_PID=<"%BACKEND_PID_FILE%"
    if not "!BACKEND_PID!"=="" (
        echo [INFO] Stopping backend PID !BACKEND_PID!
        echo [%DATE% %TIME%] Stopping backend PID !BACKEND_PID! >> "%LOG%"
        taskkill /PID !BACKEND_PID! /T /F >> "%LOG%" 2>&1
        if errorlevel 1 (
            echo [WARN] Failed to stop backend PID !BACKEND_PID! - see shutdown.log
            echo [%DATE% %TIME%] WARN backend taskkill failed PID !BACKEND_PID! >> "%LOG%"
        )
    )
    del /f /q "%BACKEND_PID_FILE%" > nul 2>&1
)
if exist "%FRONTEND_PID_FILE%" (
    set /p FRONTEND_PID=<"%FRONTEND_PID_FILE%"
    if not "!FRONTEND_PID!"=="" (
        echo [INFO] Stopping frontend PID !FRONTEND_PID!
        echo [%DATE% %TIME%] Stopping frontend PID !FRONTEND_PID! >> "%LOG%"
        taskkill /PID !FRONTEND_PID! /T /F >> "%LOG%" 2>&1
        if errorlevel 1 (
            echo [WARN] Failed to stop frontend PID !FRONTEND_PID! - see shutdown.log
            echo [%DATE% %TIME%] WARN frontend taskkill failed PID !FRONTEND_PID! >> "%LOG%"
        )
    )
    del /f /q "%FRONTEND_PID_FILE%" > nul 2>&1
)
echo [OK] Tracked process stop attempted.

echo [2/3] Stopping optional Docker infrastructure...
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

echo [3/3] Done.
echo.
echo Shutdown complete.
echo Log: %LOG%
echo.
pause
exit /b 0
