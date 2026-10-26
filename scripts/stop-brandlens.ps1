param([switch]$Containers)
$ErrorActionPreference = 'Continue'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logs = Join-Path $root 'logs'
foreach ($service in @('web', 'worker', 'api')) {
  $pidPath = Join-Path $logs "$service.pid"
  if (-not (Test-Path $pidPath)) { continue }
  $processId = 0
  if ([int]::TryParse((Get-Content -Raw $pidPath).Trim(), [ref]$processId)) {
    $process = Get-CimInstance Win32_Process -Filter "ProcessId = $processId" -ErrorAction SilentlyContinue
    if ($process -and $process.CommandLine -like '*run-service.ps1*') {
      & taskkill.exe /PID $processId /T /F | Out-Null
    }
  }
  Remove-Item -LiteralPath $pidPath -Force -ErrorAction SilentlyContinue
}
if ($Containers) {
  $docker = Get-Command docker.exe -ErrorAction SilentlyContinue
  if (-not $docker -and $env:LOCALAPPDATA) {
    $perUserDocker = Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin'
    if (Test-Path (Join-Path $perUserDocker 'docker.exe')) {
      $env:PATH = "$perUserDocker;$env:PATH"
      $docker = Get-Command docker.exe -ErrorAction SilentlyContinue
    }
  }
  if (-not $docker) {
    Write-Host 'Docker data services were not stopped because docker.exe is unavailable.'
  }
  else {
    & docker.exe info *> $null
    if ($LASTEXITCODE -ne 0) {
      Write-Host 'Docker data services were not stopped because the Docker engine is unavailable. Start Docker Desktop and run stop.bat containers again.'
    }
    else {
      Push-Location $root
      & docker.exe compose stop db redis mailpit *> $null
      $stopCode = $LASTEXITCODE
      Pop-Location
      if ($stopCode -eq 0) { Write-Host 'Docker data services have been stopped.' }
      else { Write-Host 'Docker could not stop all data services. Check Docker Desktop and run docker compose ps for their status.' }
    }
  }
}
Write-Host 'BrandLens web, API and worker processes have been stopped.'
