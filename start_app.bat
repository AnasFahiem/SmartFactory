@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

title SmartFactory Manager
echo ==========================================
echo    Starting SmartFactory System
echo    (Processes running in background)
echo ==========================================

rem Prepare log paths with timestamp to avoid lock conflicts
set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" md "%LOG_DIR%"
set "LOG_SUFFIX=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
set "LOG_SUFFIX=%LOG_SUFFIX: =0%"
set "BACKEND_LOG=%LOG_DIR%\backend_%LOG_SUFFIX%.txt"
set "DOTNET_LOG=%LOG_DIR%\iotbackend_%LOG_SUFFIX%.txt"
set "FRONTEND_LOG=%LOG_DIR%\frontend_%LOG_SUFFIX%.txt"

echo Checking Python environment...
if not exist "%~dp0venv" (
    echo    Creating virtualenv...
    python -m venv "%~dp0venv"
)
call "%~dp0venv\Scripts\activate" >nul 2>&1
python -m pip show flask >nul 2>&1
if errorlevel 1 (
    echo    Installing Python requirements...
    python -m pip install -r "%~dp0requirements.txt"
)

echo Checking Node dependencies...
if not exist "%~dp0frontend\node_modules" (
    echo    Installing npm packages...
    pushd "%~dp0frontend"
    npm install
    popd
)

echo Starting Python Camera/PPE Backend (5000)...
start "FlaskBackend" /b cmd /c "cd /d ""%~dp0backend"" && ""%~dp0venv\Scripts\python"" app.py > ""%BACKEND_LOG%"" 2>&1"

echo Starting IoT (.NET) Server (5005)...
start "IoTBackend" /b cmd /c "cd /d ""%~dp0IoTBackend"" && set ASPNETCORE_URLS=http://localhost:5005 && dotnet run > ""%DOTNET_LOG%"" 2>&1"

echo Starting Angular Frontend (4200)...
start "Frontend" /b cmd /c "cd /d ""%~dp0frontend"" && npm start > ""%FRONTEND_LOG%"" 2>&1"

set "health_ok=1"
set "max_tries=20"
set "delay_seconds=1"

call :wait_for "Flask (5000)" "http://localhost:5000/api/status"
call :wait_for ".NET (5005)" "http://localhost:5005/api/products"
call :wait_for "Angular (4200)" "http://localhost:4200"

if "!health_ok!"=="1" (
    echo All services healthy; opening browser...
    start http://localhost:4200
) else (
    echo One or more services failed health checks; browser will not open.
)

echo ==========================================
echo    System Running!
echo    Logs saved to:
echo       %BACKEND_LOG%
echo       %DOTNET_LOG%
echo       %FRONTEND_LOG%
echo    CLOSE THIS WINDOW TO STOP ALL SERVERS
echo ==========================================
echo.
echo Manual run commands:
echo   Python backend:  cd /d "%~dp0backend" ^&^& ..\venv\Scripts\python app.py
echo   .NET backend:    cd /d "%~dp0IoTBackend" ^&^& set ASPNETCORE_URLS=http://localhost:5005 ^&^& dotnet run
echo   Angular front:   cd /d "%~dp0frontend" ^&^& npm start
echo.
cmd /k

:wait_for
set "svc=%~1"
set "url=%~2"
set /a tries=0
:wait_loop
if !tries! GEQ %max_tries% (
    echo   !svc! not responding at !url!
    set "health_ok=0"
    goto :eof
)
curl -s --head "!url!" >nul 2>&1
if !errorlevel! EQU 0 (
    echo   !svc! is up (!url!)
    goto :eof
)
timeout /t %delay_seconds% >nul
set /a tries+=1
goto wait_loop
