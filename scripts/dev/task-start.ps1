param([Parameter(Mandatory=$true)][string[]]$Id)
$ts = (Get-Date).ToUniversalTime().ToString("o")
$path = "docs/spec/TASKS.json"
if (!(Test-Path $path)) { Write-Host "No TASKS.json yet"; exit 0 }
$json = Get-Content $path -Raw | ConvertFrom-Json
foreach ($i in $Id) {
  $t = $json.tasks | Where-Object { $_.id -eq $i }
  if ($t -and -not $t.start_at_utc) { $t.start_at_utc = $ts; $t.status = "in_progress" }
}
$json | ConvertTo-Json -Depth 9 | Set-Content $path -Encoding UTF8