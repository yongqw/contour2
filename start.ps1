# PowerShell script to launch Terrain Tunneling Calculator GUI
# This script activates the virtual environment and starts the GUI

Write-Host "Starting Terrain Tunneling Calculator..." -ForegroundColor Green

# Check if virtual environment exists
if (-not (Test-Path ".\venv\Scripts\Activate.ps1")) {
    Write-Host "Virtual environment not found. Please run setup first." -ForegroundColor Red
    exit 1
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
try {
    & .\venv\Scripts\Activate.ps1
}
catch {
    Write-Host "Failed to activate virtual environment. Please run:" -ForegroundColor Red
    Write-Host ".\venv\Scripts\Activate.ps1" -ForegroundColor Cyan
    exit 1
}

# Change to project directory
Set-Location $PSScriptRoot

# Start GUI application
Write-Host "Launching GUI application..." -ForegroundColor Green
try {
    python src\main.py --gui
}
catch {
    Write-Host "Error starting application: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Application closed." -ForegroundColor Green
