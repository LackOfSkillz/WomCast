#!/usr/bin/env pwsh
# Performance test script for indexer: cold vs warm cache
# Usage: .\scripts\dev\perf-index.ps1 <test_media_directory>

param(
    [Parameter(Mandatory=$true)]
    [string]$TestDir
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== WomCast Indexer Performance Test ===" -ForegroundColor Cyan
Write-Host ""

# Validate test directory
if (-not (Test-Path $TestDir)) {
    Write-Host "Error: Test directory does not exist: $TestDir" -ForegroundColor Red
    exit 1
}

$TestDirPath = Resolve-Path $TestDir
$FileCount = (Get-ChildItem -Path $TestDirPath -File -Recurse).Count
Write-Host "Test directory: $TestDirPath" -ForegroundColor Yellow
Write-Host "Total files: $FileCount" -ForegroundColor Yellow
Write-Host ""

# Database path
$DbPath = "womcast.db"
$BackupPath = "womcast_backup.db"

# Get Python executable path
$PythonExe = "C:/Dev/WomCast/.venv/Scripts/python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "Error: Python executable not found: $PythonExe" -ForegroundColor Red
    Write-Host "Run: .\scripts\dev\configure_python.ps1" -ForegroundColor Yellow
    exit 1
}

# Function to run indexer and measure time
function Measure-IndexerRun {
    param(
        [string]$RunType,
        [string]$TestPath
    )
    
    Write-Host "--- $RunType Run ---" -ForegroundColor Cyan
    
    $StartTime = Get-Date
    & $PythonExe apps/backend/perf_wrapper.py $TestPath 2>&1 | Out-Host
    $EndTime = Get-Date
    
    $Duration = ($EndTime - $StartTime).TotalSeconds
    Write-Host "$RunType time: $([math]::Round($Duration, 2))s" -ForegroundColor Green
    Write-Host ""
    
    return $Duration
}

# Backup existing database if present
if (Test-Path $DbPath) {
    Write-Host "Backing up existing database..." -ForegroundColor Yellow
    Copy-Item $DbPath $BackupPath -Force
}

# === COLD CACHE TEST ===
Write-Host ""
Write-Host "=== Cold Cache Test ===" -ForegroundColor Cyan
Write-Host "Removing database and clearing cache..." -ForegroundColor Yellow
if (Test-Path $DbPath) {
    Remove-Item $DbPath -Force
}
[System.GC]::Collect()
Start-Sleep -Milliseconds 500

$ColdTime = Measure-IndexerRun -RunType "Cold" -TestPath $TestDirPath

# === WARM CACHE TEST ===
Write-Host ""
Write-Host "=== Warm Cache Test ===" -ForegroundColor Cyan
Write-Host "Running indexer again with warm cache..." -ForegroundColor Yellow

$WarmTime = Measure-IndexerRun -RunType "Warm" -TestPath $TestDirPath

# === RESULTS ===
Write-Host ""
Write-Host "=== Performance Results ===" -ForegroundColor Cyan
Write-Host "Test directory:     $TestDirPath"
Write-Host "Total files:        $FileCount"
Write-Host "Cold cache time:    $([math]::Round($ColdTime, 2))s"
Write-Host "Warm cache time:    $([math]::Round($WarmTime, 2))s"
Write-Host "Speedup:            $([math]::Round($ColdTime / $WarmTime, 2))x"
Write-Host "Cold throughput:    $([math]::Round($FileCount / $ColdTime, 1)) files/s"
Write-Host "Warm throughput:    $([math]::Round($FileCount / $WarmTime, 1)) files/s"

# Check performance thresholds
$Threshold = 5.0
if ($FileCount -ge 1000 -and $ColdTime -gt $Threshold) {
    Write-Host ""
    Write-Host "Performance Warning: Cold cache exceeded ${Threshold}s threshold for 1000+ files" -ForegroundColor Red
    Write-Host "Expected: <=${Threshold}s for 1k files" -ForegroundColor Yellow
    Write-Host "Actual:   $([math]::Round($ColdTime, 2))s" -ForegroundColor Yellow
    $ExitCode = 1
} else {
    Write-Host ""
    Write-Host "Performance OK: Cold cache within expected range" -ForegroundColor Green
    $ExitCode = 0
}

# Restore backup if it existed
if (Test-Path $BackupPath) {
    Write-Host ""
    Write-Host "Restoring original database..." -ForegroundColor Yellow
    Remove-Item $DbPath -Force -ErrorAction SilentlyContinue
    Move-Item $BackupPath $DbPath -Force
}

Write-Host ""
exit $ExitCode
