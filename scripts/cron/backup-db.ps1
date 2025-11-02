#!/usr/bin/env pwsh
# Automated database backup script for WomCast (PowerShell)
# Runs nightly via Task Scheduler to create and maintain backups

param(
    [string]$DbPath = "womcast.db",
    [string]$BackupDir = "backups",
    [int]$KeepBackups = 7
)

$ErrorActionPreference = "Stop"

$LogFile = "backup.log"

# Logging function
function Write-Log {
    param([string]$Message)
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$Timestamp] $Message"
    Write-Host $LogEntry
    Add-Content -Path $LogFile -Value $LogEntry
}

function Write-Error-Log {
    param([string]$Message)
    Write-Log "ERROR: $Message"
    Write-Error $Message
}

# Create backup directory
if (-not (Test-Path $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir -Force | Out-Null
}

# Check if database exists
if (-not (Test-Path $DbPath)) {
    Write-Error-Log "Database not found: $DbPath"
    exit 1
}

Write-Log "=== Starting database backup ==="
Write-Log "Database: $DbPath"
Write-Log "Backup directory: $BackupDir"

# Get Python executable
$PythonExe = "C:/Dev/WomCast/.venv/Scripts/python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Error-Log "Python not found: $PythonExe"
    exit 1
}

# Create backup
Write-Log "Creating backup..."
$BackupResult = & $PythonExe -m common.backup backup $DbPath $BackupDir 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Log "Backup created successfully"
    Write-Log $BackupResult
} else {
    Write-Error-Log "Backup creation failed: $BackupResult"
    exit 1
}

# Verify backup integrity
$LatestBackup = Get-ChildItem -Path $BackupDir -Filter "womcast_backup_*.db" | 
    Sort-Object LastWriteTime -Descending | 
    Select-Object -First 1

if ($LatestBackup) {
    Write-Log "Verifying backup: $($LatestBackup.Name)"
    $VerifyResult = & $PythonExe -m common.backup verify $LatestBackup.FullName 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Log "Backup verification passed"
    } else {
        Write-Error-Log "Backup verification failed: $VerifyResult"
        exit 1
    }
} else {
    Write-Error-Log "No backup file found after creation"
    exit 1
}

# Cleanup old backups
Write-Log "Cleaning up old backups (keeping $KeepBackups most recent)..."
$CleanupResult = & $PythonExe -m common.backup cleanup $BackupDir $KeepBackups 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Log "Cleanup completed"
    Write-Log $CleanupResult
} else {
    Write-Error-Log "Cleanup failed: $CleanupResult"
    exit 1
}

# List remaining backups
Write-Log "Current backups:"
Get-ChildItem -Path $BackupDir -Filter "womcast_backup_*.db" | 
    Format-Table Name, Length, LastWriteTime -AutoSize |
    Out-String |
    Write-Log

# Calculate backup size
$BackupSize = (Get-ChildItem -Path $BackupDir -Recurse | 
    Measure-Object -Property Length -Sum).Sum
$BackupSizeMB = [math]::Round($BackupSize / 1MB, 2)
Write-Log "Total backup size: $BackupSizeMB MB"

Write-Log "=== Backup completed successfully ==="

exit 0
