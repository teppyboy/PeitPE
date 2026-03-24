<#
.SYNOPSIS
    Downloads and injects new apps (defined in apps/additions.json) into the mounted WIM.
#>
param(
    [Parameter(Mandatory)][hashtable]$Config
)

$ErrorActionPreference = 'Stop'

$mountDir   = $Config.MountDir
$cacheDir   = $Config.DownloadCacheDir
$sevenZip   = $Config.SevenZipPath
$appsFile   = Join-Path $PSScriptRoot ".." "apps" "additions.json"

$helpersDir = Join-Path $PSScriptRoot "helpers"
. (Join-Path $helpersDir "Get-LatestGitHubRelease.ps1")
. (Join-Path $helpersDir "Invoke-AppDownload.ps1")

$appsDef = (Get-Content $appsFile -Raw | ConvertFrom-Json).apps
$enabled = $appsDef | Where-Object { $_.enabled -eq $true }

if (-not $enabled) {
    Write-Host "[*] No apps enabled in additions.json. Skipping." -ForegroundColor Yellow
    return
}

Write-Host "[*] Adding $($enabled.Count) new app(s) to WIM..." -ForegroundColor Cyan

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
        Write-Warning "  [SKIP] No downloadUrl for $($app.name). Update apps/additions.json."
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

    if (Test-Path $wimTarget) {
        Write-Warning "    '$($app.targetPath)' already exists in WIM. Overwriting."
        Remove-Item $wimTarget -Recurse -Force
    }
    New-Item -ItemType Directory -Path $wimTarget -Force | Out-Null
    Copy-Item "$stageDir\*" $wimTarget -Recurse -Force

    Write-Host "  [OK] $($app.name) -> $($app.targetPath)" -ForegroundColor Green
}

Write-Host "`n[OK] App additions complete." -ForegroundColor Green
