@echo off
echo Killing processes on common development ports...
echo.

REM Get PIDs for listening processes on our ports (3000, 3001, 8001, 8765)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000 :3001 :8001 :8765" ^| findstr "LISTENING"') do (
    echo Killing process %%a
    taskkill /F /PID %%a 2>nul
)

echo.
echo Done! All processes killed.
