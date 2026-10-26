$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$resolvedRoot = [IO.Path]::GetFullPath($root).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
Write-Host 'This permanently removes BrandLens local Docker volumes, uploaded development files and build/log output.' -ForegroundColor Yellow
$confirmation = Read-Host 'Type RESET BRANDLENS DEV DATA to continue'
if ($confirmation -cne 'RESET BRANDLENS DEV DATA') { Write-Host 'Reset cancelled.'; exit 1 }
$docker = Get-Command docker.exe -ErrorAction SilentlyContinue
if (-not $docker -and $env:LOCALAPPDATA) {
  $perUserDocker = Join-Path $env:LOCALAPPDATA 'Programs/DockerDesktop/resources/bin'
  if (Test-Path (Join-Path $perUserDocker 'docker.exe')) {
    $env:PATH = "$perUserDocker;$env:PATH"
    $docker = Get-Command docker.exe -ErrorAction SilentlyContinue
  }
}
if (-not $docker) { throw 'Docker Desktop with Docker Compose is required to reset local development data.' }
& (Join-Path $PSScriptRoot 'stop-brandlens.ps1')
Push-Location $root
& docker.exe compose down --volumes
if ($LASTEXITCODE -ne 0) { Pop-Location; throw 'Docker volume reset failed; no local files were removed.' }
Pop-Location
foreach ($relative in @('api/private-uploads', 'logs', '.next-brandlens-build', '.next-brandlens-dev', '.brandlens-npm-lock-hash')) {
  $target = [IO.Path]::GetFullPath((Join-Path $root $relative))
  if (-not $target.StartsWith($resolvedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw "Refusing to remove a path outside the repository: $target" }
  if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Recurse -Force }
}
Write-Host 'Development data reset complete. .env files and installed dependencies were preserved.'
