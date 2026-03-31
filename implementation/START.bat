@echo off
setlocal

set "ROOT=%~dp0"
set "LOG=%ROOT%startup.log"
set "RUN_DIR=%ROOT%.run"
set "BACKEND_PID_FILE=%RUN_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%RUN_DIR%\frontend.pid"

cd /d "%ROOT%"

if not exist "%RUN_DIR%" mkdir "%RUN_DIR%" > nul 2>&1
if exist "%BACKEND_PID_FILE%" del /f /q "%BACKEND_PID_FILE%" > nul 2>&1
if exist "%FRONTEND_PID_FILE%" del /f /q "%FRONTEND_PID_FILE%" > nul 2>&1

echo. > "%LOG%"
echo [%DATE% %TIME%] START.bat invoked >> "%LOG%"

echo.
echo ============================================================================
echo  SMART CITY SYSTEM - AUTOMATIC STARTUP
echo ============================================================================
echo.
echo [INFO] Working directory: %CD%
echo [INFO] Log file: %LOG%

where python > nul 2>&1
if errorlevel 1 goto :err_python

where npm > nul 2>&1
if errorlevel 1 goto :err_npm

python -m pip --version > nul 2>&1
if errorlevel 1 goto :err_pip

echo [0/6] Toolchain OK (python, pip, npm)
echo [%DATE% %TIME%] Toolchain OK >> "%LOG%"

echo [1/6] Starting optional infrastructure (Redis + TimescaleDB)...
docker --version > nul 2>&1
if errorlevel 1 (
    echo [WARN] Docker not found. Continuing with in-memory fallback.
    echo [%DATE% %TIME%] Docker not found >> "%LOG%"
) else (
    docker compose version > nul 2>&1
    if errorlevel 1 (
        echo [WARN] Docker Compose plugin not available. Skipping infra startup.
        echo [%DATE% %TIME%] Docker compose missing >> "%LOG%"
    ) else (
        docker compose up -d redis timescaledb >> "%LOG%" 2>&1
        if errorlevel 1 (
            echo [WARN] Could not start infrastructure. See startup.log
            echo [%DATE% %TIME%] Infra startup failed >> "%LOG%"
        ) else (
            echo [OK] Infrastructure ready (or already running)
            echo [%DATE% %TIME%] Infra startup OK >> "%LOG%"
        )
    )
)

echo [2/6] Installing backend dependencies...
python -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :err_requirements

echo [3/6] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    pushd frontend
    call npm install >> "%LOG%" 2>&1
    set "NPM_RC=%ERRORLEVEL%"
    popd
    if not "%NPM_RC%"=="0" goto :err_npm_install
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies already present
)

echo [4/6] Starting backend terminal...
powershell -NoProfile -Command "$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/k','cd /d \"%ROOT%\" && python app.py proposed' -WindowStyle Normal -PassThru; Set-Content -Path '%BACKEND_PID_FILE%' -Value $p.Id"

echo [5/6] Starting frontend terminal...
powershell -NoProfile -Command "$p = Start-Process -FilePath 'cmd.exe' -ArgumentList '/k','cd /d \"%ROOT%frontend\" && npm start' -WindowStyle Normal -PassThru; Set-Content -Path '%FRONTEND_PID_FILE%' -Value $p.Id"

echo [6/6] Waiting for backend health endpoint (up to ~90s)...
set /a TRIES=0

:wait_health
set /a TRIES+=1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5000/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" > nul 2>&1
if not errorlevel 1 goto :health_ok
if %TRIES% GEQ 45 goto :health_timeout
timeout /t 2 > nul
goto :wait_health

:health_ok
echo [OK] Backend API is healthy.
start "" "http://localhost:3000"
start "" "http://localhost:3000/#/logic"
start "" "http://localhost:3000/#/thesis"
goto :summary

:health_timeout
echo [WARN] Health endpoint not ready yet. Backend may still be pretraining.
echo [WARN] You can still open: http://localhost:3000

:summary
echo.
echo ============================================================================
echo  PLATFORM STARTED
echo ============================================================================
echo.
echo Active terminals:
echo   - SmartCity Backend
echo   - SmartCity Frontend
echo.
echo URLs:
echo   - Dashboard:   http://localhost:3000
echo   - Logic:       http://localhost:3000/#/logic
echo   - Thesis v2:   http://localhost:3000/#/thesis
echo   - API health:  http://127.0.0.1:5000/api/health
echo.
echo Process tracking:
echo   - %BACKEND_PID_FILE%
echo   - %FRONTEND_PID_FILE%
echo.
echo Troubleshooting log:
echo   - %LOG%
echo.
pause
exit /b 0

:err_python
echo ERROR: Python not found in PATH.
echo [%DATE% %TIME%] ERROR python missing >> "%LOG%"
goto :fail

:err_npm
echo ERROR: npm not found in PATH. Install Node.js.
echo [%DATE% %TIME%] ERROR npm missing >> "%LOG%"
goto :fail

:err_pip
echo ERROR: pip not found for current Python.
echo [%DATE% %TIME%] ERROR pip missing >> "%LOG%"
goto :fail

:err_requirements
echo ERROR: Backend dependency installation failed. See startup.log
echo [%DATE% %TIME%] ERROR pip install failed >> "%LOG%"
goto :fail

:err_npm_install
echo ERROR: Frontend dependency installation failed. See startup.log
echo [%DATE% %TIME%] ERROR npm install failed >> "%LOG%"
goto :fail

:fail
echo.
echo Startup failed. Review: %LOG%
pause
exit /b 1
