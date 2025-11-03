#!/usr/bin/env pwsh
# Backend performance benchmark script
# Measures: Database queries, API endpoints, connector performance, memory usage
# Usage: .\scripts\dev\perf-backend.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "perf-backend-results.json"
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== WomCast Backend Performance Benchmark ===" -ForegroundColor Cyan
Write-Host ""

# Get Python executable path
$PythonExe = "C:/Dev/WomCast/.venv/Scripts/python.exe"
if (-not (Test-Path $PythonExe)) {
    Write-Host "Error: Python executable not found: $PythonExe" -ForegroundColor Red
    Write-Host "Run: .\scripts\dev\configure_python.ps1" -ForegroundColor Yellow
    exit 1
}

# Ensure backend server is running
Write-Host "Checking if backend server is running..." -ForegroundColor Yellow
$BackendUrl = "http://localhost:8000"
try {
    $Response = Invoke-RestMethod -Uri "$BackendUrl/health" -TimeoutSec 2
    Write-Host "Backend server is running" -ForegroundColor Green
} catch {
    Write-Host "Error: Backend server is not running at $BackendUrl" -ForegroundColor Red
    Write-Host "Start backend with: cd apps/backend && $PythonExe -m gateway.main" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Results storage
$Results = @{
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    backend_url = $BackendUrl
    tests = @()
}

# Function to measure API endpoint performance
function Measure-Endpoint {
    param(
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [object]$Body = $null,
        [int]$Iterations = 10
    )
    
    Write-Host "Testing $Name..." -ForegroundColor Cyan
    
    $Times = @()
    $Errors = 0
    
    for ($i = 1; $i -le $Iterations; $i++) {
        try {
            $StartTime = Get-Date
            
            if ($Method -eq "GET") {
                $Response = Invoke-RestMethod -Uri $Url -Method Get -TimeoutSec 30
            } elseif ($Method -eq "POST") {
                $Response = Invoke-RestMethod -Uri $Url -Method Post -Body ($Body | ConvertTo-Json) -ContentType "application/json" -TimeoutSec 30
            }
            
            $EndTime = Get-Date
            $Duration = ($EndTime - $StartTime).TotalMilliseconds
            $Times += $Duration
        } catch {
            $Errors++
            Write-Host "  Iteration $i failed: $_" -ForegroundColor Red
        }
    }
    
    if ($Times.Count -gt 0) {
        $AvgTime = ($Times | Measure-Object -Average).Average
        $MinTime = ($Times | Measure-Object -Minimum).Minimum
        $MaxTime = ($Times | Measure-Object -Maximum).Maximum
        $MedianTime = ($Times | Sort-Object)[[math]::Floor($Times.Count / 2)]
        
        Write-Host "  Avg: $([math]::Round($AvgTime, 1))ms | Min: $([math]::Round($MinTime, 1))ms | Max: $([math]::Round($MaxTime, 1))ms | Median: $([math]::Round($MedianTime, 1))ms" -ForegroundColor Green
        if ($Errors -gt 0) {
            Write-Host "  Errors: $Errors / $Iterations" -ForegroundColor Yellow
        }
        
        return @{
            name = $Name
            url = $Url
            method = $Method
            iterations = $Iterations
            avg_ms = [math]::Round($AvgTime, 2)
            min_ms = [math]::Round($MinTime, 2)
            max_ms = [math]::Round($MaxTime, 2)
            median_ms = [math]::Round($MedianTime, 2)
            errors = $Errors
            success_rate = [math]::Round((($Iterations - $Errors) / $Iterations) * 100, 1)
        }
    } else {
        Write-Host "  All iterations failed" -ForegroundColor Red
        return @{
            name = $Name
            url = $Url
            method = $Method
            iterations = $Iterations
            errors = $Errors
            success_rate = 0.0
        }
    }
}

# === Core API Endpoints ===
Write-Host "=== Core API Endpoints ===" -ForegroundColor Cyan
$Results.tests += Measure-Endpoint -Name "Health Check" -Url "$BackendUrl/health" -Iterations 20
$Results.tests += Measure-Endpoint -Name "Database Stats" -Url "$BackendUrl/v1/storage/stats" -Iterations 10
$Results.tests += Measure-Endpoint -Name "Get Playlists" -Url "$BackendUrl/v1/storage/playlists" -Iterations 10

# === Search Performance ===
Write-Host ""
Write-Host "=== Search Performance ===" -ForegroundColor Cyan
$Results.tests += Measure-Endpoint -Name "Search (Empty Query)" -Url "$BackendUrl/v1/search?q=" -Iterations 10
$Results.tests += Measure-Endpoint -Name "Search (Single Word)" -Url "$BackendUrl/v1/search?q=test" -Iterations 10
$Results.tests += Measure-Endpoint -Name "Search (Complex Query)" -Url "$BackendUrl/v1/search?q=test+movie+2024" -Iterations 10

# === Connector Performance ===
Write-Host ""
Write-Host "=== Connector Performance ===" -ForegroundColor Cyan
$Results.tests += Measure-Endpoint -Name "Internet Archive Collections" -Url "$BackendUrl/v1/connectors/internet-archive/collections" -Iterations 5
$Results.tests += Measure-Endpoint -Name "Internet Archive Search" -Url "$BackendUrl/v1/connectors/internet-archive/search?q=nasa&rows=20" -Iterations 5
$Results.tests += Measure-Endpoint -Name "NASA Live Streams" -Url "$BackendUrl/v1/connectors/nasa/live" -Iterations 5
$Results.tests += Measure-Endpoint -Name "PBS Featured" -Url "$BackendUrl/v1/connectors/pbs/featured?limit=20" -Iterations 5
$Results.tests += Measure-Endpoint -Name "Jamendo Popular" -Url "$BackendUrl/v1/connectors/jamendo/popular?limit=20" -Iterations 5

# === Live TV Performance ===
Write-Host ""
Write-Host "=== Live TV Performance ===" -ForegroundColor Cyan
$Results.tests += Measure-Endpoint -Name "Live TV Channels" -Url "$BackendUrl/v1/livetv/channels" -Iterations 10

# === Settings Performance ===
Write-Host ""
Write-Host "=== Settings Performance ===" -ForegroundColor Cyan
$Results.tests += Measure-Endpoint -Name "Get All Settings" -Url "$BackendUrl/v1/settings" -Iterations 10
$Results.tests += Measure-Endpoint -Name "Get Setting (kodi_host)" -Url "$BackendUrl/v1/settings/kodi_host" -Iterations 10

# === Summary ===
Write-Host ""
Write-Host "=== Performance Summary ===" -ForegroundColor Cyan

$TotalTests = $Results.tests.Count
$SuccessfulTests = ($Results.tests | Where-Object { $_.success_rate -eq 100.0 }).Count
$PartialFailures = ($Results.tests | Where-Object { $_.success_rate -lt 100.0 -and $_.success_rate -gt 0.0 }).Count
$TotalFailures = ($Results.tests | Where-Object { $_.success_rate -eq 0.0 }).Count

Write-Host "Total tests:          $TotalTests"
Write-Host "Successful (100%):    $SuccessfulTests" -ForegroundColor Green
if ($PartialFailures -gt 0) {
    Write-Host "Partial failures:     $PartialFailures" -ForegroundColor Yellow
}
if ($TotalFailures -gt 0) {
    Write-Host "Total failures:       $TotalFailures" -ForegroundColor Red
}

# Identify slowest endpoints
Write-Host ""
Write-Host "=== Slowest Endpoints ===" -ForegroundColor Cyan
$SlowestEndpoints = $Results.tests | Where-Object { $_.avg_ms -ne $null } | Sort-Object -Property avg_ms -Descending | Select-Object -First 5
foreach ($Test in $SlowestEndpoints) {
    Write-Host "  $($Test.name): $([math]::Round($Test.avg_ms, 1))ms avg" -ForegroundColor Yellow
}

# Identify fastest endpoints
Write-Host ""
Write-Host "=== Fastest Endpoints ===" -ForegroundColor Cyan
$FastestEndpoints = $Results.tests | Where-Object { $_.avg_ms -ne $null } | Sort-Object -Property avg_ms | Select-Object -First 5
foreach ($Test in $FastestEndpoints) {
    Write-Host "  $($Test.name): $([math]::Round($Test.avg_ms, 1))ms avg" -ForegroundColor Green
}

# Save results to JSON
Write-Host ""
Write-Host "Saving results to $OutputFile..." -ForegroundColor Yellow
$Results | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFile
Write-Host "Results saved" -ForegroundColor Green

# Performance thresholds
Write-Host ""
Write-Host "=== Performance Thresholds ===" -ForegroundColor Cyan
$ThresholdHealth = 100
$ThresholdSearch = 500
$ThresholdConnector = 3000

$HealthTest = $Results.tests | Where-Object { $_.name -eq "Health Check" }
$SearchTest = $Results.tests | Where-Object { $_.name -eq "Search (Single Word)" }
$ConnectorTest = $Results.tests | Where-Object { $_.name -eq "Internet Archive Collections" }

$ExitCode = 0

if ($HealthTest -and $HealthTest.avg_ms -gt $ThresholdHealth) {
    Write-Host "⚠ Health Check exceeded ${ThresholdHealth}ms threshold: $([math]::Round($HealthTest.avg_ms, 1))ms" -ForegroundColor Red
    $ExitCode = 1
} else {
    Write-Host "✓ Health Check within ${ThresholdHealth}ms threshold" -ForegroundColor Green
}

if ($SearchTest -and $SearchTest.avg_ms -gt $ThresholdSearch) {
    Write-Host "⚠ Search exceeded ${ThresholdSearch}ms threshold: $([math]::Round($SearchTest.avg_ms, 1))ms" -ForegroundColor Red
    $ExitCode = 1
} else {
    Write-Host "✓ Search within ${ThresholdSearch}ms threshold" -ForegroundColor Green
}

if ($ConnectorTest -and $ConnectorTest.avg_ms -gt $ThresholdConnector) {
    Write-Host "⚠ Connector exceeded ${ThresholdConnector}ms threshold: $([math]::Round($ConnectorTest.avg_ms, 1))ms" -ForegroundColor Yellow
} else {
    Write-Host "✓ Connector within ${ThresholdConnector}ms threshold" -ForegroundColor Green
}

Write-Host ""
exit $ExitCode
