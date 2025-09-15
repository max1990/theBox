Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')

$env:CAMERA_CONNECTED = 'true'
& .\scripts\RUN_ME.ps1
