@echo off
echo Stopping AI Enterprise Studio services...
echo.

REM Kill processes on our ports
echo Stopping server processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 :3000 :3001 :8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)

REM Stop Docker services
echo Stopping Docker services...
docker-compose down

echo.
echo All services stopped!
echo.
pause
