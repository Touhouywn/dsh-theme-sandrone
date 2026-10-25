# Sandrone · 人偶工坊 — remove the DSH theme from a profile.
#
#   pwsh -File .\uninstall.ps1            # remove the row and the junction, keep files
#   pwsh -File .\uninstall.ps1 -Purge     # also delete %DSH_HOME%\themes\sandrone
#
# The page falls back to the stock look on the next reload.

[CmdletBinding()]
param(
  [string]$Profile = 'desktop',
  [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }),
  [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$dest = Join-Path $DshHome 'themes\sandrone'
$profileDir = Join-Path $DshHome "profiles\$Profile"
$link = Join-Path $profileDir 'node_modules\dsh-theme-sandrone'
$patch = Join-Path $profileDir 'cordis.patch.yml'

# 1. Drop the loader row.
if (Test-Path -LiteralPath $patch) {
  $raw = [System.IO.File]::ReadAllText($patch)
  $pattern = '(?ms)^# ---- theme-sandrone:.*?^[ \t]+name: dsh-theme-sandrone[ \t]*\r?\n'
  $next = [regex]::Replace($raw, $pattern, '')
  if ($next -eq $raw) {
    # Marker missing but a row may still exist in another shape.
    $next = [regex]::Replace($raw, '(?ms)^- insert:\r?\n(?:[ \t]+.*\r?\n)*?[ \t]+- id: theme-sandrone\r?\n(?:[ \t]+.*\r?\n)*?(?=^- |\z)', '')
  }
  if ($next -ne $raw) {
    [System.IO.File]::WriteAllText($patch, $next, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "patch    -> theme-sandrone row removed" -ForegroundColor Green
  }
  else {
    Write-Host "patch    -> no theme-sandrone row found (nothing to do)" -ForegroundColor Yellow
  }
}

# 2. Remove the junction.
if (Test-Path -LiteralPath $link) {
  $existing = Get-Item -LiteralPath $link -Force
  if ($existing.LinkType) { $existing.Delete() } else { Remove-Item -LiteralPath $link -Recurse -Force }
  Write-Host "junction -> removed" -ForegroundColor Green
}

# 3. Optionally delete the package copy.
if ($Purge) {
  if (Test-Path -LiteralPath $dest) {
    Remove-Item -LiteralPath $dest -Recurse -Force
    Write-Host "files    -> $dest deleted" -ForegroundColor Green
  }
}
else {
  Write-Host "files    -> kept at $dest (use -Purge to delete)" -ForegroundColor Yellow
}

Write-Host ''
Write-Host 'Reload the Web GUI to return to the stock theme.' -ForegroundColor Cyan
