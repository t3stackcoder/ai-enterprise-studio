@echo off
REM Start Auth Server
echo Starting Auth Server...
echo.

REM Check if .env exists, if not create from example
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please update .env with your configuration!
    echo Press any key to continue...
    pause >nul
)

REM Start the server
python server.py
