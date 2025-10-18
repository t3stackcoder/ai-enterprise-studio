@echo off
echo Testing Auth Server Startup...
echo.

REM Start PostgreSQL if not running
docker-compose up -d postgres
timeout /t 5 /nobreak >nul

REM Try to start auth server
cd apps\auth-server
python server.py

pause
