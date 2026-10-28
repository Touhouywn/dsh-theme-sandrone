# Sandrone · 机偶 — remove this bundle from a DSH profile.
#
#   pwsh -File .\uninstall.ps1                 # remove from the desktop profile
#   pwsh -File .\uninstall.ps1 -Profile other
#   pwsh -File .\uninstall.ps1 -Purge          # also delete the copied bundle + voice cache
#
# Removes the loader row and the node_modules junction. Nothing else is touched.

[CmdletBinding()]
param(
  [string]$Profile = 'desktop',
  [string]$DshHome = $(if ($env:DSH_HOME) { $env:DSH_HOME } else { Join-Path $env:USERPROFILE '.dsh' }),
  [switch]$Purge
)

$ErrorActionPreference = 'Stop'
$dest = Join-Path $DshHome 'plugins\sandrone-fairy'
$profileDir = Join-Path $DshHome "profiles\$Profile"
$link = Join-Path $profileDir 'node_modules\sandrone-fairy'
$patch = Join-Path $profileDir 'cordis.patch.yml'

if (-not (Test-Path -LiteralPath $profileDir)) {
  throw "DSH profile not found: $profileDir"
}

# 1. Drop the junction.
if (Test-Path -LiteralPath $link) {
  $existing = Get-Item -LiteralPath $link -Force
  if ($existing.LinkType) { $existing.Delete() } else { Remove-Item -LiteralPath $link -Recurse -Force }
  Write-Host "junction -> removed" -ForegroundColor Green
}

# 2. Drop the loader row (the whole 3-line insert block).
if (Test-Path -LiteralPath $patch) {
  $lines = [System.IO.File]::ReadAllLines($patch, [System.Text.Encoding]::UTF8)
  $out = New-Object System.Collections.Generic.List[string]
  $skipped = 0
  for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^\s+-\s+id:\s*sandrone-fairy\s*$') {
      # strip the "- insert:" header above, and the "name:" line below
      if ($out.Count -gt 0 -and $out[$out.Count - 1] -match '^-\s+insert:\s*$') { $out.RemoveAt($out.Count - 1) }
      if ($i + 1 -lt $lines.Count -and $lines[$i + 1] -match '^\s+name:\s*.?sandrone-fairy.?') { $i++ }
      $skipped++
      continue
    }
    $out.Add($lines[$i])
  }
  if ($skipped -gt 0) {
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    Copy-Item -LiteralPath $patch -Destination "$patch.bak-$stamp" -Force
    [System.IO.File]::WriteAllText($patch, (($out -join "`n") + "`n"), (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "patch    -> row removed (backup: $patch.bak-$stamp)" -ForegroundColor Green
  }
  else {
    Write-Host 'patch    -> row not present, left unchanged' -ForegroundColor DarkGray
  }
}

# 3. Optionally delete the copied bundle (keeps voice cache unless -Purge twice).
if ($Purge -and (Test-Path -LiteralPath $dest)) {
  Remove-Item -LiteralPath $dest -Recurse -Force
  Write-Host "bundle   -> deleted $dest" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Done. Refresh the DSH page.' -ForegroundColor Cyan
