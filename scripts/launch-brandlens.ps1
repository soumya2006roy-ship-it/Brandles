param([ValidateSet('dev', 'prod')][string]$Mode = 'dev')
$ErrorActionPreference = 'Stop'
# PowerShell 7 can turn a native program's stderr into a terminating error.
# Docker uses stderr for daemon connection failures, which should be handled by
# its exit code so this script can show the actionable launcher diagnostic.
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$logs = Join-Path $root 'logs'
$script:StartedDataServices = $false
New-Item -ItemType Directory -Path $logs -Force | Out-Null

function Stop-WithMessage([string]$Message) {
  Write-Host "ERROR: $Message" -ForegroundColor Red
  $stopScript = Join-Path $PSScriptRoot 'stop-brandlens.ps1'
  if (Test-Path $stopScript) {
    if ($script:StartedDataServices) { & $stopScript -Containers | Out-Null }
    else { & $stopScript | Out-Null }
  }
  Write-Host 'No service windows were left running.'
  exit 1
}
trap {
  Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
  if (Test-Path (Join-Path $PSScriptRoot 'stop-brandlens.ps1')) {
    if ($script:StartedDataServices) { & (Join-Path $PSScriptRoot 'stop-brandlens.ps1') -Containers | Out-Null }
    else { & (Join-Path $PSScriptRoot 'stop-brandlens.ps1') | Out-Null }
  }
  exit 1
}

function Get-CommandVersion([string]$Command, [string[]]$Arguments) {
  $output = & $Command @Arguments 2>&1
  if ($LASTEXITCODE -ne 0) { return $null }
  return ($output | Select-Object -First 1).ToString()
}

function Get-MajorMinor([string]$Version) {
  $match = [regex]::Match($Version, '(\d+)\.(\d+)')
  if (-not $match.Success) { return $null }
  return [version]::new([int]$match.Groups[1].Value, [int]$match.Groups[2].Value)
}

if (-not (Get-Command node.exe -ErrorAction SilentlyContinue)) { Stop-WithMessage 'Node.js 20.9 or newer is required. Install the LTS release from https://nodejs.org/ and reopen this window.' }
if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) { Stop-WithMessage 'npm is required. Reinstall Node.js 20.9 or newer from https://nodejs.org/.' }
$nodeVersion = Get-CommandVersion 'node.exe' @('--version')
if (-not $nodeVersion -or (Get-MajorMinor $nodeVersion) -lt [version]::new(20, 9)) { Stop-WithMessage "Node.js 20.9 or newer is required; detected $nodeVersion." }
$npmVersion = Get-CommandVersion 'npm.cmd' @('--version')
if (-not $npmVersion -or (Get-MajorMinor $npmVersion) -lt [version]::new(10, 0)) { Stop-WithMessage "npm 10 or newer is required; detected $npmVersion. Reinstall Node.js 20.9 or newer from https://nodejs.org/." }
if (-not (Get-Command python.exe -ErrorAction SilentlyContinue)) { Stop-WithMessage 'Python 3.12 or newer is required. Install it from https://www.python.org/downloads/windows/ and enable Add Python to PATH.' }
$pythonVersion = Get-CommandVersion 'python.exe' @('--version')
if (-not $pythonVersion -or (Get-MajorMinor $pythonVersion) -lt [version]::new(3, 12)) { Stop-WithMessage "Python 3.12 or newer is required; detected $pythonVersion." }
if (-not (Get-Command docker.exe -ErrorAction SilentlyContinue)) { Stop-WithMessage 'Docker Desktop with Docker Compose is required for PostgreSQL, Redis and MinIO. Install it from https://www.docker.com/products/docker-desktop/, start Docker Desktop, then run this launcher again.' }
& docker.exe info *> $null
if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Docker Desktop is installed, but its engine is unavailable. Start Docker Desktop, wait until it reports that the engine is running, then run this launcher again.' }
& docker.exe compose version *> $null
if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Docker Compose is unavailable. Update Docker Desktop, then try again.' }

$priorRunHealthy = $true
foreach ($service in @('api', 'worker', 'web')) {
  $pidPath = Join-Path $logs "$service.pid"
  if (-not (Test-Path $pidPath)) { $priorRunHealthy = $false; break }
  $priorPid = 0
  if (-not [int]::TryParse((Get-Content -Raw $pidPath).Trim(), [ref]$priorPid)) { $priorRunHealthy = $false; break }
  $priorProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $priorPid" -ErrorAction SilentlyContinue
  if (-not $priorProcess -or $priorProcess.CommandLine -notlike '*run-service.ps1*') { $priorRunHealthy = $false; break }
}
if ($priorRunHealthy) {
  $apiHealthy = $false; $webHealthy = $false
  try { $apiHealthy = (Invoke-WebRequest 'http://127.0.0.1:8000/health' -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 } catch { }
  try { $webHealthy = (Invoke-WebRequest 'http://127.0.0.1:3000/' -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 } catch { }
  $currentLockHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'package-lock.json')).Hash
  $currentRequirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'api/requirements.txt')).Hash
  $modePath = Join-Path $logs '.mode'
  $sameMode = (Test-Path $modePath) -and ((Get-Content -Raw $modePath).Trim() -eq "$Mode $currentLockHash $currentRequirementsHash")
  if ($sameMode -and $apiHealthy -and $webHealthy) {
    Write-Host 'BrandLens is already running and healthy at http://localhost:3000/.' -ForegroundColor Green
    Start-Process 'http://localhost:3000/'
    exit 0
  }
  & (Join-Path $PSScriptRoot 'stop-brandlens.ps1') | Out-Null
}

$ports = @(3000, 8000, 5432, 6379, 9000, 9001, 8025, 1025)
foreach ($port in $ports) {
  $listeners = @(Get-NetTCPConnection -State Listen -LocalPort $port -ErrorAction SilentlyContinue)
  if ($listeners.Count -gt 0) {
    $owners = @($listeners | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
      $process = Get-CimInstance Win32_Process -Filter "ProcessId = $_" -ErrorAction SilentlyContinue
      if ($process) { "$($process.Name) (PID $_)" } else { "PID $_" }
    }) -join ', '
    Stop-WithMessage "Port $port is already in use by $owners. Stop that process and run the launcher again."
  }
}

$envPath = Join-Path $root '.env'
$apiEnvPath = Join-Path $root 'api/.env'
if (-not (Test-Path $envPath)) {
  $example = Join-Path $root '.env.example'
  if (-not (Test-Path $example)) { Stop-WithMessage 'The repository .env.example is missing.' }
  $secretBytes = New-Object byte[] 48
  $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
  $rng.GetBytes($secretBytes)
  $secret = [Convert]::ToBase64String($secretBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
  $adminBytes = New-Object byte[] 30
  $rng.GetBytes($adminBytes)
  $adminPassword = [Convert]::ToBase64String($adminBytes).TrimEnd('=').Replace('+','-').Replace('/','_')
  $content = [IO.File]::ReadAllText($example)
  $content = [regex]::Replace($content, '(?m)^APP_SECRET_KEY=.*$', "APP_SECRET_KEY=$secret")
  $content = [regex]::Replace($content, '(?m)^BOOTSTRAP_ADMIN_PASSWORD=.*$', "BOOTSTRAP_ADMIN_PASSWORD=$adminPassword")
  $content = [regex]::Replace($content, '(?m)^MINIO_ROOT_PASSWORD=.*$', "MINIO_ROOT_PASSWORD=$secret")
  $content = [regex]::Replace($content, '(?m)^S3_SECRET_ACCESS_KEY=.*$', "S3_SECRET_ACCESS_KEY=$secret")
  [IO.File]::WriteAllText($envPath, $content, [System.Text.UTF8Encoding]::new($false))
  Write-Host 'First-run settings created. The generated development administrator password is stored in .env; change it after signing in.'
}
if (-not (Test-Path $apiEnvPath)) { Copy-Item -LiteralPath $envPath -Destination $apiEnvPath }

$envLines = Get-Content -LiteralPath $envPath
foreach ($line in $envLines) {
  if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)=(.*)$') {
    $key = $Matches[1]
    $value = $Matches[2].Trim()
    if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'")))) { $value = $value.Substring(1, $value.Length - 2) }
    [Environment]::SetEnvironmentVariable($key, $value, 'Process')
  }
}
$env:BRANDLENS_LAUNCH_MODE = $Mode

$lockPath = Join-Path $root 'package-lock.json'
$npmMarker = Join-Path $root '.brandlens-npm-lock-hash'
$lockHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $lockPath).Hash
if (-not (Test-Path (Join-Path $root 'node_modules')) -or -not (Test-Path $npmMarker) -or (Get-Content -Raw $npmMarker).Trim() -ne $lockHash) {
  Write-Host 'Installing web dependencies with npm ci...'
  Push-Location $root
  & npm.cmd ci
  $installCode = $LASTEXITCODE
  Pop-Location
  if ($installCode -ne 0) { Stop-WithMessage 'npm ci failed. See the output above, fix the dependency issue and retry.' }
  Set-Content -LiteralPath $npmMarker -Value $lockHash -NoNewline
}

$venvPython = Join-Path $root 'api/.venv/Scripts/python.exe'
if (-not (Test-Path $venvPython)) {
  Write-Host 'Creating the API Python environment...'
  Push-Location (Join-Path $root 'api')
  & python.exe -m venv .venv
  $venvCode = $LASTEXITCODE
  Pop-Location
  if ($venvCode -ne 0) { Stop-WithMessage 'Could not create api/.venv.' }
}
$requirementsHash = (Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $root 'api/requirements.txt')).Hash
$requirementsMarker = Join-Path $root 'api/.venv/.brandlens-requirements-hash'
if (-not (Test-Path $requirementsMarker) -or (Get-Content -Raw $requirementsMarker).Trim() -ne $requirementsHash) {
  Write-Host 'Installing API dependencies...'
  & $venvPython -m pip install -r (Join-Path $root 'api/requirements.txt')
  if ($LASTEXITCODE -ne 0) { Stop-WithMessage 'Installing API dependencies failed.' }
  Set-Content -LiteralPath $requirementsMarker -Value $requirementsHash -NoNewline
}

Write-Host 'Starting PostgreSQL, Redis, MinIO and local mail capture...'
$script:StartedDataServices = $true
Push-Location $root
& docker.exe compose up -d db redis minio minio-init mailpit *> $null
$composeCode = $LASTEXITCODE
Pop-Location
if ($composeCode -ne 0) { Stop-WithMessage 'Docker Compose could not start the data services. Check that Docker Desktop is running, then run docker compose logs db redis minio minio-init mailpit for details.' }

$healthDeadline = [DateTime]::UtcNow.AddMinutes(2)
while ([DateTime]::UtcNow -lt $healthDeadline) {
  $healthy = $true
  foreach ($service in @('db', 'redis')) {
    Push-Location $root
    $containerOutput = & docker.exe compose ps -q $service | Select-Object -First 1
    $containerId = [string]$containerOutput
    $containerId = $containerId.Trim()
    Pop-Location
    if (-not $containerId) { $healthy = $false; continue }
    $stateOutput = & docker.exe inspect --format '{{.State.Health.Status}}' $containerId 2>$null | Select-Object -First 1
    $state = [string]$stateOutput
    $state = $state.Trim()
    if ($state -ne 'healthy') { $healthy = $false }
  }
  Push-Location $root
  $initOutput = & docker.exe compose ps -a -q minio-init | Select-Object -First 1
  Pop-Location
  $initId = ([string]$initOutput).Trim()
  if (-not $initId) { $healthy = $false }
  else {
    $initStatus = [string](& docker.exe inspect --format '{{.State.Status}}' $initId 2>$null | Select-Object -First 1)
    $initExitCode = [string](& docker.exe inspect --format '{{.State.ExitCode}}' $initId 2>$null | Select-Object -First 1)
    if ($initStatus.Trim() -ne 'exited' -or $initExitCode.Trim() -ne '0') { $healthy = $false }
  }
  if ($healthy) { break }
  Start-Sleep -Seconds 2
}
if (-not $healthy) {
  Push-Location $root
  & docker.exe compose ps
  & docker.exe compose logs --tail 80 db redis minio minio-init
  Pop-Location
  Stop-WithMessage 'PostgreSQL, Redis or object storage did not become healthy within two minutes.'
}

Write-Host 'Applying database migrations...'
Push-Location (Join-Path $root 'api')
& $venvPython -m alembic upgrade head
$migrationCode = $LASTEXITCODE
Pop-Location
if ($migrationCode -ne 0) { Stop-WithMessage 'Database migration failed. Review the migration output and API database settings.' }
Write-Host 'Checking first platform administrator bootstrap...'
Push-Location (Join-Path $root 'api')
& $venvPython -m app.cli bootstrap-platform-admin
$adminCode = $LASTEXITCODE
Pop-Location
if ($adminCode -ne 0) { Stop-WithMessage 'Platform administrator bootstrap failed. Check BOOTSTRAP_ADMIN_EMAIL and BOOTSTRAP_ADMIN_PASSWORD in .env.' }

if ($Mode -eq 'prod') {
  Write-Host 'Building the production web app...'
  Push-Location $root
  & npm.cmd run build
  $buildCode = $LASTEXITCODE
  Pop-Location
  if ($buildCode -ne 0) { Stop-WithMessage 'The production web build failed.' }
}

$serviceScript = Join-Path $PSScriptRoot 'run-service.ps1'
foreach ($service in @('api', 'worker', 'web')) {
  $serviceLog = Join-Path $logs "$service.log"
  if (Test-Path $serviceLog) { Clear-Content -LiteralPath $serviceLog }
  $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', "`"$serviceScript`"", '-Service', $service, '-Mode', $Mode)
  $process = Start-Process -FilePath 'powershell.exe' -ArgumentList $arguments -WorkingDirectory $root -PassThru
  Set-Content -LiteralPath (Join-Path $logs "$service.pid") -Value $process.Id
}
Set-Content -LiteralPath (Join-Path $logs '.mode') -Value "$Mode $lockHash $requirementsHash" -NoNewline

function Wait-Http([string]$Uri, [int]$Seconds) {
  $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
  while ([DateTime]::UtcNow -lt $deadline) {
    try { $result = Invoke-WebRequest -Uri $Uri -TimeoutSec 3 -UseBasicParsing; if ($result.StatusCode -ge 200 -and $result.StatusCode -lt 500) { return $true } } catch { }
    Start-Sleep -Seconds 2
  }
  return $false
}
if (-not (Wait-Http 'http://127.0.0.1:8000/health' 90)) {
  Get-Content (Join-Path $logs 'api.log') -Tail 60 -ErrorAction SilentlyContinue
  Stop-WithMessage 'The API did not become healthy within 90 seconds. Review logs/api.log.'
}
if (-not (Wait-Http 'http://127.0.0.1:3000/' 90)) {
  Get-Content (Join-Path $logs 'web.log') -Tail 60 -ErrorAction SilentlyContinue
  Stop-WithMessage 'The web app did not become healthy within 90 seconds. Review logs/web.log.'
}
foreach ($service in @('api', 'worker', 'web')) {
  $pidPath = Join-Path $logs "$service.pid"
  $serviceProcessId = [int](Get-Content -Raw $pidPath)
  if (-not (Get-Process -Id $serviceProcessId -ErrorAction SilentlyContinue)) {
    Get-Content (Join-Path $logs "$service.log") -Tail 60 -ErrorAction SilentlyContinue
    Stop-WithMessage "The $service service exited during startup. See logs/$service.log."
  }
  if (Select-String -LiteralPath (Join-Path $logs "$service.log") -Pattern 'exited with code' -Quiet -ErrorAction SilentlyContinue) {
    Get-Content (Join-Path $logs "$service.log") -Tail 60 -ErrorAction SilentlyContinue
    Stop-WithMessage "The $service process exited during startup. See logs/$service.log."
  }
}
Write-Host ''
Write-Host 'BrandLens is ready.' -ForegroundColor Green
Write-Host 'Website:     http://localhost:3000/'
Write-Host 'Login:       http://localhost:3000/login'
Write-Host 'API health:  http://localhost:8000/health'
Write-Host 'API docs:    http://localhost:8000/docs'
Write-Host "Logs:        $logs"
Write-Host 'Stop services with stop.bat. Use stop.bat containers to also stop Docker data services.'
Start-Process 'http://localhost:3000/'
