<#
.SYNOPSIS
    Drops the KaiOS workspace scaffold into a repository.

.DESCRIPTION
    The whole framework lives in one directory, so scaffolding a work repository
    is one copy: everything under .github goes into the target repository's
    .github, and a .vscode/mcp.json with no servers configured is rendered from
    the shipped template. That carries the constitution, the path-scoped
    instructions, the agents, the skills, the hook registry and wrappers, the
    Python package and the doctrine tree in a single move.

    The framework's own scripts and tests are left behind: a work repository
    consumes KaiOS, it does not build or re-install it. Pass -IncludeTests to
    carry the test suite too.

    Nothing is ever overwritten. A destination file that already exists is
    left exactly as it is and counted as skipped, so running this against a
    repository that has its own customised copies is safe.

.PARAMETER Path
    The repository to scaffold.

.PARAMETER IncludeTests
    Also copy .github/tests into the target repository.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .github\scripts\Init-Workspace.ps1 -Path C:\work\my-repo

.NOTES
    Windows PowerShell 5.1 compatible. This script sits two levels below the
    repository root, at .github\scripts.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path,
    [switch]$IncludeTests
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Created = 0
$script:Skipped = 0
$script:Notes = New-Object System.Collections.Generic.List[string]

function Join-KaiosPath {
    [CmdletBinding()]
    param([string]$Base, [string]$Relative)

    $result = $Base
    foreach ($segment in ($Relative -split '[\\/]+')) {
        if ($segment) {
            $result = Join-Path -Path $result -ChildPath $segment
        }
    }
    return $result
}

function New-DirectoryIfMissing {
    [CmdletBinding()]
    param([string]$Target)

    if (Test-Path -LiteralPath $Target) { return }
    New-Item -ItemType Directory -Path $Target -Force | Out-Null
}

function Write-Utf8NoBom {
    [CmdletBinding()]
    param([string]$Target, [string]$Text)

    $parent = Split-Path -Parent $Target
    if ($parent) { New-DirectoryIfMissing -Target $parent }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Target, $Text, $encoding)
}

function Copy-FileIfAbsent {
    [CmdletBinding()]
    param([string]$Source, [string]$Destination)

    if (Test-Path -LiteralPath $Destination) {
        $script:Skipped++
        return
    }
    $parent = Split-Path -Parent $Destination
    if ($parent) { New-DirectoryIfMissing -Target $parent }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    $script:Created++
}

function Test-CarriedFile {
    # Build artefacts never travel, and the framework's own scripts and tests are
    # not part of what a work repository consumes.
    [CmdletBinding()]
    param([string]$Relative, [string[]]$ExcludedTop)

    $segments = @($Relative -split '[\\/]+' | Where-Object { $_ })
    if ($segments.Count -eq 0) { return $false }
    if ($ExcludedTop -contains $segments[0]) { return $false }
    foreach ($segment in $segments) {
        if ($segment -eq '__pycache__') { return $false }
    }
    if ([System.IO.Path]::GetExtension($Relative) -eq '.pyc') { return $false }
    return $true
}

function Copy-TreeIfAbsent {
    [CmdletBinding()]
    param([string]$Source, [string]$Destination, [string]$Label, [string[]]$ExcludedTop = @())

    if (-not (Test-Path -LiteralPath $Source)) {
        $script:Notes.Add(("skipped {0} — not present in this checkout" -f $Label))
        return
    }
    $root = (Resolve-Path -LiteralPath $Source).Path
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -File)
    if ($files.Count -eq 0) {
        $script:Notes.Add(("skipped {0} — directory is empty" -f $Label))
        return
    }
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($root.Length)
        if (-not (Test-CarriedFile -Relative $relative -ExcludedTop $ExcludedTop)) { continue }
        $target = Join-KaiosPath -Base $Destination -Relative $relative
        Copy-FileIfAbsent -Source $file.FullName -Destination $target
    }
}

# ----------------------------------------------------------------------------
# Resolve locations
# ----------------------------------------------------------------------------

# This script lives at <repo>\.github\scripts, so the repository root is two
# levels up and the framework directory is one.
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
$scriptDir = (Resolve-Path -LiteralPath $scriptDir).Path
$repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
if (-not $repoRoot) { $repoRoot = (Get-Location).Path }
$repoRoot = (Resolve-Path -LiteralPath $repoRoot).Path

$sourceGithub = Join-Path -Path $repoRoot -ChildPath '.github'
if (-not (Test-Path -LiteralPath $sourceGithub)) {
    Write-Error "no .github directory under $repoRoot; run this script from inside the KaiOS checkout"
    exit 2
}

if (-not (Test-Path -LiteralPath $Path)) {
    New-DirectoryIfMissing -Target $Path
    $script:Notes.Add('target directory did not exist and was created')
}
$target = (Resolve-Path -LiteralPath $Path).Path
if ($target -eq $repoRoot) {
    Write-Error 'the target is the KaiOS repository itself; pick a different repository'
    exit 2
}

Write-Host ''
Write-Host '════ KaiOS workspace scaffold ════════════════'
Write-Host ''
Write-Host ("  source : {0}" -f $repoRoot)
Write-Host ("  target : {0}" -f $target)
Write-Host ''

# ----------------------------------------------------------------------------
# The framework: one directory, copied whole
# ----------------------------------------------------------------------------

$excludedTop = @('scripts')
if (-not $IncludeTests) { $excludedTop += 'tests' }

Copy-TreeIfAbsent -Source $sourceGithub `
    -Destination (Join-KaiosPath -Base $target -Relative '.github') `
    -Label '.github' `
    -ExcludedTop $excludedTop
$script:Notes.Add(('left behind: {0}' -f ($excludedTop -join ', ')))

# ----------------------------------------------------------------------------
# .vscode/mcp.json — rendered from the template with no servers configured
# ----------------------------------------------------------------------------

$mcpTemplate = Join-KaiosPath -Base $sourceGithub -Relative 'SYSTEM/TEMPLATES/mcp.json.template'
$mcpTarget = Join-KaiosPath -Base $target -Relative '.vscode/mcp.json'
if (-not (Test-Path -LiteralPath $mcpTemplate)) {
    $script:Notes.Add('skipped .vscode/mcp.json — template not present in this checkout')
}
elseif (Test-Path -LiteralPath $mcpTarget) {
    $script:Skipped++
}
else {
    $text = [System.IO.File]::ReadAllText($mcpTemplate)
    # Drop every placeholder line so the rendered file is a valid, empty registry.
    $text = [System.Text.RegularExpressions.Regex]::Replace($text, '(?m)^[ \t]*\{\{[A-Za-z0-9_]+\}\}[ \t]*\r?\n', '')
    $text = [System.Text.RegularExpressions.Regex]::Replace($text, '\{\{[A-Za-z0-9_]+\}\}', '')
    Write-Utf8NoBom -Target $mcpTarget -Text $text
    $script:Created++
    $script:Notes.Add('wrote .vscode/mcp.json with no servers — run python -m kaios setup render to add them')
}

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

Write-Host ("  files created : {0}" -f $script:Created)
Write-Host ("  files skipped : {0}" -f $script:Skipped)
Write-Host ''

if ($script:Notes.Count -gt 0) {
    Write-Host '  notes:'
    foreach ($note in $script:Notes) {
        Write-Host ("    - {0}" -f $note)
    }
    Write-Host ''
}

Write-Host ("KaiOS scaffold complete — {0} created, {1} left alone." -f $script:Created, $script:Skipped)
Write-Host ''
exit 0
