@echo off
echo Starting AI Enterprise Studio...
echo.

REM Kill any existing processes on our ports
echo Cleaning up existing processes...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001 :8002 :3000 :3001 :3002 :8765" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a 2>nul
)
timeout /t 2 /nobreak >nul
echo.

REM Start all Docker services (Postgres, Redis, Qdrant, MinIO, MLflow)
echo Starting Docker services...
docker-compose up -d
echo Waiting for services to be ready...
timeout /t 15 /nobreak >nul
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
timeout /t 3 /nobreak >nul

REM Start Video Analysis Server in new window
echo Starting Video Analysis Server...
start "Video Analysis Server" cmd /k "cd apps\video-analysis-server && C:\Python311\python.exe server.py"

REM Wait a few seconds for server to start
timeout /t 3 /nobreak >nul

REM Start Web Analysis (preview mode for built remote)
echo Starting Web Analysis (built remote)...
start "Web Analysis" cmd /k "cd apps\web-chess-analysis && npm run preview"

REM Wait for preview to start
timeout /t 3 /nobreak >nul

REM Start Web Shell (dev mode)
echo Starting Web Shell...
start "Web Shell" cmd /k "npm run dev --workspace=@ai-enterprise-studio/web-shell"

echo.
echo ========================================
echo Services Running:
echo ========================================
echo Docker Services:
echo   - PostgreSQL:           localhost:5432
echo   - Redis:                localhost:6379
echo   - Qdrant (Vector DB):   localhost:6333
echo   - MinIO (S3):           localhost:9000 (Console: 9001)
echo   - MLflow:               http://localhost:5000
echo.
echo Application Services:
echo   - Auth Server:          http://localhost:8001
echo   - Analysis Server:      ws://localhost:8765
echo   - Video Analysis Server: http://localhost:8002
echo.
echo Frontend Apps:
echo   - Web Shell:            http://localhost:3000
echo   - Web Chess Analysis:   http://localhost:3001
echo   - Web Video Analysis:   http://localhost:3002
echo ========================================
echo.
echo To stop all services, run: docker-compose down
echo.
pause
