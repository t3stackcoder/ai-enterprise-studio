@echo off
echo Starting AI Enterprise Studio...
echo.

REM Kill any existing processes on our ports
echo Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 :3001 :8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul
echo.

REM Start Analysis Server in new window
echo Starting Analysis Server...
start "Analysis Server" cmd /k "cd apps\analysis-server && C:\Python311\python.exe server.py"

REM Wait a few seconds for server to start
timeout /t 5 /nobreak >nul

REM Start Web Apps
echo Starting Web Applications...
start "Web Apps" cmd /k "npm run dev:web"

echo.
echo Services starting:
echo   - Analysis Server: ws://localhost:8765
echo   - Web Shell:       http://localhost:3000
echo   - Web Analysis:    http://localhost:3001
echo.
pause
