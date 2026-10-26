$ErrorActionPreference = 'Stop'
$deadline = [DateTime]::UtcNow.AddMinutes(3)
$apiReady = $false
$webReady = $false

while ([DateTime]::UtcNow -lt $deadline) {
  try {
    $api = Invoke-RestMethod -Uri 'http://127.0.0.1:8000/ready' -TimeoutSec 3
    $apiReady = $api.status -eq 'ready'
  } catch {
    $apiReady = $false
  }

  try {
    $web = Invoke-WebRequest -Uri 'http://127.0.0.1:3000/login' -TimeoutSec 3 -UseBasicParsing
    $webReady = $web.StatusCode -eq 200
  } catch {
    $webReady = $false
  }

  if ($apiReady -and $webReady) {
    Write-Host 'API readiness and website sign-in checks passed.'
    exit 0
  }

  Start-Sleep -Seconds 2
}

Write-Error 'Timed out waiting for API readiness and the website sign-in page.'
exit 1
