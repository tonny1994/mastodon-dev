[CmdletBinding()]
param(
  [Parameter(Mandatory, Position = 0)]
  [ValidateSet('Test', 'Apply', 'Restore')]
  [string] $Action,

  [ValidatePattern('^v?[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.-]+)?$')]
  [string] $Version
)

$ErrorActionPreference = 'Stop'
$workspace = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$compose = 'compose.local.yml'
$overlay = 'deploy/local/frontend/compose.patch.yml'
$dockerfile = 'deploy/local/frontend/Dockerfile'

function Invoke-Docker {
  param([string[]] $DockerArguments)
  & docker @DockerArguments
  if ($LASTEXITCODE -ne 0) { throw "Docker command failed (exit $LASTEXITCODE)." }
}

Push-Location $workspace
try {
  if ($Action -eq 'Restore') {
    Invoke-Docker -DockerArguments @('compose', '-f', $compose, 'up', '-d', '--no-deps', '--wait', '--wait-timeout', '90', 'web')
    Write-Host 'Official Mastodon web image restored. Database and media were not changed.'
    return
  }

  if ($Version -and $Action -ne 'Test') {
    throw '-Version is only for testing a future release. Update compose.local.yml before Apply.'
  }

  $configJson = & docker compose -f $compose config --format json
  if ($LASTEXITCODE -ne 0) { throw 'Could not read the official image from compose.local.yml.' }
  $config = ($configJson -join "`n") | ConvertFrom-Json
  $releaseImage = [string] $config.services.sidekiq.image
  if ([string] $config.services.web.image -ne $releaseImage) {
    throw 'Base Compose web and sidekiq images must use the same official release.'
  }
  if ($Version) { $releaseImage = 'ghcr.io/mastodon/mastodon:v' + $Version.TrimStart('v') }
  if ($releaseImage -notmatch '^ghcr\.io/mastodon/mastodon:v([A-Za-z0-9._-]+)$') {
    throw "Unsupported official image: $releaseImage"
  }

  $patchImage = 'mastodon-local:{0}-live' -f $Matches[1]
  Invoke-Docker -DockerArguments @('build', '--build-arg', "MASTODON_IMAGE=$releaseImage", '-f', $dockerfile, '-t', $patchImage, '.')
  Write-Host "Patch compatibility test passed for $releaseImage."
  if ($Action -eq 'Test') { return }

  $previousPatchImage = [Environment]::GetEnvironmentVariable('MASTODON_PATCH_IMAGE', 'Process')
  try {
    $env:MASTODON_PATCH_IMAGE = $patchImage
    Invoke-Docker -DockerArguments @('compose', '-f', $compose, '-f', $overlay, 'up', '-d', '--no-deps', '--wait', '--wait-timeout', '90', 'web')
  }
  finally {
    if ($null -eq $previousPatchImage) {
      Remove-Item Env:MASTODON_PATCH_IMAGE -ErrorAction SilentlyContinue
    }
    else {
      $env:MASTODON_PATCH_IMAGE = $previousPatchImage
    }
  }
  Write-Host "Patch applied to web: $patchImage. Database and media were not changed."
}
finally {
  Pop-Location
}
