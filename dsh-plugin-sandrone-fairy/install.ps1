# Sandrone · 机偶 — install this bundle into a DSH profile.
#
#   pwsh -File .\install.ps1                    # install into the desktop profile
#   pwsh -File .\install.ps1 -Profile other     # another profile
#   pwsh -File .\install.ps1 -WithEngine        # also copy the local GPT-SoVITS engine (~1.3 GB)
#   pwsh -File .\install.ps1 -Purge             # reinstall from scratch
#
# Steps: copy the bundle to %DSH_HOME%\plugins\sandrone-fairy, link it into the
# profile's node_modules, and append one insert row to cordis.patch.yml.
# The profile layer is watched, so the plugin mounts after a page refresh.

[CmdletBinding()]
param(
  [string]$Profile = 'desktop',
  [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }),
  [switch]$WithEngine,
  [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$source = $PSScriptRoot
$dest = Join-Path $DshHome 'plugins\sandrone-fairy'
$profileDir = Join-Path $DshHome "profiles\$Profile"
$link = Join-Path $profileDir 'node_modules\sandrone-fairy'
$patch = Join-Path $profileDir 'cordis.patch.yml'

if (-not (Test-Path -LiteralPath $profileDir)) {
  throw "DSH profile not found: $profileDir"
}
if (-not (Test-Path -LiteralPath (Join-Path $source 'index.js'))) {
  throw "Run this script from the sandrone-fairy directory (index.js not found next to it)."
}

# 1. Copy the bundle to its durable home.
if ($Purge -and (Test-Path -LiteralPath $dest)) {
  Remove-Item -LiteralPath $dest -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$files = @(
  'package.json', 'index.js', 'client.js', 'icon.svg', 'cordis.patch.yml',
  'README.md', 'CHANGELOG.md', 'NOTICE.md', 'LICENSE', 'INTEGRATION.md',
  'install.ps1', 'install.sh', 'uninstall.ps1'
)
foreach ($f in $files) {
  $from = Join-Path $source $f
  if (-not (Test-Path -LiteralPath $from)) { throw "Bundle incomplete, missing: $from" }
  Copy-Item -LiteralPath $from -Destination (Join-Path $dest $f) -Force
}

foreach ($dir in @('locale', 'assets', 'tools', 'ui', 'docs')) {
  $from = Join-Path $source $dir
  if (-not (Test-Path -LiteralPath $from)) { throw "Bundle incomplete, missing: $from" }
  $to = Join-Path $dest $dir
  if (Test-Path -LiteralPath $to) { Remove-Item -LiteralPath $to -Recurse -Force }
  Copy-Item -LiteralPath $from -Destination $to -Recurse -Force
}

# tts: scripts and reference clips only — never the model weights.
$ttsDest = Join-Path $dest 'tts'
New-Item -ItemType Directory -Force -Path (Join-Path $ttsDest 'ref') | Out-Null
Get-ChildItem -LiteralPath (Join-Path $source 'tts') -Include *.py, *.json, *.txt -File | Copy-Item -Destination $ttsDest -Force
Get-ChildItem -LiteralPath (Join-Path $source 'tts\ref') -Filter *.wav -File -ErrorAction SilentlyContinue |
  Copy-Item -Destination (Join-Path $ttsDest 'ref') -Force

if ($WithEngine) {
  $engine = Join-Path $source 'tts\gptsovits'
  if (-not (Test-Path -LiteralPath $engine)) {
    throw "Engine not found: $engine  (run the GPT-SoVITS setup first, or omit -WithEngine)"
  }
  $engineDest = Join-Path $ttsDest 'gptsovits'
  if (Test-Path -LiteralPath $engineDest) { Remove-Item -LiteralPath $engineDest -Recurse -Force }
  Copy-Item -LiteralPath $engine -Destination $engineDest -Recurse -Force
  New-Item -ItemType Directory -Force -Path (Join-Path $dest 'assets\voice\cache') | Out-Null
  Write-Host 'engine   -> tts\gptsovits (python deps still need: torch cu121, modelscope, ffmpeg-python)' -ForegroundColor Yellow
}

Write-Host "bundle   -> $dest" -ForegroundColor Green

# 2. Link it into the profile so the loader can import it by bare name.
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $link) | Out-Null
if (Test-Path -LiteralPath $link) {
  $existing = Get-Item -LiteralPath $link -Force
  if ($existing.LinkType) { $existing.Delete() } else { Remove-Item -LiteralPath $link -Recurse -Force }
}
New-Item -ItemType Junction -Path $link -Target $dest | Out-Null
Write-Host "junction -> $link" -ForegroundColor Green

# 3. DSH parses the profile manifest and the patch with strict readers: a UTF-8
#    BOM is a fatal startup error. Strip one if an editor left it behind.
function Repair-Utf8Bom([string]$Path) {
  if (-not (Test-Path -LiteralPath $Path)) { return }
  $bytes = [System.IO.File]::ReadAllBytes($Path)
  if ($bytes.Length -lt 3 -or $bytes[0] -ne 0xEF -or $bytes[1] -ne 0xBB -or $bytes[2] -ne 0xBF) { return }
  $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
  Copy-Item -LiteralPath $Path -Destination "$Path.bom-bak-$stamp" -Force
  $text = [System.Text.Encoding]::UTF8.GetString($bytes, 3, $bytes.Length - 3)
  [System.IO.File]::WriteAllText($Path, $text, (New-Object System.Text.UTF8Encoding($false)))
  Write-Host "bom      -> stripped from $Path" -ForegroundColor Yellow
}
Repair-Utf8Bom (Join-Path $profileDir 'package.json')
Repair-Utf8Bom $patch

# 4. Add the loader row once.
if (-not (Test-Path -LiteralPath $patch)) {
  [System.IO.File]::WriteAllText(
    $patch,
    "# Your patch layer for this dsh profile, applied after every bundle layer:`n",
    (New-Object System.Text.UTF8Encoding($false))
  )
}
$raw = [System.IO.File]::ReadAllText($patch)
if ($raw -match '(?m)^\s+-\s+id:\s*sandrone-fairy\s*$') {
  Write-Host 'patch    -> row already present, left unchanged' -ForegroundColor DarkGray
}
else {
  if ($raw.Length -gt 0 -and -not $raw.EndsWith("`n")) { $raw += "`n" }
  $row = "- insert:`n    - id: sandrone-fairy`n      name: 'sandrone-fairy'`n"
  [System.IO.File]::WriteAllText($patch, $raw + $row, (New-Object System.Text.UTF8Encoding($false)))
  Write-Host 'patch    -> row appended' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Done. Refresh the DSH page; the splash plays on load.' -ForegroundColor Cyan
Write-Host 'Config: GET/POST /sandrone/config   Self-check: GET /sandrone/voice' -ForegroundColor DarkGray
