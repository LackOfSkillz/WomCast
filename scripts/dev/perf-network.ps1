#!/usr/bin/env pwsh
# Network performance benchmark script
# Measures: Connector API latency, Kodi JSON-RPC response times, circuit breaker behavior
# Usage: .\scripts\dev\perf-network.ps1

param(
    [Parameter(Mandatory=$false)]
    [string]$OutputFile = "perf-network-results.json",
    [Parameter(Mandatory=$false)]
    [string]$KodiHost = "localhost",
    [Parameter(Mandatory=$false)]
    [int]$KodiPort = 9090
)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=== WomCast Network Performance Benchmark ===" -ForegroundColor Cyan
Write-Host ""

# Results storage
$Results = @{
    timestamp = Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ"
    kodi_host = $KodiHost
    kodi_port = $KodiPort
    tests = @()
}

# Function to measure network request latency
function Measure-NetworkLatency {
    param(
        [string]$Name,
        [string]$Url,
        [int]$Iterations = 5,
        [hashtable]$Headers = @{}
    )
    
    Write-Host "Testing $Name..." -ForegroundColor Cyan
    
    $Times = @()
    $Errors = 0
    
    for ($i = 1; $i -le $Iterations; $i++) {
        try {
            $StartTime = Get-Date
            $Response = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -Headers $Headers -UseBasicParsing
            $EndTime = Get-Date
            
            $Duration = ($EndTime - $StartTime).TotalMilliseconds
            $Times += $Duration
            
            Write-Host "  Iteration $i: $([math]::Round($Duration, 1))ms (Status: $($Response.StatusCode))" -ForegroundColor Gray
        } catch {
            $Errors++
            Write-Host "  Iteration $i failed: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    
    if ($Times.Count -gt 0) {
        $AvgTime = ($Times | Measure-Object -Average).Average
        $MinTime = ($Times | Measure-Object -Minimum).Minimum
        $MaxTime = ($Times | Measure-Object -Maximum).Maximum
        
        Write-Host "  Avg: $([math]::Round($AvgTime, 1))ms | Min: $([math]::Round($MinTime, 1))ms | Max: $([math]::Round($MaxTime, 1))ms" -ForegroundColor Green
        
        return @{
            name = $Name
            url = $Url
            iterations = $Iterations
            avg_ms = [math]::Round($AvgTime, 2)
            min_ms = [math]::Round($MinTime, 2)
            max_ms = [math]::Round($MaxTime, 2)
            errors = $Errors
            success_rate = [math]::Round((($Iterations - $Errors) / $Iterations) * 100, 1)
        }
    } else {
        Write-Host "  All iterations failed" -ForegroundColor Red
        return @{
            name = $Name
            url = $Url
            iterations = $Iterations
            errors = $Errors
            success_rate = 0.0
        }
    }
}

# === Internet Archive Connector ===
Write-Host "=== Internet Archive Connector ===" -ForegroundColor Cyan
$Results.tests += Measure-NetworkLatency -Name "IA: Collections API" -Url "https://archive.org/advancedsearch.php?q=mediatype:collection&fl=identifier,title&rows=10&output=json" -Iterations 5
$Results.tests += Measure-NetworkLatency -Name "IA: Search API" -Url "https://archive.org/advancedsearch.php?q=nasa&fl=identifier,title,description&rows=20&output=json" -Iterations 5
$Results.tests += Measure-NetworkLatency -Name "IA: Metadata API" -Url "https://archive.org/metadata/nasa" -Iterations 5

# === NASA API ===
Write-Host ""
Write-Host "=== NASA API ===" -ForegroundColor Cyan
$Results.tests += Measure-NetworkLatency -Name "NASA: Image/Video Library Search" -Url "https://images-api.nasa.gov/search?q=apollo&media_type=image" -Iterations 5
$Results.tests += Measure-NetworkLatency -Name "NASA: Item Metadata" -Url "https://images-api.nasa.gov/search?nasa_id=as11-40-5903" -Iterations 5

# === PBS API (Note: PBS may require API key or have rate limits) ===
Write-Host ""
Write-Host "=== PBS API ===" -ForegroundColor Cyan
Write-Host "Note: PBS API may require authentication or have strict rate limits" -ForegroundColor Yellow
# $Results.tests += Measure-NetworkLatency -Name "PBS: Content API" -Url "https://www.pbs.org/search/api/?q=nova" -Iterations 3

# === Jamendo API ===
Write-Host ""
Write-Host "=== Jamendo API ===" -ForegroundColor Cyan
$Results.tests += Measure-NetworkLatency -Name "Jamendo: Tracks API" -Url "https://api.jamendo.com/v3.0/tracks/?client_id=56d30c95&format=json&limit=10" -Iterations 5

# === Kodi JSON-RPC ===
Write-Host ""
Write-Host "=== Kodi JSON-RPC ===" -ForegroundColor Cyan
$KodiUrl = "http://${KodiHost}:${KodiPort}/jsonrpc"

Write-Host "Testing Kodi at $KodiUrl..." -ForegroundColor Yellow

# Check if Kodi is reachable
try {
    $PingBody = @{
        jsonrpc = "2.0"
        method = "JSONRPC.Ping"
        id = 1
    } | ConvertTo-Json
    
    $PingStartTime = Get-Date
    $PingResponse = Invoke-RestMethod -Uri $KodiUrl -Method Post -Body $PingBody -ContentType "application/json" -TimeoutSec 5
    $PingEndTime = Get-Date
    $PingDuration = ($PingEndTime - $PingStartTime).TotalMilliseconds
    
    Write-Host "Kodi is reachable (Ping: $([math]::Round($PingDuration, 1))ms)" -ForegroundColor Green
    
    $Results.tests += @{
        name = "Kodi: JSON-RPC Ping"
        url = $KodiUrl
        duration_ms = [math]::Round($PingDuration, 2)
        success = $true
    }
    
    # Test Player.GetActivePlayers
    $PlayersBody = @{
        jsonrpc = "2.0"
        method = "Player.GetActivePlayers"
        id = 2
    } | ConvertTo-Json
    
    $PlayersStartTime = Get-Date
    $PlayersResponse = Invoke-RestMethod -Uri $KodiUrl -Method Post -Body $PlayersBody -ContentType "application/json" -TimeoutSec 5
    $PlayersEndTime = Get-Date
    $PlayersDuration = ($PlayersEndTime - $PlayersStartTime).TotalMilliseconds
    
    Write-Host "Kodi: GetActivePlayers ($([math]::Round($PlayersDuration, 1))ms)" -ForegroundColor Green
    
    $Results.tests += @{
        name = "Kodi: Get Active Players"
        url = $KodiUrl
        duration_ms = [math]::Round($PlayersDuration, 2)
        success = $true
    }
} catch {
    Write-Host "Kodi is not reachable: $($_.Exception.Message)" -ForegroundColor Yellow
    Write-Host "Make sure Kodi is running at ${KodiHost}:${KodiPort} with JSON-RPC enabled" -ForegroundColor Yellow
    
    $Results.tests += @{
        name = "Kodi: JSON-RPC Ping"
        url = $KodiUrl
        success = $false
        error = $_.Exception.Message
    }
}

# === DNS Resolution Performance ===
Write-Host ""
Write-Host "=== DNS Resolution Performance ===" -ForegroundColor Cyan

$DnsTargets = @(
    "archive.org",
    "images-api.nasa.gov",
    "api.jamendo.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com"
)

foreach ($Target in $DnsTargets) {
    try {
        $DnsStartTime = Get-Date
        $DnsResult = Resolve-DnsName -Name $Target -Type A -QuickTimeout -ErrorAction Stop
        $DnsEndTime = Get-Date
        $DnsDuration = ($DnsEndTime - $DnsStartTime).TotalMilliseconds
        
        Write-Host "  $Target : $([math]::Round($DnsDuration, 1))ms" -ForegroundColor Green
        
        $Results.tests += @{
            name = "DNS: $Target"
            target = $Target
            duration_ms = [math]::Round($DnsDuration, 2)
            success = $true
            ip_address = $DnsResult[0].IPAddress
        }
    } catch {
        Write-Host "  $Target : FAILED" -ForegroundColor Red
        
        $Results.tests += @{
            name = "DNS: $Target"
            target = $Target
            success = $false
            error = $_.Exception.Message
        }
    }
}

# === Summary ===
Write-Host ""
Write-Host "=== Performance Summary ===" -ForegroundColor Cyan

$TotalTests = $Results.tests.Count
$SuccessfulTests = ($Results.tests | Where-Object { $_.success -eq $true -or $_.success_rate -eq 100.0 }).Count
$PartialFailures = ($Results.tests | Where-Object { $_.success_rate -lt 100.0 -and $_.success_rate -gt 0.0 }).Count
$TotalFailures = ($Results.tests | Where-Object { $_.success -eq $false -or $_.success_rate -eq 0.0 }).Count

Write-Host "Total tests:          $TotalTests"
Write-Host "Successful:           $SuccessfulTests" -ForegroundColor Green
if ($PartialFailures -gt 0) {
    Write-Host "Partial failures:     $PartialFailures" -ForegroundColor Yellow
}
if ($TotalFailures -gt 0) {
    Write-Host "Total failures:       $TotalFailures" -ForegroundColor Yellow
}

# Identify slowest network calls
Write-Host ""
Write-Host "=== Slowest Network Calls ===" -ForegroundColor Cyan
$SlowestCalls = $Results.tests | Where-Object { $_.avg_ms -ne $null -or $_.duration_ms -ne $null } | ForEach-Object {
    if ($_.avg_ms) {
        $_ | Add-Member -MemberType NoteProperty -Name latency_ms -Value $_.avg_ms -PassThru
    } elseif ($_.duration_ms) {
        $_ | Add-Member -MemberType NoteProperty -Name latency_ms -Value $_.duration_ms -PassThru
    }
} | Sort-Object -Property latency_ms -Descending | Select-Object -First 5

foreach ($Call in $SlowestCalls) {
    Write-Host "  $($Call.name): $([math]::Round($Call.latency_ms, 1))ms" -ForegroundColor Yellow
}

# Identify fastest network calls
Write-Host ""
Write-Host "=== Fastest Network Calls ===" -ForegroundColor Cyan
$FastestCalls = $Results.tests | Where-Object { $_.avg_ms -ne $null -or $_.duration_ms -ne $null } | ForEach-Object {
    if ($_.avg_ms) {
        $_ | Add-Member -MemberType NoteProperty -Name latency_ms -Value $_.avg_ms -PassThru -Force
    } elseif ($_.duration_ms) {
        $_ | Add-Member -MemberType NoteProperty -Name latency_ms -Value $_.duration_ms -PassThru -Force
    }
} | Sort-Object -Property latency_ms | Select-Object -First 5

foreach ($Call in $FastestCalls) {
    Write-Host "  $($Call.name): $([math]::Round($Call.latency_ms, 1))ms" -ForegroundColor Green
}

# Save results to JSON
Write-Host ""
Write-Host "Saving results to $OutputFile..." -ForegroundColor Yellow
$Results | ConvertTo-Json -Depth 10 | Set-Content -Path $OutputFile
Write-Host "Results saved" -ForegroundColor Green

# Performance thresholds
Write-Host ""
Write-Host "=== Performance Thresholds ===" -ForegroundColor Cyan

$ExitCode = 0

# Kodi latency threshold: < 100ms
$KodiTest = $Results.tests | Where-Object { $_.name -eq "Kodi: JSON-RPC Ping" }
if ($KodiTest -and $KodiTest.success -and $KodiTest.duration_ms -gt 100) {
    Write-Host "⚠ Kodi latency exceeded 100ms threshold: $([math]::Round($KodiTest.duration_ms, 1))ms" -ForegroundColor Yellow
} elseif ($KodiTest -and $KodiTest.success) {
    Write-Host "✓ Kodi latency within 100ms threshold" -ForegroundColor Green
} else {
    Write-Host "⚠ Kodi not reachable (skipping threshold check)" -ForegroundColor Yellow
}

# DNS resolution threshold: < 100ms average
$DnsTests = $Results.tests | Where-Object { $_.name -like "DNS:*" -and $_.success -eq $true }
if ($DnsTests.Count -gt 0) {
    $AvgDns = ($DnsTests | Measure-Object -Property duration_ms -Average).Average
    if ($AvgDns -gt 100) {
        Write-Host "⚠ Average DNS resolution exceeded 100ms threshold: $([math]::Round($AvgDns, 1))ms" -ForegroundColor Yellow
    } else {
        Write-Host "✓ Average DNS resolution within 100ms threshold: $([math]::Round($AvgDns, 1))ms" -ForegroundColor Green
    }
}

# Connector API latency threshold: < 3000ms
$ConnectorTests = $Results.tests | Where-Object { $_.name -like "IA:*" -or $_.name -like "NASA:*" -or $_.name -like "Jamendo:*" }
$SlowConnectors = $ConnectorTests | Where-Object { $_.avg_ms -gt 3000 }
if ($SlowConnectors.Count -gt 0) {
    Write-Host "⚠ $($SlowConnectors.Count) connector(s) exceeded 3000ms threshold" -ForegroundColor Yellow
    foreach ($Slow in $SlowConnectors) {
        Write-Host "    $($Slow.name): $([math]::Round($Slow.avg_ms, 1))ms" -ForegroundColor Yellow
    }
} else {
    Write-Host "✓ All connectors within 3000ms threshold" -ForegroundColor Green
}

Write-Host ""
exit $ExitCode
