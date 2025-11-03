#!/usr/bin/env pwsh
# Frontend performance benchmark script
# Measures: Page load time, component render time, bundle size
# Usage: .\scripts\dev\perf-frontend.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "perf-frontend-results.json"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== WomCast Frontend Performance Benchmark ===" -ForegroundColor Cyan
Write-Host ""

# Navigate to frontend directory
$FrontendDir = "apps/frontend"
if (-not (Test-Path $FrontendDir)) {
    Write-Host "Error: Frontend directory not found: $FrontendDir" -ForegroundColor Red
    exit 1
}

Push-Location $FrontendDir

# Results storage
$Results = @{
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    tests = @()
}

# === Bundle Size Analysis ===
Write-Host "=== Bundle Size Analysis ===" -ForegroundColor Cyan
Write-Host "Building production bundle..." -ForegroundColor Yellow

try {
    $BuildOutput = npm run build 2>&1 | Out-String
    Write-Host $BuildOutput
    
    $DistDir = "dist"
    if (Test-Path $DistDir) {
        # Measure total bundle size
        $TotalSize = (Get-ChildItem -Path $DistDir -Recurse -File | Measure-Object -Property Length -Sum).Sum
        $TotalSizeMB = [math]::Round($TotalSize / 1MB, 2)
        
        # Measure JS bundle size
        $JsFiles = Get-ChildItem -Path "$DistDir/assets" -Filter "*.js" -File -ErrorAction SilentlyContinue
        $JsSize = ($JsFiles | Measure-Object -Property Length -Sum).Sum
        $JsSizeKB = [math]::Round($JsSize / 1KB, 1)
        
        # Measure CSS bundle size
        $CssFiles = Get-ChildItem -Path "$DistDir/assets" -Filter "*.css" -File -ErrorAction SilentlyContinue
        $CssSize = ($CssFiles | Measure-Object -Property Length -Sum).Sum
        $CssSizeKB = [math]::Round($CssSize / 1KB, 1)
        
        Write-Host "Total bundle size:    ${TotalSizeMB} MB" -ForegroundColor Green
        Write-Host "JavaScript bundle:    ${JsSizeKB} KB" -ForegroundColor Green
        Write-Host "CSS bundle:           ${CssSizeKB} KB" -ForegroundColor Green
        
        $Results.tests += @{
            name = "Bundle Size"
            total_mb = $TotalSizeMB
            js_kb = $JsSizeKB
            css_kb = $CssSizeKB
            js_files = $JsFiles.Count
            css_files = $CssFiles.Count
        }
    } else {
        Write-Host "Warning: Dist directory not found after build" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Error during build: $_" -ForegroundColor Red
    exit 1
}

# === TypeScript Compilation Performance ===
Write-Host ""
Write-Host "=== TypeScript Compilation Performance ===" -ForegroundColor Cyan
Write-Host "Running type check..." -ForegroundColor Yellow

$TscStartTime = Get-Date
try {
    npm run type-check 2>&1 | Out-Host
    $TscEndTime = Get-Date
    $TscDuration = ($TscEndTime - $TscStartTime).TotalSeconds
    
    Write-Host "TypeScript compilation: $([math]::Round($TscDuration, 2))s" -ForegroundColor Green
    
    $Results.tests += @{
        name = "TypeScript Compilation"
        duration_seconds = [math]::Round($TscDuration, 2)
    }
} catch {
    Write-Host "Type check failed: $_" -ForegroundColor Red
}

# === Lint Performance ===
Write-Host ""
Write-Host "=== Lint Performance ===" -ForegroundColor Cyan
Write-Host "Running ESLint..." -ForegroundColor Yellow

$LintStartTime = Get-Date
try {
    npm run lint 2>&1 | Out-Host
    $LintEndTime = Get-Date
    $LintDuration = ($LintEndTime - $LintStartTime).TotalSeconds
    
    Write-Host "ESLint execution: $([math]::Round($LintDuration, 2))s" -ForegroundColor Green
    
    $Results.tests += @{
        name = "ESLint"
        duration_seconds = [math]::Round($LintDuration, 2)
    }
} catch {
    Write-Host "Lint failed: $_" -ForegroundColor Red
}

# === Development Server Startup Time ===
Write-Host ""
Write-Host "=== Development Server Startup Time ===" -ForegroundColor Cyan
Write-Host "Starting dev server (will timeout after 30s)..." -ForegroundColor Yellow

$DevServerStartTime = Get-Date
$DevServerProcess = $null

try {
    # Start dev server in background
    $DevServerProcess = Start-Process -FilePath "npm" -ArgumentList "run", "dev" -NoNewWindow -PassThru
    
    # Wait for server to be ready (check for port 5173)
    $MaxWaitSeconds = 30
    $WaitInterval = 1
    $ElapsedSeconds = 0
    $ServerReady = $false
    
    while ($ElapsedSeconds -lt $MaxWaitSeconds) {
        try {
            $Response = Invoke-WebRequest -Uri "http://localhost:5173" -TimeoutSec 1 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($Response.StatusCode -eq 200) {
                $ServerReady = $true
                break
            }
        } catch {
            # Server not ready yet
        }
        
        Start-Sleep -Seconds $WaitInterval
        $ElapsedSeconds += $WaitInterval
        Write-Host "." -NoNewline
    }
    
    $DevServerEndTime = Get-Date
    $DevServerDuration = ($DevServerEndTime - $DevServerStartTime).TotalSeconds
    
    Write-Host ""
    if ($ServerReady) {
        Write-Host "Dev server startup: $([math]::Round($DevServerDuration, 2))s" -ForegroundColor Green
        
        $Results.tests += @{
            name = "Dev Server Startup"
            duration_seconds = [math]::Round($DevServerDuration, 2)
            success = $true
        }
    } else {
        Write-Host "Dev server failed to start within ${MaxWaitSeconds}s" -ForegroundColor Yellow
        
        $Results.tests += @{
            name = "Dev Server Startup"
            duration_seconds = $MaxWaitSeconds
            success = $false
        }
    }
} catch {
    Write-Host "Error starting dev server: $_" -ForegroundColor Red
} finally {
    # Kill dev server process
    if ($DevServerProcess) {
        Write-Host "Stopping dev server..." -ForegroundColor Yellow
        Stop-Process -Id $DevServerProcess.Id -Force -ErrorAction SilentlyContinue
        
        # Kill any remaining node processes on port 5173
        $NodeProcesses = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | ForEach-Object { Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue }
        foreach ($Proc in $NodeProcesses) {
            Stop-Process -Id $Proc.Id -Force -ErrorAction SilentlyContinue
        }
    }
}

# === Summary ===
Write-Host ""
Write-Host "=== Performance Summary ===" -ForegroundColor Cyan
Write-Host "Total tests: $($Results.tests.Count)"

# Save results to JSON
Write-Host ""
Write-Host "Saving results to $OutputFile..." -ForegroundColor Yellow
$Results | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFile
Write-Host "Results saved" -ForegroundColor Green

# Performance thresholds
Write-Host ""
Write-Host "=== Performance Thresholds ===" -ForegroundColor Cyan

$BundleTest = $Results.tests | Where-Object { $_.name -eq "Bundle Size" }
$TscTest = $Results.tests | Where-Object { $_.name -eq "TypeScript Compilation" }

$ExitCode = 0

# Bundle size threshold: < 5 MB total
if ($BundleTest -and $BundleTest.total_mb -gt 5) {
    Write-Host "⚠ Bundle size exceeded 5 MB threshold: $($BundleTest.total_mb) MB" -ForegroundColor Yellow
} else {
    Write-Host "✓ Bundle size within 5 MB threshold" -ForegroundColor Green
}

# JavaScript bundle threshold: < 1 MB
if ($BundleTest -and $BundleTest.js_kb -gt 1024) {
    Write-Host "⚠ JavaScript bundle exceeded 1 MB threshold: $([math]::Round($BundleTest.js_kb / 1024, 1)) MB" -ForegroundColor Yellow
} else {
    Write-Host "✓ JavaScript bundle within 1 MB threshold" -ForegroundColor Green
}

# TypeScript compilation threshold: < 30s
if ($TscTest -and $TscTest.duration_seconds -gt 30) {
    Write-Host "⚠ TypeScript compilation exceeded 30s threshold: $($TscTest.duration_seconds)s" -ForegroundColor Red
    $ExitCode = 1
} else {
    Write-Host "✓ TypeScript compilation within 30s threshold" -ForegroundColor Green
}

Pop-Location

Write-Host ""
exit $ExitCode
