# Sandrone · 人偶工坊 — install the DSH theme into a profile.
#
#   pwsh -File .\install.ps1                 # install into the desktop profile
#   pwsh -File .\install.ps1 -Profile other  # another profile
#   pwsh -File .\install.ps1 -Purge          # reinstall from scratch
#
# Steps: copy the package to %DSH_HOME%\themes\sandrone, link it into the
# profile's node_modules, and append one insert row to cordis.patch.yml.
# The profile's configuration layer is watched by HMR, so the theme mounts
# without restarting DSH.

[CmdletBinding()]
param(
  [string]$Profile = 'desktop',
  [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }),
  [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
$dest = Join-Path $DshHome 'themes\sandrone'
$profileDir = Join-Path $DshHome "profiles\$Profile"
$link = Join-Path $profileDir 'node_modules\dsh-theme-sandrone'
$patch = Join-Path $profileDir 'cordis.patch.yml'

if (-not (Test-Path -LiteralPath $profileDir)) {
  throw "DSH profile not found: $profileDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $source 'lib\index.js'))) {
  throw "Run this script from the dsh-theme-sandrone directory (lib\index.js not found next to it)."
}

# 1. Copy the package to its durable home.
if ($Purge -and (Test-Path -LiteralPath $dest)) {
  Remove-Item -LiteralPath $dest -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($item in @('package.json', 'lib', 'theme', 'assets', 'cordis.patch.yml', 'locale', 'README.md', 'NOTICE.md', 'LICENSE', 'ASSET-LICENSE.md', 'PROVENANCE.json')) {
  $from = Join-Path $source $item
  if (-not (Test-Path -LiteralPath $from)) { throw "Package is incomplete, missing: $from" }
  $to = Join-Path $dest $item
  if (Test-Path -LiteralPath $to) { Remove-Item -LiteralPath $to -Recurse -Force }
  Copy-Item -LiteralPath $from -Destination $to -Recurse -Force
}
Write-Host "package  -> $dest" -ForegroundColor Green

# 2. Link it into the profile so the loader can import it by bare name.
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $link) | Out-Null
if (Test-Path -LiteralPath $link) {
  $existing = Get-Item -LiteralPath $link -Force
  if ($existing.LinkType) { $existing.Delete() } else { Remove-Item -LiteralPath $link -Recurse -Force }
}
New-Item -ItemType Junction -Path $link -Target $dest | Out-Null
Write-Host "junction -> $link" -ForegroundColor Green

# 2b. DSH parses the profile manifest and the patch with strict readers: a
#     UTF-8 BOM is a fatal startup error ("Unexpected token '﻿'"). Strip one
#     if an editor or another installer left it behind.
function Repair-Utf8Bom([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return }
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -lt 3 -or $bytes[0] -ne 0xEF -or $bytes[1] -ne 0xBB -or $bytes[2] -ne 0xBF) { return }
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  Copy-Item -LiteralPath $Path -Destination "$Path.bom-bak-$stamp" -Force
  $text = [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
  [System.IO.File]::WriteAllText($Path, $text, (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "bom      -> stripped from $Path (backup: $Path.bom-bak-$stamp)" -ForegroundColor Yellow
}
Repair-Utf8Bom (Join-Path $profileDir 'package.json')
Repair-Utf8Bom $patch

# 3. Add the loader row once.
if (-not (Test-Path -LiteralPath $patch)) {
  [System.IO.File]::WriteAllText(
    $patch,
    "# Your patch layer for this dsh profile, applied after every bundle layer:`n",
    (New-Object System.Text.UTF8Encoding($false))
  )
}
$raw = [System.IO.File]::ReadAllText($patch)
if ($raw -match 'dsh-theme-sandrone') {
  Write-Host "patch    -> already present in cordis.patch.yml (left untouched)" -ForegroundColor Yellow
}
else {
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  Copy-Item -LiteralPath $patch -Destination "$patch.bak-theme-$stamp" -Force
  $nl = if ($raw -match "`r`n") { "`r`n" } else { "`n" }
  $block = @(
    '# ---- theme-sandrone: 桑多涅 · 人偶工坊（DSH 主题；临时关闭：给条目加 disabled: true）----'
    '- insert:'
    '    - id: theme-sandrone'
    '      name: dsh-theme-sandrone'
  ) -join $nl
  $prefix = if ($raw.Length -eq 0 -or $raw.EndsWith($nl)) { '' } else { $nl }
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::AppendAllText($patch, $prefix + $block + $nl, $utf8)
  Write-Host "patch    -> appended theme-sandrone row to cordis.patch.yml" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Done. The configuration layer is hot-reloaded; if the Web GUI does not' -ForegroundColor Cyan
Write-Host 'repaint on its own, reload the Web GUI (or fully restart DSH).' -ForegroundColor Cyan
