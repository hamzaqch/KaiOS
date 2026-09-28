<#
.SYNOPSIS
    Removes the user-level KaiOS install.

.DESCRIPTION
    Deletes only what Install.ps1 put under the user-level Copilot directory.
    The list of things to remove is derived from this checkout, so an agent,
    skill or instructions file that KaiOS never shipped is left untouched.

    The KaiOS home is left alone by default because it holds memory, the ISA
    registry, the configuration and the installed SYSTEM doctrine copy under
    $KAIOS_HOME/SYSTEM. Removing it needs both -PurgeHome and
    -Force, and even then nothing else is deleted implicitly.

.PARAMETER CopilotHome
    User-level Copilot directory. Defaults to .copilot under the user profile.

.PARAMETER KaiosHome
    KaiOS runtime home. Defaults to KAIOS_HOME when set, otherwise .kaios under
    the user profile. Only used with -PurgeHome.

.PARAMETER PurgeHome
    Also delete the KaiOS home tree. Requires -Force.

.PARAMETER Force
    Confirms the destructive part of -PurgeHome.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .github\scripts\Uninstall.ps1

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .github\scripts\Uninstall.ps1 -WhatIf

.NOTES
    Windows PowerShell 5.1 compatible. This script sits two levels below the
    repository root, at .github\scripts.
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [string]$CopilotHome,
    [string]$KaiosHome,
    [switch]$PurgeHome,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:Removed = 0
$script:Missing = 0
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

function Get-UserHome {
    [CmdletBinding()]
    param()

    if ($env:USERPROFILE) { return $env:USERPROFILE }
    if ($env:HOME) { return $env:HOME }
    if (Test-Path -LiteralPath 'variable:HOME') {
        return [string](Get-Variable -Name 'HOME' -ValueOnly)
    }
    return (Get-Location).Path
}

function Remove-KaiosItem {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([string]$Target, [string]$Label)

    if (-not (Test-Path -LiteralPath $Target)) {
        $script:Missing++
        return
    }
    if ($PSCmdlet.ShouldProcess($Target, 'Remove')) {
        Remove-Item -LiteralPath $Target -Recurse -Force
        $script:Removed++
        Write-Host ("  removed {0}" -f $Label)
    }
}

function Remove-IfEmptyDirectory {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param([string]$Target)

    if (-not (Test-Path -LiteralPath $Target)) { return }
    $remaining = @(Get-ChildItem -LiteralPath $Target -Force)
    if ($remaining.Count -gt 0) {
        $script:Notes.Add(("left {0} in place — it still holds {1} item(s) KaiOS did not install" -f $Target, $remaining.Count))
        return
    }
    if ($PSCmdlet.ShouldProcess($Target, 'Remove empty directory')) {
        Remove-Item -LiteralPath $Target -Force
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

$userHome = Get-UserHome
if (-not $CopilotHome) { $CopilotHome = Join-Path -Path $userHome -ChildPath '.copilot' }
if (-not $KaiosHome) {
    if ($env:KAIOS_HOME) { $KaiosHome = $env:KAIOS_HOME }
    else { $KaiosHome = Join-Path -Path $userHome -ChildPath '.kaios' }
}

Write-Host ''
Write-Host '════ KaiOS uninstall ═════════════════════════'
Write-Host ''
Write-Host ("  copilot home : {0}" -f $CopilotHome)
Write-Host ("  kaios home   : {0}" -f $KaiosHome)
Write-Host ''

if (-not (Test-Path -LiteralPath $CopilotHome)) {
    Write-Host ("  nothing to do — {0} does not exist" -f $CopilotHome)
    Write-Host ''
    exit 0
}

# ----------------------------------------------------------------------------
# Remove only the names this checkout ships
# ----------------------------------------------------------------------------

$surfaces = @('agents', 'skills', 'instructions')
foreach ($surface in $surfaces) {
    $sourceDir = Join-KaiosPath -Base $sourceGithub -Relative $surface
    $targetDir = Join-KaiosPath -Base $CopilotHome -Relative $surface
    if (-not (Test-Path -LiteralPath $sourceDir)) { continue }
    if (-not (Test-Path -LiteralPath $targetDir)) { continue }
    foreach ($entry in @(Get-ChildItem -LiteralPath $sourceDir -Force)) {
        $candidate = Join-Path -Path $targetDir -ChildPath $entry.Name
        Remove-KaiosItem -Target $candidate -Label ($surface + '/' + $entry.Name)
    }
    Remove-IfEmptyDirectory -Target $targetDir
}

# The registry and the two wrappers Install.ps1 puts beside it.
foreach ($name in @('kaios.json', 'kaios.ps1', 'kaios.sh')) {
    $candidate = Join-KaiosPath -Base $CopilotHome -Relative ('hooks/' + $name)
    Remove-KaiosItem -Target $candidate -Label ('hooks/' + $name)
}
Remove-IfEmptyDirectory -Target (Join-KaiosPath -Base $CopilotHome -Relative 'hooks')

# ----------------------------------------------------------------------------
# The KaiOS home, only on an explicit double opt-in
# ----------------------------------------------------------------------------

if ($PurgeHome) {
    if (-not $Force) {
        $script:Notes.Add('-PurgeHome ignored — it holds your memory, ISA registry and config, so it also needs -Force')
    }
    elseif (-not (Test-Path -LiteralPath $KaiosHome)) {
        $script:Notes.Add(("-PurgeHome had nothing to do — {0} does not exist" -f $KaiosHome))
    }
    else {
        Remove-KaiosItem -Target $KaiosHome -Label $KaiosHome
    }
}
else {
    $script:Notes.Add(("left {0} in place — pass -PurgeHome -Force to delete it" -f $KaiosHome))
}

$script:Notes.Add('the KAIOS_HOME user environment variable is left as it is — remove it from System Properties if you want it gone')

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

Write-Host ''
Write-Host ("  items removed     : {0}" -f $script:Removed)
Write-Host ("  already absent    : {0}" -f $script:Missing)
Write-Host ''

if ($script:Notes.Count -gt 0) {
    Write-Host '  notes:'
    foreach ($note in $script:Notes) {
        Write-Host ("    - {0}" -f $note)
    }
    Write-Host ''
}

Write-Host ("KaiOS uninstall complete — {0} items removed." -f $script:Removed)
Write-Host ''
exit 0
