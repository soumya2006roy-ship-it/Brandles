param([ValidateSet('api', 'worker', 'web')][string]$Service, [ValidateSet('dev', 'prod')][string]$Mode)
$ErrorActionPreference = 'Continue'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logDir = Join-Path $root 'logs'
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$Host.UI.RawUI.WindowTitle = "BrandLens - $Service ($Mode)"

if ($Service -eq 'api' -or $Service -eq 'worker') {
  $python = Join-Path $root 'api/.venv/Scripts/python.exe'
  $workingDirectory = Join-Path $root 'api'
  if ($Service -eq 'api' -and $Mode -eq 'dev') { $program = $python; $arguments = @('-m', 'uvicorn', 'app.main:app', '--reload', '--host', '127.0.0.1', '--port', '8000') }
  elseif ($Service -eq 'api') { $program = $python; $arguments = @('-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8000') }
  else { $program = $python; $arguments = @('-m', 'app.worker') }
} else {
  $program = 'npm.cmd'
  $workingDirectory = $root
  if ($Mode -eq 'dev') { $arguments = @('run', 'dev', '--', '--hostname', '127.0.0.1') }
  else { $arguments = @('run', 'start') }
}
Set-Location -LiteralPath $workingDirectory
Write-Host "Starting $Service; output is also written to logs/$Service.log."
& $program @arguments 2>&1 | Tee-Object -FilePath (Join-Path $logDir "$Service.log")
$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) { $exitCode = 1 }
Write-Host "$Service exited with code $exitCode. Press Enter to close this log window."
Read-Host | Out-Null
exit $exitCode
