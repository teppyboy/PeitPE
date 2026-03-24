<#
.SYNOPSIS
    Rebuilds the bootable ISO from the modified extracted ISO directory using oscdimg.
    Supports both BIOS (MBR) and UEFI dual-boot output.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

$oscdimg    = $Config.OscdimgPath
$sourceDir  = $Config.ISOExtractDir
$outputISO  = $Config.OutputISO
$outputDir  = Split-Path $outputISO -Parent

# Ensure output directory exists
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

# Locate boot files for dual-boot support
$etfsboot  = Join-Path $sourceDir "boot\etfsboot.com"
$efisys    = Join-Path $sourceDir "efi\microsoft\boot\efisys.bin"

$hasEtfs = Test-Path $etfsboot
$hasEfi  = Test-Path $efisys

Write-Host "[*] Building ISO..." -ForegroundColor Cyan
Write-Host "    Source : $sourceDir"
Write-Host "    Output : $outputISO"
Write-Host "    BIOS   : $(if ($hasEtfs) { 'Yes' } else { 'No - etfsboot.com not found' })"
Write-Host "    UEFI   : $(if ($hasEfi)  { 'Yes' } else { 'No - efisys.bin not found' })"

# Build oscdimg arguments
if ($hasEtfs -and $hasEfi) {
    # Dual-boot: BIOS + UEFI
    $bootData = "2#p0,e,b`"$etfsboot`"#pEF,e,b`"$efisys`""
    $args = @(
        '-m'
        '-o'
        '-u2'
        '-udfver102'
        "-bootdata:$bootData"
        "`"$sourceDir`""
        "`"$outputISO`""
    )
    Write-Host "    Mode   : Dual-boot (BIOS + UEFI)"
} elseif ($hasEtfs) {
    # BIOS only
    $args = @(
        '-m'
        '-o'
        '-u2'
        "-b`"$etfsboot`""
        "`"$sourceDir`""
        "`"$outputISO`""
    )
    Write-Host "    Mode   : BIOS only"
} elseif ($hasEfi) {
    # UEFI only
    $args = @(
        '-m'
        '-o'
        '-u2'
        '-udfver102'
        '-pEF'
        "-b`"$efisys`""
        "`"$sourceDir`""
        "`"$outputISO`""
    )
    Write-Host "    Mode   : UEFI only"
} else {
    throw "Neither etfsboot.com nor efisys.bin found in the extracted ISO. Cannot create a bootable ISO."
}

$result = & $oscdimg @args 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "oscdimg failed (exit $LASTEXITCODE):`n$($result -join "`n")"
}

$isoSize = (Get-Item $outputISO).Length
Write-Host "[OK] ISO built: $outputISO ($('{0:N0}' -f ($isoSize / 1MB)) MB)" -ForegroundColor Green
