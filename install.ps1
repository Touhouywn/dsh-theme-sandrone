# Sandrone · 人偶工坊 — install the theme, its sidebar entry, and the persona.
#
#   pwsh -File .\install.ps1
#   pwsh -File .\install.ps1 -Profile other
#   pwsh -File .\install.ps1 -DshHome D:\dsh-data
#
# Installs every package through its own, individually idempotent script.

[CmdletBinding()]
param(
  [string]$Profile = 'desktop',
  [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' })
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

Write-Host '== Sandrone theme ==' -ForegroundColor Cyan
& (Join-Path $root 'dsh-theme-sandrone\install.ps1') -Profile $Profile -DshHome $DshHome

Write-Host ''
Write-Host '== Sandrone persona (conversation voice) ==' -ForegroundColor Cyan
& (Join-Path $root 'dsh-plugin-sandrone-persona\install.ps1') -Profile $Profile -DshHome $DshHome

Write-Host ''
Write-Host '== Sandrone Workshop (sidebar entry) ==' -ForegroundColor Cyan
& (Join-Path $root 'dsh-plugin-sandrone\install.ps1') -Profile $Profile -DshHome $DshHome

Write-Host ''
Write-Host 'Done. Fully quit and reopen DSH once so the Client declarations reload.' -ForegroundColor Cyan
Write-Host 'If the sidebar does not show 桑多涅工坊 after the restart, check:' -ForegroundColor Cyan
Write-Host '  <DshHome>\profiles\<Profile>\cordis.patch.yml' -ForegroundColor Cyan
