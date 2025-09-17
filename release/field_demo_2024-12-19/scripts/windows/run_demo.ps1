# Run TheBox MVP Demo on Windows
# This script sets up the environment and runs the demo

# Set execution policy for this process
Set-ExecutionPolicy Bypass -Scope Process -Force

Write-Host "Starting TheBox MVP Demo..." -ForegroundColor Green

# Check if virtual environment exists
if (Test-Path "..\..\venv-win\Scripts\Activate.ps1") {
    Write-Host "Activating virtual environment..." -ForegroundColor Yellow
    & "..\..\venv-win\Scripts\Activate.ps1"
} elseif (Test-Path "..\..\venv-posix\bin\activate") {
    Write-Host "Activating POSIX virtual environment..." -ForegroundColor Yellow
    & "..\..\venv-posix\bin\activate"
} else {
    Write-Host "No virtual environment found. Using system Python." -ForegroundColor Yellow
}

# Load environment variables
Write-Host "Loading environment variables..." -ForegroundColor Yellow
& ".\SET_ENV.ps1"

# Run tests first
Write-Host "Running tests..." -ForegroundColor Yellow
pytest -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Tests failed! Please fix issues before running demo." -ForegroundColor Red
    exit $LASTEXITCODE
}

# Run the demo
Write-Host "Running MVP demo..." -ForegroundColor Yellow
python "..\..\scripts\run_mvp_demo.py"

if ($LASTEXITCODE -eq 0) {
    Write-Host "Demo completed successfully!" -ForegroundColor Green
} else {
    Write-Host "Demo failed with exit code $LASTEXITCODE" -ForegroundColor Red
}

exit $LASTEXITCODE
