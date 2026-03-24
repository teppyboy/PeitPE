<#
.SYNOPSIS
    Returns the download URL for the latest GitHub release asset matching a pattern.
.OUTPUTS
    [string] The asset download URL, or $null if not found.
#>
param(
    [Parameter(Mandatory)][string]$Owner,
    [Parameter(Mandatory)][string]$Repo,
    [Parameter(Mandatory)][string]$AssetPattern
)

$ErrorActionPreference = 'Stop'

$apiUrl = "https://api.github.com/repos/$Owner/$Repo/releases/latest"

try {
    $headers = @{ 'User-Agent' = 'HirensBootCD-Modifier/1.0' }
    $release = Invoke-RestMethod -Uri $apiUrl -Headers $headers -TimeoutSec 30
} catch {
    Write-Warning "Failed to query GitHub API for $Owner/$Repo : $_"
    return $null
}

$asset = $release.assets | Where-Object { $_.name -match $AssetPattern } | Select-Object -First 1

if (-not $asset) {
    Write-Warning "No asset matching '$AssetPattern' found in latest release of $Owner/$Repo"
    Write-Host "    Available assets:" -ForegroundColor DarkGray
    $release.assets | ForEach-Object { Write-Host "      - $($_.name)" -ForegroundColor DarkGray }
    return $null
}

Write-Host "    Found: $($asset.name) ($('{0:N1}' -f ($asset.size / 1MB)) MB)" -ForegroundColor DarkGray
return $asset.browser_download_url
