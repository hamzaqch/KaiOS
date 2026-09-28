<#
.SYNOPSIS
    Drops the KaiOS workspace scaffold into a repository.

.DESCRIPTION
    Copies the constitution, the path-scoped instructions, the agents, the
    skills and the hook registry into the target repository's .github
    directory, and writes a .vscode/mcp.json with no servers configured.

    Nothing is ever overwritten. A destination file that already exists is
    left exactly as it is and counted as skipped, so running this against a
    repository that has its own customised copies is safe.

.PARAMETER Path
    The repository to scaffold.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Init-Workspace.ps1 -Path C:\work\my-repo

.NOTES
    Windows PowerShell 5.1 compatible.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Path
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

function Copy-TreeIfAbsent {
    [CmdletBinding()]
    param([string]$Source, [string]$Destination, [string]$Label)

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
        $target = Join-KaiosPath -Base $Destination -Relative $relative
        Copy-FileIfAbsent -Source $file.FullName -Destination $target
    }
}

# ----------------------------------------------------------------------------
# Resolve locations
# ----------------------------------------------------------------------------

$repoRoot = $PSScriptRoot
if (-not $repoRoot) { $repoRoot = (Get-Location).Path }
$repoRoot = (Resolve-Path -LiteralPath $repoRoot).Path

$sourceGithub = Join-Path -Path $repoRoot -ChildPath '.github'
if (-not (Test-Path -LiteralPath $sourceGithub)) {
    Write-Error "Init-Workspace.ps1 must run from the KaiOS repository root; no .github directory under $repoRoot"
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
# .github surfaces
# ----------------------------------------------------------------------------

$constitution = Join-KaiosPath -Base $sourceGithub -Relative 'copilot-instructions.md'
if (Test-Path -LiteralPath $constitution) {
    Copy-FileIfAbsent -Source $constitution -Destination (Join-KaiosPath -Base $target -Relative '.github/copilot-instructions.md')
}
else {
    $script:Notes.Add('skipped .github/copilot-instructions.md — not present in this checkout')
}

$trees = @('instructions', 'agents', 'skills', 'hooks')
foreach ($name in $trees) {
    $from = Join-KaiosPath -Base $sourceGithub -Relative $name
    $to = Join-KaiosPath -Base $target -Relative ('.github/' + $name)
    Copy-TreeIfAbsent -Source $from -Destination $to -Label ('.github/' + $name)
}

# ----------------------------------------------------------------------------
# .vscode/mcp.json — rendered from the template with no servers configured
# ----------------------------------------------------------------------------

$mcpTemplate = Join-KaiosPath -Base $repoRoot -Relative '.vscode/mcp.json.template'
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
