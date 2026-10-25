# Sandrone Workshop — install the left-sidebar hub into a DSH profile.
#
#   pwsh -File .\install.ps1
#   pwsh -File .\install.ps1 -Profile other
#
# Copies this package to %DSH_HOME%\plugins\sandrone-hub, links it into the
# profile's node_modules, and appends one insert row to cordis.patch.yml.
# The profile's configuration layer is watched by HMR.

[CmdletBinding()]
param(
  [string]$Profile = 'desktop',
  [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }),
  [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
$profileDir = Join-Path $DshHome "profiles\$Profile"
$dest = Join-Path $DshHome 'plugins\sandrone-hub'
$link = Join-Path $profileDir 'node_modules\dsh-plugin-sandrone'
$patch = Join-Path $profileDir 'cordis.patch.yml'

if (-not (Test-Path -LiteralPath $profileDir)) {
  throw "DSH profile not found: $profileDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $source 'client.js'))) {
  throw "Run this script from the dsh-plugin-sandrone directory (client.js not found)."
}

# DSH parses the profile manifest and patch strictly: a UTF-8 BOM is a fatal
# startup error. Strip one if an editor or another installer left it behind.
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

# 1. Copy the package to a durable home, then link it into the profile so the
#    loader can import it by name. The extracted distribution folder may be
#    deleted afterwards.
if ($Purge -and (Test-Path -LiteralPath $dest)) {
  Remove-Item -LiteralPath $dest -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null
foreach ($item in @('package.json', 'index.js', 'client.js', 'cordis.patch.yml', 'locale', 'icon.svg', 'README.md')) {
  $from = Join-Path $source $item
  if (-not (Test-Path -LiteralPath $from)) { throw "Package is incomplete, missing: $from" }
  $to = Join-Path $dest $item
  if (Test-Path -LiteralPath $to) { Remove-Item -LiteralPath $to -Recurse -Force }
  Copy-Item -LiteralPath $from -Destination $to -Recurse -Force
}
Write-Host "package  -> $dest" -ForegroundColor Green

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $link) | Out-Null
if (Test-Path -LiteralPath $link) {
  $existing = Get-Item -LiteralPath $link -Force
  if ($existing.LinkType) { $existing.Delete() } else { Remove-Item -LiteralPath $link -Recurse -Force }
}
New-Item -ItemType Junction -Path $link -Target $dest | Out-Null
Write-Host "junction -> $link" -ForegroundColor Green

# 2. Add the loader row once, with a backup before the first write.
if (-not (Test-Path -LiteralPath $patch)) {
  [System.IO.File]::WriteAllText(
    $patch,
    "# Your patch layer for this dsh profile, applied after every bundle layer:`n",
    (New-Object System.Text.UTF8Encoding($false))
  )
}
$raw = [System.IO.File]::ReadAllText($patch)
if ($raw -match 'sandrone-hub') {
  Write-Host "patch    -> already present in cordis.patch.yml (left untouched)" -ForegroundColor Yellow
}
else {
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  Copy-Item -LiteralPath $patch -Destination "$patch.bak-sandrone-hub-$stamp" -Force
  $nl = if ($raw -match "`r`n") { "`r`n" } else { "`n" }
  $block = @(
    '# ---- sandrone-hub: 桑多涅主题的左侧栏入口（禁用：给条目加 disabled: true）----'
    '- insert:'
    '    - id: sandrone-hub'
    '      name: dsh-plugin-sandrone'
  ) -join $nl
  $prefix = if ($raw.Length -eq 0 -or $raw.EndsWith($nl)) { '' } else { $nl }
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::AppendAllText($patch, $prefix + $block + $nl, $utf8)
  Write-Host "patch    -> appended sandrone-hub row to cordis.patch.yml" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Done. The configuration layer is hot-reloaded; if the sidebar does not' -ForegroundColor Cyan
Write-Host 'show 桑多涅工坊, fully quit and reopen DSH once.' -ForegroundColor Cyan
