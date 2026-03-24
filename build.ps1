<#
.SYNOPSIS
    Main build script for modifying Hiren's BootCD PE ISO.
    Run this as Administrator.

.DESCRIPTION
    Pipeline:
      0. Download latest ISO (skipped if already present)
      1. Check prerequisites
      2. Extract source ISO
      3. Mount boot.wim
      4. Update existing apps to latest versions
      5. Inject new apps
      6. Replace wallpaper
      7. Unmount + commit WIM
      8. Rebuild bootable ISO

.PARAMETER SkipDownload
    Skip ISO download (use if you already have the ISO in peit\).

.PARAMETER SkipExtract
    Skip ISO extraction (use if already extracted into peit\iso\).

.PARAMETER SkipApps
    Skip all app updates and additions.

.PARAMETER SkipWallpaper
    Skip wallpaper replacement.

.PARAMETER SkipBuild
    Skip final ISO build (useful for inspection only).

.PARAMETER ForceDownload
    Re-download the ISO even if it already exists.

.PARAMETER ConfigFile
    Path to config.json. Defaults to .\config.json.

.EXAMPLE
    # Full build (downloads ISO if missing, then modifies and repackages)
    .\build.ps1

    # Force fresh ISO download then full build
    .\build.ps1 -ForceDownload

    # Skip download and extraction (WIM already mounted and ready)
    .\build.ps1 -SkipDownload -SkipExtract

    # Rebuild ISO only
    .\build.ps1 -SkipDownload -SkipExtract -SkipApps -SkipWallpaper
#>
[CmdletBinding()]
param(
    [switch]$SkipDownload,
    [switch]$SkipExtract,
    [switch]$SkipApps,
    [switch]$SkipWallpaper,
    [switch]$SkipBuild,
    [switch]$ForceDownload,
    [string]$ConfigFile = "$PSScriptRoot\config.json"
)

$ErrorActionPreference = 'Stop'
$startTime = Get-Date

Write-Host ""
Write-Host "=================================================" -ForegroundColor Magenta
Write-Host "  Hiren's BootCD PE - ISO Modifier" -ForegroundColor Magenta
Write-Host "=================================================" -ForegroundColor Magenta
Write-Host ""

# ── Load config ──────────────────────────────────────────────────────────────
if (-not (Test-Path $ConfigFile)) {
    throw "Config file not found: $ConfigFile"
}
$cfg = Get-Content $ConfigFile -Raw | ConvertFrom-Json
$Config = @{}
$cfg.PSObject.Properties | ForEach-Object { $Config[$_.Name] = $_.Value }

# Resolve all relative paths against the project root (where build.ps1 lives)
$pathKeys = 'SourceISO', 'WorkDir', 'ISOExtractDir', 'MountDir', 'OutputISO',
            'DownloadCacheDir', 'WallpaperSource'
foreach ($key in $pathKeys) {
    if ($Config[$key] -and -not [IO.Path]::IsPathRooted($Config[$key])) {
        $Config[$key] = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot $Config[$key]))
    }
}

if ($SkipWallpaper) { $Config['SkipWallpaper'] = $true }

$scriptsDir = Join-Path $PSScriptRoot "scripts"

# ── Step runner ───────────────────────────────────────────────────────────────
function Invoke-Step {
    param([string]$Name, [scriptblock]$Block)
    Write-Host ""
    Write-Host "--- $Name ---" -ForegroundColor DarkCyan
    try {
        & $Block
    } catch {
        Write-Host ""
        Write-Host "[ERROR] Step '$Name' failed: $_" -ForegroundColor Red
        Write-Host $_.ScriptStackTrace -ForegroundColor DarkRed
        exit 1
    }
}

# ── Step 0: Download ISO ─────────────────────────────────────────────────────
if (-not $SkipDownload) {
    Invoke-Step "Download ISO" {
        $dlArgs = @{ Config = $Config }
        if ($ForceDownload) { $dlArgs['Force'] = $true }
        $resolved = & (Join-Path $scriptsDir "Get-LatestISO.ps1") @dlArgs
        # Script may return a path with a versioned filename; keep Config in sync
        if ($resolved -and (Test-Path $resolved)) {
            $Config['SourceISO'] = $resolved
        }
    }
} else {
    Write-Host "`n[*] Skipping ISO download." -ForegroundColor Yellow
}

# ── Step 1: Prerequisites ────────────────────────────────────────────────────
Invoke-Step "Prerequisites" {
    & (Join-Path $scriptsDir "Initialize.ps1") -Config $Config
}

# ── Step 2: Extract ISO ──────────────────────────────────────────────────────
if (-not $SkipExtract) {
    Invoke-Step "Extract ISO" {
        & (Join-Path $scriptsDir "Mount-ISO.ps1") -Config $Config
    }
} else {
    Write-Host "`n[*] Skipping ISO extraction." -ForegroundColor Yellow
}

# ── Step 3: Mount WIM ────────────────────────────────────────────────────────
Invoke-Step "Mount WIM" {
    & (Join-Path $scriptsDir "Mount-WIM.ps1") -Config $Config
}

# ── Step 4 & 5: Apps ─────────────────────────────────────────────────────────
if (-not $SkipApps) {
    Invoke-Step "Update Apps" {
        & (Join-Path $scriptsDir "Update-Apps.ps1") -Config $Config
    }
    Invoke-Step "Add New Apps" {
        & (Join-Path $scriptsDir "Add-Apps.ps1") -Config $Config
    }
} else {
    Write-Host "`n[*] Skipping app updates and additions." -ForegroundColor Yellow
}

# ── Step 6: Wallpaper ────────────────────────────────────────────────────────
if (-not $SkipWallpaper -and -not $Config.SkipWallpaper) {
    Invoke-Step "Set Wallpaper" {
        & (Join-Path $scriptsDir "Set-Wallpaper.ps1") -Config $Config
    }
} else {
    Write-Host "`n[*] Skipping wallpaper update." -ForegroundColor Yellow
}

# ── Step 7: Unmount WIM ──────────────────────────────────────────────────────
Invoke-Step "Unmount WIM" {
    & (Join-Path $scriptsDir "Unmount-WIM.ps1") -Config $Config
}

# ── Step 8: Build ISO ────────────────────────────────────────────────────────
if (-not $SkipBuild) {
    Invoke-Step "Build ISO" {
        & (Join-Path $scriptsDir "Build-ISO.ps1") -Config $Config
    }
} else {
    Write-Host "`n[*] Skipping ISO build." -ForegroundColor Yellow
}

$elapsed = (Get-Date) - $startTime
Write-Host ""
Write-Host "=================================================" -ForegroundColor Magenta
Write-Host "  Done in $($elapsed.ToString('mm\:ss'))!" -ForegroundColor Green
Write-Host "  Output: $($Config.OutputISO)" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Magenta
Write-Host ""
