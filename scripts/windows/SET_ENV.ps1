# Set environment variables for TheBox MVP
# This script loads environment variables from .thebox.env into the current PowerShell session

$envFile = "..\..\env\.thebox.env"

if (Test-Path $envFile) {
    Write-Host "Loading environment from $envFile" -ForegroundColor Green
    
    # Read the .env file and set environment variables
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $name = $matches[1].Trim()
            $value = $matches[2].Trim()
            
            # Remove quotes if present
            if ($value -match '^"(.*)"$') {
                $value = $matches[1]
            }
            
            # Set the environment variable
            [Environment]::SetEnvironmentVariable($name, $value, "Process")
            Write-Host "Set $name = $value" -ForegroundColor Yellow
        }
    }
    
    Write-Host "Environment loaded successfully" -ForegroundColor Green
} else {
    Write-Host "Environment file not found at $envFile" -ForegroundColor Red
    Write-Host "Please ensure the .thebox.env file exists in the env/ directory" -ForegroundColor Red
}