<#
.SYNOPSIS
    Downloads the latest version of each app in apps/updates.json and injects
    it into the mounted WIM, replacing the existing installation.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

$mountDir   = $Config.MountDir
$cacheDir   = $Config.DownloadCacheDir
$sevenZip   = $Config.SevenZipPath
$appsFile   = Join-Path $PSScriptRoot ".." "apps" "updates.json"

$helpersDir = Join-Path $PSScriptRoot "helpers"
. (Join-Path $helpersDir "Get-LatestGitHubRelease.ps1")
. (Join-Path $helpersDir "Invoke-AppDownload.ps1")

$appsDef = (Get-Content $appsFile -Raw | ConvertFrom-Json).apps
$enabled = $appsDef | Where-Object { $_.enabled -eq $true }

if (-not $enabled) {
    Write-Host "[*] No apps enabled in updates.json. Skipping." -ForegroundColor Yellow
    return
}

Write-Host "[*] Updating $($enabled.Count) app(s) in WIM..." -ForegroundColor Cyan

foreach ($app in $enabled) {
    Write-Host "`n  -> $($app.name): $($app.description)" -ForegroundColor White

    $appHt = @{}
    $app.PSObject.Properties | ForEach-Object { $appHt[$_.Name] = $_.Value }

    # Resolve download URL for GitHub-sourced apps
    if ($app.source -eq 'github') {
        $url = & (Join-Path $helpersDir "Get-LatestGitHubRelease.ps1") `
            -Owner $app.owner -Repo $app.repo -AssetPattern $app.assetPattern
        if (-not $url) {
            Write-Warning "  [SKIP] Could not resolve download URL for $($app.name)"
            continue
        }
        $appHt['downloadUrl'] = $url
    }

    if (-not $appHt['downloadUrl']) {
        Write-Warning "  [SKIP] No downloadUrl for $($app.name). Update apps/updates.json."
        continue
    }

    # Download and stage
    try {
        $stageDir = Invoke-AppDownload -App $appHt -CacheDir $cacheDir -SevenZipPath $sevenZip
    } catch {
        Write-Warning "  [FAIL] $($app.name): $_"
        continue
    }

    # Target path inside the mounted WIM
    $wimTarget = Join-Path $mountDir $app.targetPath.TrimStart('\')

    # Clear the existing app folder and replace with new version
    if (Test-Path $wimTarget) {
        Remove-Item $wimTarget -Recurse -Force
        Write-Host "    Removed old version at: $wimTarget" -ForegroundColor DarkGray
    }
    New-Item -ItemType Directory -Path $wimTarget -Force | Out-Null
    Copy-Item "$stageDir\*" $wimTarget -Recurse -Force

    Write-Host "  [OK] $($app.name) -> $($app.targetPath)" -ForegroundColor Green
}

Write-Host "`n[OK] App updates complete." -ForegroundColor Green
