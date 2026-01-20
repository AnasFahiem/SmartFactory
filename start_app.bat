@echo off
title SmartFactory Manager
echo ==========================================
echo    Starting SmartFactory System
echo    (Processes running in background)
echo ==========================================

echo Starting Backend Server...
cd backend
start /b py -3.14 app.py > ..\backend_log.txt 2>&1
cd ..

echo Starting Frontend Application...
cd frontend
start /b npm start > ..\frontend_log.txt 2>&1
cd ..

echo Waiting for servers to initialize (15s)...
timeout /t 15

echo Opening Browser...
start http://localhost:4200

echo ==========================================
echo    System Running!
echo    Logs saved to: backend_log.txt / frontend_log.txt
echo    CLOSE THIS WINDOW TO STOP ALL SERVERS
echo ==========================================
rem Prevent the script from exiting immediately
cmd /k
