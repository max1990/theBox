# TheBox Environment Loader for PowerShell
# This script dot-sources the .thebox.env file into the current PowerShell session
# Usage: .\scripts\windows\SET_ENV.ps1

$envFile = Join-Path $PSScriptRoot "..\..\mvp\env\.thebox.env"

if (Test-Path $envFile) {
    Write-Host "Loading environment from: $envFile" -ForegroundColor Green
    
    # Read the .env file and set environment variables
    Get-Content $envFile | ForEach-Object {
        # Skip comments and empty lines
        if ($_ -match '^\s*#' -or $_ -match '^\s*$') {
            return
        }
        
        # Parse KEY=VALUE pairs
        if ($_ -match '^([^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Remove quotes if present
            if ($value -match '^"(.*)"$' -or $value -match "^'(.*)'$") {
                $value = $matches[1]
            }
            
            # Set the environment variable
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
            Write-Host "  $key = $value" -ForegroundColor Gray
        }
    }
    
    Write-Host "Environment loaded successfully!" -ForegroundColor Green
    Write-Host "You can now run TheBox scripts in this PowerShell session." -ForegroundColor Yellow
} else {
    Write-Host "Environment file not found: $envFile" -ForegroundColor Red
    Write-Host "Please ensure the .thebox.env file exists in mvp/env/" -ForegroundColor Red
    exit 1
}
