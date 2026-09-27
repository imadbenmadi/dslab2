@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "ROOT=%~dp0"
set "LOG=%ROOT%startup.log"
set "RUN_DIR=%ROOT%.run"
set "BACKEND_PID_FILE=%RUN_DIR%\backend.pid"
set "FRONTEND_PID_FILE=%RUN_DIR%\frontend.pid"
set "BACKEND_OUT_LOG=%RUN_DIR%\backend.out.log"
set "BACKEND_ERR_LOG=%RUN_DIR%\backend.err.log"
set "FRONTEND_OUT_LOG=%RUN_DIR%\frontend.out.log"
set "FRONTEND_ERR_LOG=%RUN_DIR%\frontend.err.log"

cd /d "%ROOT%"

if not exist "%RUN_DIR%" mkdir "%RUN_DIR%" > nul 2>&1
if exist "%BACKEND_PID_FILE%" del /f /q "%BACKEND_PID_FILE%" > nul 2>&1
if exist "%FRONTEND_PID_FILE%" del /f /q "%FRONTEND_PID_FILE%" > nul 2>&1
if exist "%BACKEND_OUT_LOG%" del /f /q "%BACKEND_OUT_LOG%" > nul 2>&1
if exist "%BACKEND_ERR_LOG%" del /f /q "%BACKEND_ERR_LOG%" > nul 2>&1
if exist "%FRONTEND_OUT_LOG%" del /f /q "%FRONTEND_OUT_LOG%" > nul 2>&1
if exist "%FRONTEND_ERR_LOG%" del /f /q "%FRONTEND_ERR_LOG%" > nul 2>&1

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

where node > nul 2>&1
if errorlevel 1 goto :err_node

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
    docker info > nul 2>&1
    if errorlevel 1 (
        echo [WARN] Docker is installed but the engine is not running. Skipping infra startup.
        echo [%DATE% %TIME%] Docker engine not running >> "%LOG%"
        goto :after_infra
    )
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
            echo [OK] Infrastructure ready or already running
            echo [%DATE% %TIME%] Infra startup OK >> "%LOG%"
        )
    )
)

:after_infra

echo [2/6] Installing backend dependencies...
python -m pip install -r requirements.txt >> "%LOG%" 2>&1
if errorlevel 1 goto :err_requirements

echo [3/6] Checking frontend dependencies...
if not exist "frontend\node_modules" (
    pushd frontend
    call npm install --no-audit --no-fund >> "%LOG%" 2>&1
    set "NPM_RC=!ERRORLEVEL!"
    popd
    if not "!NPM_RC!"=="0" (
        if exist "frontend\node_modules" (
            echo [WARN] npm reported exit code !NPM_RC! but node_modules exists; continuing.
            echo [%DATE% %TIME%] WARN npm install nonzero but node_modules present >> "%LOG%"
        ) else (
            goto :err_npm_install
        )
    )
    echo [OK] Frontend dependencies installed
) else (
    echo [OK] Frontend dependencies already present
)

echo [4/6] Starting backend (API + WebSocket)...
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $root='%ROOT%'; $p = Start-Process -FilePath 'python' -WorkingDirectory $root -ArgumentList @('app.py','proposed') -PassThru -RedirectStandardOutput '%BACKEND_OUT_LOG%' -RedirectStandardError '%BACKEND_ERR_LOG%'; Set-Content -Path '%BACKEND_PID_FILE%' -Value ([string]$p.Id) -Encoding ascii -NoNewline"
if not exist "%BACKEND_PID_FILE%" goto :err_backend_start

echo [5/6] Waiting for backend health endpoint (up to ~90s)...
set /a TRIES=0

:wait_health
set /a TRIES+=1
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:5000/api/health' -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" > nul 2>&1
if not errorlevel 1 goto :health_ok
if %TRIES% GEQ 45 goto :health_timeout
ping 127.0.0.1 -n 3 > nul
goto :wait_health

:health_ok
echo [OK] Backend API is healthy.
goto :start_frontend

:health_timeout
echo [WARN] Health endpoint not ready yet. Backend may still be pretraining.
echo [WARN] You can still open: http://localhost:3000
echo [WARN] Backend logs: %BACKEND_OUT_LOG% and %BACKEND_ERR_LOG%
goto :start_frontend

:start_frontend
echo [6/6] Starting frontend (React dev server)...
powershell -NoProfile -Command "$ErrorActionPreference='Stop'; $front='%ROOT%frontend'; $p = Start-Process -FilePath 'node' -WorkingDirectory $front -ArgumentList @('node_modules/react-scripts/bin/react-scripts.js','start') -PassThru -RedirectStandardOutput '%FRONTEND_OUT_LOG%' -RedirectStandardError '%FRONTEND_ERR_LOG%'; Set-Content -Path '%FRONTEND_PID_FILE%' -Value ([string]$p.Id) -Encoding ascii -NoNewline"
if not exist "%FRONTEND_PID_FILE%" goto :err_frontend_start

start "" "http://localhost:3000"
start "" "http://localhost:3000/#/logic"
start "" "http://localhost:3000/#/thesis"
goto :summary

:summary
echo.
echo ============================================================================
echo  PLATFORM STARTED
echo ============================================================================
echo.
echo Processes started:
echo   - Backend:  Python API on http://127.0.0.1:5000 and WS on ws://localhost:8765/
echo   - Frontend: React dev server on http://localhost:3000
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
echo Backend logs:
echo   - %BACKEND_OUT_LOG%
echo   - %BACKEND_ERR_LOG%
echo Frontend logs:
echo   - %FRONTEND_OUT_LOG%
echo   - %FRONTEND_ERR_LOG%
echo.
pause
exit /b 0

:err_backend_start
echo ERROR: Backend process failed to start.
echo [%DATE% %TIME%] ERROR backend start failed >> "%LOG%"
goto :fail

:err_frontend_start
echo ERROR: Frontend process failed to start.
echo [%DATE% %TIME%] ERROR frontend start failed >> "%LOG%"
goto :fail

:err_python
echo ERROR: Python not found in PATH.
echo [%DATE% %TIME%] ERROR python missing >> "%LOG%"
goto :fail

:err_npm
echo ERROR: npm not found in PATH. Install Node.js.
echo [%DATE% %TIME%] ERROR npm missing >> "%LOG%"
goto :fail

:err_node
echo ERROR: node not found in PATH. Install Node.js.
echo [%DATE% %TIME%] ERROR node missing >> "%LOG%"
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
