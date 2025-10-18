# Start Development Environment
# This script starts the analysis server and then the web applications

Write-Host "Starting AI Enterprise Studio Development Environment..." -ForegroundColor Green

# Start the analysis server in a new PowerShell window
Write-Host "`nStarting Analysis Server..." -ForegroundColor Cyan
$serverPath = "c:\Projects\ai-enterprise-studio\apps\analysis-server"
$pythonExe = "C:/Python311/python.exe"

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
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
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
Write-Host "  - Analysis Server: http://localhost:8000" -ForegroundColor White
Write-Host "  - Web Shell:       http://localhost:3000" -ForegroundColor White
Write-Host "  - Web Analysis:    http://localhost:3001" -ForegroundColor White
Write-Host "`nPress any key to exit this window..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
