param([switch]$Containers)
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logs = Join-Path $root 'logs'
foreach ($service in @('web', 'worker', 'api')) {
  $pidPath = Join-Path $logs "$service.pid"
  if (-not (Test-Path $pidPath)) { continue }
  $processId = 0
  if ([int]::TryParse((Get-Content -Raw $pidPath).Trim(), [ref]$processId)) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -like '*run-service.ps1*') {
      & taskkill.exe /PID $processId /T | Out-Null
      Start-Sleep -Seconds 3
      if (Get-Process -Id $processId -ErrorAction SilentlyContinue) { & taskkill.exe /PID $processId /T /F | Out-Null }
    }
  }
  Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}
if ($Containers) {
  Push-Location $root
  & docker.exe compose stop db redis minio minio-init mailpit
  Pop-Location
}
Write-Host 'BrandLens web, API and worker processes have been stopped. Use -Containers to stop local data services too.'
