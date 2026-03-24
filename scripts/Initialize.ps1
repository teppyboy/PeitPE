<#
.SYNOPSIS
    Validates prerequisites before starting the ISO build process.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

function Test-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]$identity
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Host "[*] Checking prerequisites..." -ForegroundColor Cyan

# Must run as Administrator (required for DISM)
if (-not (Test-Administrator)) {
    throw "This script must be run as Administrator (required for DISM mount operations)."
}
Write-Host "  [OK] Running as Administrator"

# DISM availability
$dismPath = "$env:SystemRoot\System32\dism.exe"
if (-not (Test-Path $dismPath)) {
    throw "DISM not found at '$dismPath'. Ensure Windows ADK or DISM is installed."
}
Write-Host "  [OK] DISM found"

# oscdimg - dynamic discovery
function Find-Oscdimg {
    # 1. Config path
    if ($Config.OscdimgPath -and (Test-Path $Config.OscdimgPath)) {
        return $Config.OscdimgPath
    }
    # 2. Registry: Windows Kits installed root (works regardless of drive)
    $regPaths = @(
        'HKLM:\SOFTWARE\Microsoft\Windows Kits\Installed Roots',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows Kits\Installed Roots'
    )
    foreach ($reg in $regPaths) {
        if (Test-Path $reg) {
            $kitsRoot = (Get-ItemProperty $reg -ErrorAction SilentlyContinue).KitsRoot10
            if ($kitsRoot) {
                $candidate = Join-Path $kitsRoot 'Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe'
                if (Test-Path $candidate) { return $candidate }
            }
        }
    }
    # 3. Search all fixed drives under common ADK relative path
    $drives = (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -match '^[A-Z]:\\$' }).Root
    foreach ($drive in $drives) {
        foreach ($base in @('Program Files (x86)', 'Program Files')) {
            $candidate = Join-Path $drive "$base\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
            if (Test-Path $candidate) { return $candidate }
        }
    }
    # 4. PATH / where.exe
    $inPath = Get-Command oscdimg.exe -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }
    return $null
}

$resolvedOscdimg = Find-Oscdimg
if (-not $resolvedOscdimg) {
    throw "oscdimg.exe not found. Install Windows ADK (Deployment Tools feature) from https://learn.microsoft.com/windows-hardware/get-started/adk-install"
}
$Config['OscdimgPath'] = $resolvedOscdimg
Write-Host "  [OK] oscdimg found: $resolvedOscdimg"

# 7-Zip - dynamic discovery
function Find-SevenZip {
    if ($Config.SevenZipPath -and (Test-Path $Config.SevenZipPath)) {
        return $Config.SevenZipPath
    }
    $drives = (Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Root -match '^[A-Z]:\\$' }).Root
    foreach ($drive in $drives) {
        foreach ($base in @('Program Files', 'Program Files (x86)')) {
            $candidate = Join-Path $drive "$base\7-Zip\7z.exe"
            if (Test-Path $candidate) { return $candidate }
        }
    }
    $inPath = Get-Command 7z.exe -ErrorAction SilentlyContinue
    if ($inPath) { return $inPath.Source }
    return $null
}

$resolvedSevenZip = Find-SevenZip
if (-not $resolvedSevenZip) {
    throw "7-Zip (7z.exe) not found. Install 7-Zip from https://www.7-zip.org/"
}
$Config['SevenZipPath'] = $resolvedSevenZip
Write-Host "  [OK] 7-Zip found: $resolvedSevenZip"

# Source ISO exists
if (-not (Test-Path $Config.SourceISO)) {
    throw "Source ISO not found: '$($Config.SourceISO)'. Update SourceISO in config.json."
}
Write-Host "  [OK] Source ISO found: $($Config.SourceISO)"

# Wallpaper asset exists (if configured)
if ($Config.WallpaperSource -and $Config.WallpaperSource -ne '') {
    $wallpaperPath = Join-Path $PSScriptRoot ".." $Config.WallpaperSource
    $wallpaperPath = [IO.Path]::GetFullPath($wallpaperPath)
    if (-not (Test-Path $wallpaperPath)) {
        Write-Warning "  [WARN] Wallpaper not found at '$wallpaperPath'. Wallpaper update will be skipped."
        $Config['SkipWallpaper'] = $true
    } else {
        Write-Host "  [OK] Wallpaper found: $wallpaperPath"
        $Config['ResolvedWallpaperPath'] = $wallpaperPath
    }
}

# Create working directories
foreach ($dir in @($Config.WorkDir, $Config.ISOExtractDir, $Config.MountDir, $Config.DownloadCacheDir)) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  [+] Created directory: $dir"
    }
}

Write-Host "[OK] All prerequisites satisfied." -ForegroundColor Green
