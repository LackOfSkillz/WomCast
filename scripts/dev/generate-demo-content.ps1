#requires -Version 7.0
<#!
.SYNOPSIS
    Generates placeholder demo media files and a safe demo playlist for WomCast.

.DESCRIPTION
    Creates a balanced set of stub media files (default: 1,000 entries) across
    the demo library folders and refreshes the curated sample M3U playlist used
    by CI smoke tests and demo environments.

    Existing files that match the generated naming pattern (demo-*) are
    overwritten to keep the dataset idempotent. The script intentionally keeps
    file contents lightweight while embedding enough identifying text to make
    debugging easier.

.PARAMETER TotalStubEntries
    Total number of placeholder media files to generate. The files are spread
    evenly across the configured media categories.

.PARAMETER LibraryRoot
    Path to the demo media library root. Defaults to the repo's test-media
    folder.

.PARAMETER PlaylistOutput
    Output path for the sample M3U playlist. Defaults to build/demo/sample.m3u
    within the repository.

.PARAMETER Clean
    When supplied, removes any existing "demo-*" files from the target
    directories before generating the new dataset.

.EXAMPLE
    ./generate-demo-content.ps1

    Generates 1,000 placeholder media files under test-media/ and refreshes the
    demo playlist at build/demo/sample.m3u.

.EXAMPLE
    ./generate-demo-content.ps1 -TotalStubEntries 1500 -Clean

    Regenerates a larger 1,500 item dataset after purging previously created
    demo placeholders.
#>

[CmdletBinding()]
param(
    [Parameter()]
    [ValidateRange(1, 5000)]
    [int]
    $TotalStubEntries = 1000,

    [Parameter()]
    [string]
    $LibraryRoot,

    [Parameter()]
    [string]
    $PlaylistOutput,

    [switch]
    $Clean
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

# Resolve default paths relative to the repository root.
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if (-not $LibraryRoot) {
    $LibraryRoot = Join-Path $repoRoot 'test-media'
}
if (-not $PlaylistOutput) {
    $PlaylistOutput = Join-Path $repoRoot 'build/demo/sample.m3u'
}

$libraryRootPath = Resolve-Path -Path $LibraryRoot -ErrorAction SilentlyContinue
if (-not $libraryRootPath) {
    New-Item -ItemType Directory -Path $LibraryRoot -Force | Out-Null
    $libraryRootPath = Resolve-Path -Path $LibraryRoot
}

$playlistDirectory = Split-Path -Parent $PlaylistOutput
if (-not (Test-Path -LiteralPath $playlistDirectory)) {
    New-Item -ItemType Directory -Path $playlistDirectory -Force | Out-Null
}

$categoryConfigs = @(
    [pscustomobject]@{
        Name                = 'Movies'
        Directory           = 'movies'
        Extension           = '.mp4'
        Template            = 'demo-movie-{0:D4}'
        DescriptionTemplate = 'WomCast Demo Movie #{0}'
    }
    [pscustomobject]@{
        Name                = 'Television'
        Directory           = 'tv'
        Extension           = '.mkv'
        Template            = 'demo-episode-{0:D4}'
        DescriptionTemplate = 'WomCast Demo Episode #{0}'
    }
    [pscustomobject]@{
        Name                = 'Music'
        Directory           = 'music'
        Extension           = '.mp3'
        Template            = 'demo-track-{0:D4}'
        DescriptionTemplate = 'WomCast Demo Track #{0}'
    }
    [pscustomobject]@{
        Name                = 'Photos'
        Directory           = 'photos'
        Extension           = '.jpg'
        Template            = 'demo-photo-{0:D4}'
        DescriptionTemplate = 'WomCast Demo Photo #{0}'
    }
    [pscustomobject]@{
        Name                = 'Games'
        Directory           = 'games'
        Extension           = '.zip'
        Template            = 'demo-rom-{0:D4}'
        DescriptionTemplate = 'WomCast Demo ROM #{0}'
    }
)

function Remove-ExistingDemoFiles {
    param(
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    Get-ChildItem -LiteralPath $Path -File -Filter 'demo-*' -ErrorAction SilentlyContinue |
        Remove-Item -Force
}

function Write-PlaceholderFile {
    param(
        [string]$Path,
        [string]$Category,
        [string]$Description
    )

    $content = @(
        'WomCast Demo Placeholder',
        "Category: $Category",
        "Description: $Description",
        "Generated: $(Get-Date -Format 'u')",
        'Note: Replace with real media for production deployments.'
    )

    $encoding = if ($Path.EndsWith('.zip')) { 'Byte' } else { 'UTF8' }

    if ($encoding -eq 'Byte') {
        # Write a minimal ZIP header to prevent unzip errors when inspected.
        $bytes = [byte[]](0x50,0x4B,0x03,0x04,0x14,0x00,0x00,0x00,0x00,0x00,0xB7,0xAC,0xCE,0x34,0x00,0x00,
                          0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00)
        Set-Content -Path $Path -Value $bytes -Encoding Byte
    } else {
        Set-Content -Path $Path -Value $content -Encoding UTF8
    }
}

function New-PlaylistLines {
    param()

    $channels = @(
        [pscustomobject]@{
            Id       = 'nasa-tv-public'
            Name     = 'NASA TV (Education)'
            Group    = 'Space & Science'
            Logo     = 'https://www.nasa.gov/wp-content/uploads/sites/2/2023/07/nasa-meatball.png'
            Language = 'en'
            Url      = 'https://ntv1-ak.akamaized.net/hls/live/2014075/NASA-Public-Channel/master.m3u8'
        }
        [pscustomobject]@{
            Id       = 'dw-news-en'
            Name     = 'DW News (English)'
            Group    = 'News'
            Logo     = 'https://upload.wikimedia.org/wikipedia/commons/1/19/Deutsche_Welle_logo.svg'
            Language = 'en'
            Url      = 'https://dwstream30-lh.akamaihd.net/i/dwstream30_delivery@131329/master.m3u8'
        }
        [pscustomobject]@{
            Id       = 'bloomberg-quicktake'
            Name     = 'Bloomberg Quicktake'
            Group    = 'News'
            Logo     = 'https://upload.wikimedia.org/wikipedia/en/0/0f/Bloomberg_logo.svg'
            Language = 'en'
            Url      = 'https://www.bloomberg.com/media-manifest/streams/qt.m3u8'
        }
        [pscustomobject]@{
            Id       = 'big-buck-bunny'
            Name     = 'Big Buck Bunny (Demo)'
            Group    = 'Animation'
            Logo     = 'https://upload.wikimedia.org/wikipedia/commons/7/70/Big_Buck_Bunny_alt_poster.jpg'
            Language = 'en'
            Url      = 'https://storage.googleapis.com/shaka-demo-assets/angel-one-hls/hls.m3u8'
        }
        [pscustomobject]@{
            Id       = 'sintel-open-movie'
            Name     = 'Sintel (Open Movie)'
            Group    = 'Movies'
            Logo     = 'https://upload.wikimedia.org/wikipedia/commons/3/3c/Sintel_poster.jpg'
            Language = 'en'
            Url      = 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'
        }
        [pscustomobject]@{
            Id       = 'tears-of-steel'
            Name     = 'Tears of Steel (Demo)'
            Group    = 'Sci-Fi'
            Logo     = 'https://upload.wikimedia.org/wikipedia/commons/7/73/Tears_of_Steel_poster.jpg'
            Language = 'en'
            Url      = 'https://test-streams.mux.dev/ptsVOD/tears_of_steel.m3u8'
        }
        [pscustomobject]@{
            Id       = 'akamai-test'
            Name     = 'Akamai Test Channel'
            Group    = 'Tech Demos'
            Logo     = 'https://upload.wikimedia.org/wikipedia/commons/3/3b/Akamai_logo.svg'
            Language = 'en'
            Url      = 'https://cph-p2p-msl.akamaized.net/hls/live/2000341/test/master.m3u8'
        }
        [pscustomobject]@{
            Id       = 'red-bull-tv'
            Name     = 'Red Bull TV (Demo)'
            Group    = 'Sports & Culture'
            Logo     = 'https://upload.wikimedia.org/wikipedia/en/6/6c/Red_Bull_TV_logo.svg'
            Language = 'en'
            Url      = 'https://test-streams.mux.dev/ptsVOD/redbull_tv.m3u8'
        }
    )

    $lines = [System.Collections.Generic.List[string]]::new()
    $lines.Add('#EXTM3U') | Out-Null

    foreach ($channel in $channels) {
        $metaParts = [System.Collections.Generic.List[string]]::new()

        if ($channel.Id) {
            $metaParts.Add(('tvg-id="{0}"' -f $channel.Id)) | Out-Null
        }
        if ($channel.Name) {
            $metaParts.Add(('tvg-name="{0}"' -f $channel.Name)) | Out-Null
        }
        if ($channel.Logo) {
            $metaParts.Add(('tvg-logo="{0}"' -f $channel.Logo)) | Out-Null
        }
        if ($channel.Group) {
            $metaParts.Add(('group-title="{0}"' -f $channel.Group)) | Out-Null
        }
        if ($channel.Language) {
            $metaParts.Add(('language="{0}"' -f $channel.Language)) | Out-Null
        }

        $metaString = if ($metaParts.Count -gt 0) { ($metaParts -join ' ') + ',' } else { ',' }

        $lines.Add("#EXTINF:-1 $metaString$($channel.Name)") | Out-Null
        $lines.Add($channel.Url) | Out-Null
    }

    return $lines
}

$totalCreated = 0

for ($index = 0; $index -lt $categoryConfigs.Count; $index++) {
    $category = $categoryConfigs[$index]
    $targetDirectory = Join-Path $libraryRootPath $category.Directory
    if (-not (Test-Path -LiteralPath $targetDirectory)) {
        New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null
    }

    if ($Clean) {
        Remove-ExistingDemoFiles -Path $targetDirectory
    }

    # Always remove previously generated files to keep the dataset deterministic.
    Remove-ExistingDemoFiles -Path $targetDirectory

    $allocation = [math]::Floor($TotalStubEntries / $categoryConfigs.Count)
    if ($index -lt ($TotalStubEntries % $categoryConfigs.Count)) {
        $allocation++
    }

    for ($i = 1; $i -le $allocation; $i++) {
        $fileNameRoot = [string]::Format($category.Template, $i)
        $fileName = "$fileNameRoot$($category.Extension)"
        $filePath = Join-Path $targetDirectory $fileName
        $description = [string]::Format($category.DescriptionTemplate, $i)

        Write-PlaceholderFile -Path $filePath -Category $category.Name -Description $description
        $totalCreated++
    }
}

$playlistLines = New-PlaylistLines
$playlistLines | Set-Content -Path $PlaylistOutput -Encoding UTF8

Write-Host "Generated $totalCreated demo media placeholders under $libraryRootPath" -ForegroundColor Green
Write-Host "Sample playlist written to $PlaylistOutput" -ForegroundColor Green

[pscustomobject]@{
    LibraryRoot    = $libraryRootPath.ProviderPath
    PlaylistOutput = (Resolve-Path -Path $PlaylistOutput).ProviderPath
    TotalCreated   = $totalCreated
}
