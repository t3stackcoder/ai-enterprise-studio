@echo off
echo Starting AI Enterprise Studio...
echo.

REM Kill any existing processes on our ports
echo Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 :3000 :3001 :8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul
echo.

REM Start PostgreSQL database
echo Starting PostgreSQL database...
docker-compose up -d postgres
echo Waiting for database to be ready...
timeout /t 10 /nobreak >nul
echo.

REM Start Auth Server in new window
echo Starting Auth Server...
start "Auth Server" cmd /k "cd apps\auth-server && python server.py"

REM Wait a few seconds for auth server to start
timeout /t 5 /nobreak >nul

REM Build web-chess-analysis remote
echo Building web-chess-analysis remote...
cd apps\web-chess-analysis
call npm run build
cd ..\..
echo.

REM Start Analysis Server in new window
echo Starting Analysis Server...
start "Analysis Server" cmd /k "cd apps\analysis-server && C:\Python311\python.exe server.py"

REM Wait a few seconds for server to start
timeout /t 5 /nobreak >nul

REM Start Web Analysis (preview mode for built remote)
echo Starting Web Analysis (built remote)...
start "Web Analysis" cmd /k "cd apps\web-chess-analysis && npm run preview"

REM Wait for preview to start
timeout /t 3 /nobreak >nul

REM Start Web Shell (dev mode)
echo Starting Web Shell...
start "Web Shell" cmd /k "npm run dev --workspace=@ai-enterprise-studio/web-shell"

echo.
echo Services starting:
echo   - PostgreSQL:      localhost:5432
echo   - Auth Server:     http://localhost:8001
echo   - Analysis Server: ws://localhost:8765
echo   - Web Analysis:    http://localhost:3001 (built remote)
echo   - Web Shell:       http://localhost:3000
echo.
echo To stop all services, run: docker-compose down
echo.
pause
