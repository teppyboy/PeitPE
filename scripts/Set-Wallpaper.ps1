<#
.SYNOPSIS
    Replaces the WinPE wallpaper (winpe.jpg) inside the mounted WIM with a custom image.
    Handles the file ownership/permission requirements of protected system files.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

if ($Config.SkipWallpaper) {
    Write-Host "[*] Skipping wallpaper update (asset not found)." -ForegroundColor Yellow
    return
}

$mountDir       = $Config.MountDir
$wallpaperSrc   = $Config.ResolvedWallpaperPath
$wallpaperDest  = Join-Path $mountDir "Windows\System32\winpe.jpg"

if (-not (Test-Path $wallpaperSrc)) {
    Write-Warning "Wallpaper source not found: $wallpaperSrc. Skipping."
    return
}

Write-Host "[*] Replacing wallpaper..." -ForegroundColor Cyan
Write-Host "    Source : $wallpaperSrc"
Write-Host "    Target : $wallpaperDest"

# Take ownership of the protected system file
Write-Host "    Taking ownership of winpe.jpg..." -ForegroundColor DarkGray
$takeown = & takeown /F "$wallpaperDest" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "takeown failed: $takeown"
}

# Grant Administrators full control
$icacls = & icacls "$wallpaperDest" /grant "Administrators:F" 2>&1
if ($LASTEXITCODE -ne 0) {
    throw "icacls failed: $icacls"
}

# Validate it's a JPEG (basic check)
$srcExt = [IO.Path]::GetExtension($wallpaperSrc).ToLower()
if ($srcExt -notin '.jpg', '.jpeg') {
    Write-Warning "Wallpaper source is not a JPEG ($srcExt). WinPE expects a JPEG at winpe.jpg."
}

Copy-Item $wallpaperSrc $wallpaperDest -Force
Write-Host "[OK] Wallpaper replaced." -ForegroundColor Green
