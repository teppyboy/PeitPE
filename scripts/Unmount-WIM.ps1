<#
.SYNOPSIS
    Unmounts the WIM and commits all changes back to boot.wim.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

$mountDir = $Config.MountDir

Write-Host "[*] Unmounting WIM and committing changes..." -ForegroundColor Cyan
Write-Host "    This may take several minutes."

$result = & dism /Unmount-Image /MountDir:"$mountDir" /commit 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Error "DISM unmount failed (exit $LASTEXITCODE):`n$($result -join "`n")"
    Write-Host ""
    Write-Host "To recover, try one of:" -ForegroundColor Yellow
    Write-Host "  dism /Unmount-Image /MountDir:`"$mountDir`" /discard"
    Write-Host "  dism /Cleanup-Wim"
    throw "Unmount failed"
}

Write-Host "[OK] WIM unmounted and changes committed." -ForegroundColor Green
