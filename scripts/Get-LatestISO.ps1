<#
.SYNOPSIS
    Downloads the latest Hiren's BootCD PE ISO into the peit working directory.
    Skips download if the file already exists and the SHA-256 matches.

.PARAMETER OutputDir
    Directory to save the ISO into. Defaults to the resolved WorkDir from config.

.PARAMETER Force
    Re-download even if the ISO already exists.

.PARAMETER Config
    Hashtable from build.ps1. If omitted the script loads config.json itself.
#>
param(
    [string]$OutputDir,
    [switch]$Force,
    [hashtable]$Config
)

$ErrorActionPreference = 'Stop'

# Load config if called standalone
if (-not $Config) {
    $cfgFile = Join-Path $PSScriptRoot ".." "config.json"
    $raw     = Get-Content $cfgFile -Raw | ConvertFrom-Json
    $Config  = @{}
    $raw.PSObject.Properties | ForEach-Object { $Config[$_.Name] = $_.Value }
    $pathKeys = 'SourceISO','WorkDir','ISOExtractDir','MountDir','OutputISO','DownloadCacheDir'
    foreach ($key in $pathKeys) {
        if ($Config[$key] -and -not [IO.Path]::IsPathRooted($Config[$key])) {
            $Config[$key] = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".." $Config[$key]))
        }
    }
}

if (-not $OutputDir) { $OutputDir = $Config.WorkDir }
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# Fetch the download page
$downloadPage = "https://www.hirensbootcd.org/download/"
Write-Host "[*] Checking latest Hiren's BootCD PE release..." -ForegroundColor Cyan
Write-Host "    Page: $downloadPage"

try {
    $response = Invoke-WebRequest -Uri $downloadPage -UseBasicParsing -TimeoutSec 30 `
                                  -UserAgent "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
} catch {
    throw "Failed to fetch download page '$downloadPage': $_"
}

# Parse ISO download link - match href ending in .iso
$isoLink = $response.Links |
    Where-Object { $_.href -match '\.iso(\?.*)?$' } |
    Select-Object -First 1

if (-not $isoLink) {
    # Fallback: scan raw HTML for any .iso URL
    $htmlMatch = [regex]::Match($response.Content, 'https?://[^\s"<>]+\.iso\b')
    if ($htmlMatch.Success) {
        $isoUrl = $htmlMatch.Value
    } else {
        throw "Could not find an ISO download link on '$downloadPage'. The page layout may have changed."
    }
} else {
    $isoUrl = $isoLink.href
    # Make absolute if relative
    if ($isoUrl -notmatch '^https?://') {
        $base   = [Uri]$downloadPage
        $isoUrl = [Uri]::new($base, $isoUrl).AbsoluteUri
    }
}

Write-Host "    ISO URL : $isoUrl" -ForegroundColor DarkGray

# Derive local filename and path
$isoFileName = [IO.Path]::GetFileName(($isoUrl -split '\?')[0])
$isoDestPath = Join-Path $OutputDir $isoFileName

# Keep config in sync so the rest of the pipeline uses the right filename
$Config['SourceISO'] = $isoDestPath

# Check for SHA-256 checksum published on the page
$sha256Pattern = '(?i)sha-?256[:\s]+([0-9a-f]{64})'
$expectedHash  = $null
if ($response.Content -match $sha256Pattern) {
    $expectedHash = $Matches[1].ToUpper()
    Write-Host "    Expected SHA-256: $expectedHash" -ForegroundColor DarkGray
}

# Skip download if file already exists and checksum matches
if (-not $Force -and (Test-Path $isoDestPath)) {
    Write-Host "    Found existing: $isoDestPath" -ForegroundColor DarkGray
    if ($expectedHash) {
        Write-Host "    Verifying checksum..." -ForegroundColor DarkGray
        $actual = (Get-FileHash $isoDestPath -Algorithm SHA256).Hash
        if ($actual -eq $expectedHash) {
            Write-Host "[OK] ISO is already up to date (checksum verified)." -ForegroundColor Green
            return $isoDestPath
        }
        Write-Warning "Checksum mismatch - re-downloading. Expected: $expectedHash  Got: $actual"
    } else {
        Write-Host "[OK] ISO already present (no checksum to verify). Use -Force to re-download." -ForegroundColor Green
        return $isoDestPath
    }
}

# Download via BITS (supports resume + progress display)
$partFile = "$isoDestPath.part"
Write-Host "[*] Downloading ISO to: $isoDestPath" -ForegroundColor Cyan

try {
    Import-Module BitsTransfer -ErrorAction Stop
    Start-BitsTransfer -Source $isoUrl -Destination $partFile `
                       -DisplayName "Hiren's BootCD PE ISO" -Description $isoFileName
} catch {
    # BITS unavailable - fall back to WebClient with progress
    Write-Warning "BITS unavailable, falling back to WebClient: $_"
    $wc      = New-Object Net.WebClient
    $lastPct = -1
    $wc.Headers.Add('User-Agent', 'HirensBootCD-Modifier/1.0')
    Register-ObjectEvent $wc DownloadProgressChanged -SourceIdentifier WcProgress -Action {
        $pct = $event.SourceEventArgs.ProgressPercentage
        if ($pct -ne $script:lastPct) {
            $script:lastPct = $pct
            $mb = [math]::Round($event.SourceEventArgs.BytesReceived / 1MB, 1)
            Write-Progress -Activity "Downloading ISO" -Status "$mb MB" -PercentComplete $pct
        }
    } | Out-Null
    $wc.DownloadFile($isoUrl, $partFile)
    Unregister-Event WcProgress -ErrorAction SilentlyContinue
    Write-Progress -Activity "Downloading ISO" -Completed
}

Move-Item $partFile $isoDestPath -Force

# Verify checksum after download
if ($expectedHash) {
    Write-Host "[*] Verifying download..." -ForegroundColor Cyan
    $actual = (Get-FileHash $isoDestPath -Algorithm SHA256).Hash
    if ($actual -ne $expectedHash) {
        Remove-Item $isoDestPath -Force
        throw "SHA-256 mismatch after download. Expected: $expectedHash  Got: $actual. File removed."
    }
    Write-Host "    SHA-256 OK: $actual" -ForegroundColor DarkGray
}

$sizeMB = [math]::Round((Get-Item $isoDestPath).Length / 1MB, 1)
Write-Host "[OK] Downloaded: $isoDestPath ($sizeMB MB)" -ForegroundColor Green
return $isoDestPath
