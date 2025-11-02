param([Parameter(Mandatory=$true)][string[]]$Id)
$ts = (Get-Date).ToUniversalTime().ToString("o")
$path = "docs/spec/TASKS.json"
if (!(Test-Path $path)) { Write-Host "No TASKS.json yet"; exit 0 }
$json = Get-Content $path -Raw | ConvertFrom-Json
foreach ($i in $Id) {
  $t = $json.tasks | Where-Object { $_.id -eq $i }
  if ($t) {
    if (-not $t.start_at_utc) { $t.start_at_utc = $ts }
    $t.end_at_utc = $ts
    try { $t.duration_h = [math]::Round(((New-TimeSpan -Start $t.start_at_utc -End $t.end_at_utc).TotalHours), 2) } catch {}
    $t.status = "done"
  }
}
$json | ConvertTo-Json -Depth 9 | Set-Content $path -Encoding UTF8
Add-Content CHANGELOG.md "`n- [$ts] Completed tasks: $($Id -join ', ')"