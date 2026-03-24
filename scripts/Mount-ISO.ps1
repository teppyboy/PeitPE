<#
.SYNOPSIS
    Extracts the Hiren's BootCD PE ISO to the working directory using 7-Zip.
    This preserves the full ISO structure needed to rebuild it later.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

$extractDir = $Config.ISOExtractDir
$sevenZip   = $Config.SevenZipPath
$sourceISO  = $Config.SourceISO

# If extract dir already has files, ask before re-extracting
if ((Get-ChildItem $extractDir -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0) {
    Write-Warning "Extract directory '$extractDir' is not empty."
    $answer = Read-Host "Re-extract ISO? This will DELETE the existing contents. [y/N]"
    if ($answer -notmatch '^[Yy]$') {
        Write-Host "[*] Skipping ISO extraction - using existing files." -ForegroundColor Yellow
        return
    }
    Remove-Item $extractDir -Recurse -Force
    New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
}

Write-Host "[*] Extracting ISO: $sourceISO" -ForegroundColor Cyan
Write-Host "    -> $extractDir"

$result = & $sevenZip x "$sourceISO" -o"$extractDir" -y 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "7-Zip extraction failed (exit $LASTEXITCODE):`n$result"
}

# Verify boot.wim exists after extraction
$wimPath = Join-Path $extractDir $Config.WimFile
if (-not (Test-Path $wimPath)) {
    throw "boot.wim not found at expected location '$wimPath' after extraction. Check WimFile in config.json."
}

Write-Host "[OK] ISO extracted successfully. boot.wim at: $wimPath" -ForegroundColor Green
