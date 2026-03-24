<#
.SYNOPSIS
    Downloads and extracts (or copies) an app into a staging folder.
.OUTPUTS
    [string] Path to the prepared app directory ready to inject into the WIM.
#>
param(
    [Parameter(Mandatory)][hashtable]$App,
    [Parameter(Mandatory)][string]$CacheDir,
    [Parameter(Mandatory)][string]$SevenZipPath
)

$ErrorActionPreference = 'Stop'

$appName    = $App.name
$url        = $App.downloadUrl
$type       = $App.type     # 'zip', '7z', 'exe', 'msi'
$subDir     = $App.extractSubDir

# Staging area for this app
$stageDir = Join-Path $CacheDir "staged\$appName"
if (Test-Path $stageDir) {
    Remove-Item $stageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $stageDir -Force | Out-Null

# Determine local cache filename
$ext       = [IO.Path]::GetExtension($url.Split('?')[0])
if (-not $ext) { $ext = ".$type" }
$cacheFile = Join-Path $CacheDir "$appName$ext"

# Download if not cached
if (-not (Test-Path $cacheFile)) {
    Write-Host "    Downloading $appName..." -ForegroundColor DarkCyan
    try {
        $wc = New-Object Net.WebClient
        $wc.Headers.Add('User-Agent', 'HirensBootCD-Modifier/1.0')
        $wc.DownloadFile($url, $cacheFile)
    } catch {
        throw "Download failed for $appName from '$url': $_"
    }
    Write-Host "    Downloaded: $cacheFile" -ForegroundColor DarkGray
} else {
    Write-Host "    Using cached: $cacheFile" -ForegroundColor DarkGray
}

# Extract / place file
switch ($type) {
    { $_ -in 'zip', '7z' } {
        Write-Host "    Extracting $appName..." -ForegroundColor DarkGray
        $extractTemp = Join-Path $CacheDir "extract_$appName"
        if (Test-Path $extractTemp) { Remove-Item $extractTemp -Recurse -Force }
        New-Item -ItemType Directory -Path $extractTemp -Force | Out-Null

        $result = & $SevenZipPath x "$cacheFile" -o"$extractTemp" -y 2>&1
        if ($LASTEXITCODE -ne 0) {
            throw "7-Zip extraction failed for $appName (exit $LASTEXITCODE):`n$result"
        }

        # If subDir is set, look for a matching subdirectory (supports wildcards)
        if ($subDir) {
            $resolved = Get-Item (Join-Path $extractTemp $subDir) -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($resolved) {
                $sourceDir = $resolved.FullName
            } else {
                throw "extractSubDir '$subDir' not found inside extracted archive for $appName"
            }
        } else {
            $sourceDir = $extractTemp
        }

        # Copy contents to staging dir
        Copy-Item "$sourceDir\*" $stageDir -Recurse -Force
        Remove-Item $extractTemp -Recurse -Force
    }
    'exe' {
        # Portable exe - just copy directly
        $destExe = Join-Path $stageDir "$appName.exe"
        Copy-Item $cacheFile $destExe -Force
    }
    default {
        throw "Unsupported app type '$type' for $appName"
    }
}

Write-Host "    Staged at: $stageDir" -ForegroundColor DarkGray
return $stageDir
