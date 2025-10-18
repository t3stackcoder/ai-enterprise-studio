# Start Development Environment
# This script starts the auth server, analysis server, and then the web applications

Write-Host "Starting AI Enterprise Studio Development Environment..." -ForegroundColor Green

# Load environment variables
if (Test-Path ".env") {
    Get-Content ".env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]*)\s*=\s*(.*)") {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
        }
    }
    Write-Host "✅ Loaded .env file" -ForegroundColor Green
}

# Get values from environment
$authServerPort = if ($env:AUTH_SERVER_PORT) { $env:AUTH_SERVER_PORT } else { "8001" }
$analysisServerPort = if ($env:ANALYSIS_SERVER_PORT) { $env:ANALYSIS_SERVER_PORT } else { "8765" }
$webShellPort = if ($env:WEB_SHELL_PORT) { $env:WEB_SHELL_PORT } else { "3000" }
$webAnalysisPort = if ($env:WEB_ANALYSIS_PORT) { $env:WEB_ANALYSIS_PORT } else { "3001" }
$pythonExe = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "python" }

# Start the auth server in a new PowerShell window
Write-Host "`nStarting Auth Server on port $authServerPort..." -ForegroundColor Cyan
$authServerPath = "c:\Projects\ai-enterprise-studio\apps\auth-server"

# Start auth server in background
$authServerProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$authServerPath'; Write-Host 'Starting Auth Server...' -ForegroundColor Green; $pythonExe server.py" -PassThru

# Wait for the auth server to be ready
Write-Host "Waiting for Auth Server to start..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$authServerReady = $false

while ($attempt -lt $maxAttempts -and -not $authServerReady) {
    Start-Sleep -Seconds 1
    $attempt++
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$authServerPort/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $authServerReady = $true
            Write-Host "✓ Auth Server is ready!" -ForegroundColor Green
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

if (-not $authServerReady) {
    Write-Host "`n✗ Auth Server failed to start within 30 seconds" -ForegroundColor Red
    Write-Host "Please check the server window for errors" -ForegroundColor Yellow
    exit 1
}

# Start the analysis server in a new PowerShell window
Write-Host "`nStarting Analysis Server on port $analysisServerPort..." -ForegroundColor Cyan
$serverPath = "c:\Projects\ai-enterprise-studio\apps\analysis-server"

# Start server in background
$serverProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$serverPath'; Write-Host 'Starting Analysis Server...' -ForegroundColor Green; $pythonExe server.py" -PassThru

# Wait for the server to be ready
Write-Host "Waiting for Analysis Server to start..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
$serverReady = $false

while ($attempt -lt $maxAttempts -and -not $serverReady) {
    Start-Sleep -Seconds 1
    $attempt++
    
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$analysisServerPort/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $serverReady = $true
            Write-Host "✓ Analysis Server is ready!" -ForegroundColor Green
        }
    } catch {
        Write-Host "." -NoNewline
    }
}

if (-not $serverReady) {
    Write-Host "`n✗ Analysis Server failed to start within 30 seconds" -ForegroundColor Red
    Write-Host "Please check the server window for errors" -ForegroundColor Yellow
    exit 1
}

# Start the web applications
Write-Host "`nStarting Web Applications..." -ForegroundColor Cyan
Start-Sleep -Seconds 1

# Start web apps in a new PowerShell window
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'c:\Projects\ai-enterprise-studio'; Write-Host 'Starting Web Applications...' -ForegroundColor Green; npm run dev:web"

Write-Host "`n✓ All services started successfully!" -ForegroundColor Green
Write-Host "`nServices:" -ForegroundColor Cyan
Write-Host "  - Auth Server:     http://localhost:$authServerPort" -ForegroundColor White
Write-Host "  - Analysis Server: ws://localhost:$analysisServerPort" -ForegroundColor White
Write-Host "  - Web Shell:       http://localhost:$webShellPort" -ForegroundColor White
Write-Host "  - Web Analysis:    http://localhost:$webAnalysisPort" -ForegroundColor White
Write-Host "`nPress any key to exit this window..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
