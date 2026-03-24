<#
.SYNOPSIS
    Mounts boot.wim from the extracted ISO using DISM for modification.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

$wimPath  = Join-Path $Config.ISOExtractDir $Config.WimFile
$mountDir = $Config.MountDir
$index    = $Config.WimIndex

# Check if already mounted
$mountStatus = & dism /Get-MountedImageInfo 2>&1
if ($mountStatus -match [regex]::Escape($mountDir)) {
    Write-Warning "WIM appears to already be mounted at '$mountDir'."
    $answer = Read-Host "Unmount (discard) and re-mount? [y/N]"
    if ($answer -notmatch '^[Yy]$') {
        Write-Host "[*] Using existing mounted WIM." -ForegroundColor Yellow
        return
    }
    Write-Host "[*] Discarding existing mount..." -ForegroundColor Yellow
    & dism /Unmount-Image /MountDir:"$mountDir" /discard | Out-Null
}

# Ensure mount dir is empty
if ((Get-ChildItem $mountDir -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
    Remove-Item "$mountDir\*" -Recurse -Force
}

Write-Host "[*] Mounting WIM (index $index)..." -ForegroundColor Cyan
Write-Host "    WIM : $wimPath"
Write-Host "    -> $mountDir"

$result = & dism /Mount-Image /ImageFile:"$wimPath" /index:$index /MountDir:"$mountDir" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "DISM mount failed (exit $LASTEXITCODE):`n$($result -join "`n")"
}

Write-Host "[OK] WIM mounted at: $mountDir" -ForegroundColor Green
