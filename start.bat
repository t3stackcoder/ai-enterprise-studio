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

REM Build web-analysis remote
echo Building web-analysis remote...
cd apps\web-analysis
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
start "Web Analysis" cmd /k "cd apps\web-analysis && npm run preview"

REM Wait for preview to start
timeout /t 3 /nobreak >nul

REM Start Web Shell (dev mode)
echo Starting Web Shell...
start "Web Shell" cmd /k "npm run dev --workspace=@ai-enterprise-studio/web-shell"

echo.
echo Services starting:
echo   - Analysis Server: ws://localhost:8765
echo   - Web Analysis:    http://localhost:3001 (built remote)
echo   - Web Shell:       http://localhost:3000
echo.
pause
