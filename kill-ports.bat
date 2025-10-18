@echo off
echo Killing processes on ports 3000, 3001, 3002, and 8765...
echo.

REM Get PIDs for listening processes on our ports
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 :3001 :3002 :8765" ^| findstr "LISTENING"') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo Done! All processes killed.
