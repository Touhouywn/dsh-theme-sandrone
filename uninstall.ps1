# Sandrone · 人偶工坊 — remove the theme, its sidebar entry, and the persona.
#
#   pwsh -File .\uninstall.ps1
#   pwsh -File .\uninstall.ps1 -Purge     # also delete %DSH_HOME%\themes\sandrone
#
# The theme row and junction are removed by the theme's own uninstall script;
# this wrapper then removes the Workshop and persona rows and junctions.

[CmdletBinding()]
param(
  [string]$Profile = 'desktop',
  [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }),
  [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$profileDir = Join-Path $DshHome "profiles\$Profile"
$patch = Join-Path $profileDir 'cordis.patch.yml'
$hubLink = Join-Path $profileDir 'node_modules\dsh-plugin-sandrone'
$personaLink = Join-Path $profileDir 'node_modules\dsh-plugin-sandrone-persona'

Write-Host '== Sandrone theme ==' -ForegroundColor Cyan
& (Join-Path $root 'dsh-theme-sandrone\uninstall.ps1') -Profile $Profile -DshHome $DshHome -Purge:$Purge

Write-Host ''
Write-Host '== Sandrone persona (conversation voice) ==' -ForegroundColor Cyan

# Drop the persona row. The marker is written by dsh-plugin-sandrone-persona\install.ps1.
if (Test-Path -LiteralPath $patch) {
  $raw = [System.IO.File]::ReadAllText($patch)
  $pattern = '(?ms)^# ---- sandrone-persona:.*?^[ \t]+name: dsh-plugin-sandrone-persona[ \t]*\r?\n'
  $next = [regex]::Replace($raw, $pattern, '')
  if ($next -eq $raw) {
    $next = [regex]::Replace($raw, '(?ms)^- insert:\r?\n(?:[ \t]+.*\r?\n)*?[ \t]+- id: sandrone-persona\r?\n(?:[ \t]+.*\r?\n)*?(?=^- |\z)', '')
  }
  if ($next -ne $raw) {
    [System.IO.File]::WriteAllText($patch, $next, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "patch    -> sandrone-persona row removed" -ForegroundColor Green
  }
  else {
    Write-Host "patch    -> no sandrone-persona row found" -ForegroundColor Yellow
  }
}

if (Test-Path -LiteralPath $personaLink) {
  $existing = Get-Item -LiteralPath $personaLink -Force
  if ($existing.LinkType) { $existing.Delete() } else { Remove-Item -LiteralPath $personaLink -Recurse -Force }
  Write-Host "junction -> persona removed" -ForegroundColor Green
}
if ($Purge) {
  $personaDest = Join-Path $DshHome 'plugins\sandrone-persona'
  if (Test-Path -LiteralPath $personaDest) {
    Remove-Item -LiteralPath $personaDest -Recurse -Force
    Write-Host "files    -> $personaDest deleted" -ForegroundColor Green
  }
}

Write-Host ''
Write-Host '== Sandrone Workshop (sidebar entry) ==' -ForegroundColor Cyan

# Drop the Workshop row. The marker is written by dsh-plugin-sandrone\install.ps1.
if (Test-Path -LiteralPath $patch) {
  $raw = [System.IO.File]::ReadAllText($patch)
  $pattern = '(?ms)^# ---- sandrone-hub:.*?^[ \t]+name: dsh-plugin-sandrone[ \t]*\r?\n'
  $next = [regex]::Replace($raw, $pattern, '')
  if ($next -eq $raw) {
    $next = [regex]::Replace($raw, '(?ms)^- insert:\r?\n(?:[ \t]+.*\r?\n)*?[ \t]+- id: sandrone-hub\r?\n(?:[ \t]+.*\r?\n)*?(?=^- |\z)', '')
  }
  if ($next -ne $raw) {
    [System.IO.File]::WriteAllText($patch, $next, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "patch    -> sandrone-hub row removed" -ForegroundColor Green
  }
  else {
    Write-Host "patch    -> no sandrone-hub row found" -ForegroundColor Yellow
  }
}

# Remove the Workshop junction, and optionally its durable package copy.
if (Test-Path -LiteralPath $hubLink) {
  $existing = Get-Item -LiteralPath $hubLink -Force
  if ($existing.LinkType) { $existing.Delete() } else { Remove-Item -LiteralPath $hubLink -Recurse -Force }
  Write-Host "junction -> removed" -ForegroundColor Green
}
if ($Purge) {
  $hubDest = Join-Path $DshHome 'plugins\sandrone-hub'
  if (Test-Path -LiteralPath $hubDest) {
    Remove-Item -LiteralPath $hubDest -Recurse -Force
    Write-Host "files    -> $hubDest deleted" -ForegroundColor Green
  }
}

Write-Host ''
Write-Host 'Reload the Web GUI to return to the stock interface.' -ForegroundColor Cyan
