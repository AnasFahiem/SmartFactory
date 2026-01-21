@echo off
setlocal EnableDelayedExpansion
pushd "%~dp0"

title SmartFactory Manager
echo ==========================================
echo    Starting SmartFactory System
echo    (Processes running in background)
echo ==========================================

rem Ensure venv exists and dependencies installed
if not exist "%~dp0venv" (
	echo Creating virtualenv...
	python -m venv "%~dp0venv"
)
call "%~dp0venv\Scripts\activate" >nul 2>&1
python -m pip show flask >nul 2>&1
if errorlevel 1 (
	echo Installing Python requirements...
	python -m pip install -r "%~dp0requirements.txt"
)

rem Start Flask camera/PPE backend
echo Starting Python Backend (5000)...
start "FlaskBackend" /b cmd /c "cd /d ""%~dp0backend"" && ""%~dp0venv\Scripts\python"" app.py > ""%~dp0backend_log.txt"" 2>&1"

rem Start .NET IoT backend
echo Starting IoT (.NET) Backend (5005)...
start "IoTBackend" /b cmd /c "cd /d ""%~dp0IoTBackend"" && set ASPNETCORE_URLS=http://localhost:5005 && dotnet run > ""%~dp0iotbackend_log.txt"" 2>&1"

rem Start Angular frontend
echo Starting Frontend (4200)...
start "Frontend" /b cmd /c "cd /d ""%~dp0frontend"" && npm start > ""%~dp0frontend_log.txt"" 2>&1"

echo Waiting for servers to initialize (15s)...
timeout /t 15 >nul

rem Open browser only after wait
start http://localhost:4200

echo ==========================================
echo    System Running!
echo    Logs saved to: backend_log.txt / iotbackend_log.txt / frontend_log.txt
echo    CLOSE THIS WINDOW TO STOP ALL SERVERS
echo ==========================================
cmd /k
