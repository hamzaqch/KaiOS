<#
.SYNOPSIS
    Installs KaiOS for the current user.

.DESCRIPTION
    Copies the agents, skills and path-scoped instructions into the user-level
    Copilot directory, creates the KaiOS home tree, installs the doctrine copy,
    and renders the user-level hook registry with absolute paths so hooks work
    from any workspace.

    The install is idempotent. File contents are compared before writing, so a
    second run reports 0 files changed. Nothing outside the two target
    directories is touched, and no elevation is required.

.PARAMETER CopilotHome
    User-level Copilot directory. Defaults to .copilot under the user profile.

.PARAMETER KaiosHome
    KaiOS runtime home. Defaults to KAIOS_HOME when set, otherwise .kaios under
    the user profile.

.PARAMETER Force
    Rewrite every file even when the content already matches.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File Install.ps1

.NOTES
    Windows PowerShell 5.1 compatible.
#>
[CmdletBinding()]
param(
    [string]$CopilotHome,
    [string]$KaiosHome,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$script:FilesChanged = 0
$script:FilesUnchanged = 0
$script:DirsCreated = 0
$script:Notes = New-Object System.Collections.Generic.List[string]
$script:ForceWrite = [bool]$Force

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

function Test-WindowsHost {
    [CmdletBinding()]
    param()

    if ($env:OS -eq 'Windows_NT') { return $true }
    if (Test-Path -LiteralPath 'variable:IsWindows') {
        return [bool](Get-Variable -Name 'IsWindows' -ValueOnly)
    }
    return $false
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

function New-DirectoryIfMissing {
    [CmdletBinding()]
    param([string]$Path)

    if (Test-Path -LiteralPath $Path) { return }
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
    $script:DirsCreated++
}

function Write-Utf8NoBom {
    [CmdletBinding()]
    param([string]$Path, [string]$Text)

    $parent = Split-Path -Parent $Path
    if ($parent) { New-DirectoryIfMissing -Path $parent }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function Test-SameContent {
    [CmdletBinding()]
    param([string]$Left, [string]$Right)

    if (-not (Test-Path -LiteralPath $Right)) { return $false }
    $a = [System.IO.File]::ReadAllBytes($Left)
    $b = [System.IO.File]::ReadAllBytes($Right)
    if ($a.Length -ne $b.Length) { return $false }
    for ($i = 0; $i -lt $a.Length; $i++) {
        if ($a[$i] -ne $b[$i]) { return $false }
    }
    return $true
}

function Copy-FileIfDifferent {
    [CmdletBinding()]
    param([string]$Source, [string]$Destination)

    if ((-not $script:ForceWrite) -and (Test-SameContent -Left $Source -Right $Destination)) {
        $script:FilesUnchanged++
        return
    }
    $parent = Split-Path -Parent $Destination
    if ($parent) { New-DirectoryIfMissing -Path $parent }
    Copy-Item -LiteralPath $Source -Destination $Destination -Force
    $script:FilesChanged++
}

function Copy-TreeIfDifferent {
    [CmdletBinding()]
    param([string]$Source, [string]$Destination, [string]$Label)

    if (-not (Test-Path -LiteralPath $Source)) {
        $script:Notes.Add(("skipped {0} — not present in this checkout" -f $Label))
        return
    }
    $root = (Resolve-Path -LiteralPath $Source).Path
    $files = @(Get-ChildItem -LiteralPath $root -Recurse -File | Where-Object { $_.FullName -notmatch '__pycache__' -and $_.Extension -ne '.pyc' })
    if ($files.Count -eq 0) {
        $script:Notes.Add(("skipped {0} — directory is empty" -f $Label))
        return
    }
    New-DirectoryIfMissing -Path $Destination
    foreach ($file in $files) {
        $relative = $file.FullName.Substring($root.Length)
        $target = Join-KaiosPath -Base $Destination -Relative $relative
        Copy-FileIfDifferent -Source $file.FullName -Destination $target
    }
}

function Resolve-PythonLauncher {
    [CmdletBinding()]
    param()

    $candidates = @(
        @{ Name = 'python';  Prefix = @() },
        @{ Name = 'python3'; Prefix = @() },
        @{ Name = 'py';      Prefix = @('-3') }
    )
    foreach ($candidate in $candidates) {
        $found = Get-Command -Name $candidate.Name -CommandType Application -ErrorAction SilentlyContinue
        if ($found) {
            $exe = $found | Select-Object -First 1
            return @{ Exe = $exe.Source; Prefix = $candidate.Prefix }
        }
    }
    return $null
}

function Format-CommandToken {
    [CmdletBinding()]
    param([string]$Token)

    if ($Token -match '\s') { return '"' + $Token + '"' }
    return $Token
}

function ConvertTo-JsonStringLiteral {
    [CmdletBinding()]
    param([string]$Value)

    $builder = New-Object System.Text.StringBuilder
    [void]$builder.Append('"')
    foreach ($char in $Value.ToCharArray()) {
        $code = [int]$char
        if ($char -eq '"') { [void]$builder.Append('\"') }
        elseif ($char -eq '\') { [void]$builder.Append('\\') }
        elseif ($char -eq "`n") { [void]$builder.Append('\n') }
        elseif ($char -eq "`r") { [void]$builder.Append('\r') }
        elseif ($char -eq "`t") { [void]$builder.Append('\t') }
        elseif ($code -lt 32) { [void]$builder.Append(('\u{0:x4}' -f $code)) }
        else { [void]$builder.Append($char) }
    }
    [void]$builder.Append('"')
    return $builder.ToString()
}

function Format-HookRegistry {
    [CmdletBinding()]
    param(
        [string]$TemplatePath,
        [string]$WrapperPath,
        [hashtable]$Launcher
    )

    $template = [System.IO.File]::ReadAllText($TemplatePath) | ConvertFrom-Json
    $events = @($template.hooks.PSObject.Properties.Name)
    if ($events.Count -eq 0) {
        throw "hook template $TemplatePath registers no events"
    }

    $timeout = 20
    $firstEntries = @($template.hooks.($events[0]))
    if ($firstEntries.Count -gt 0) {
        $entry = $firstEntries[0]
        if ($entry.PSObject.Properties.Name -contains 'timeout') {
            $timeout = [int]$entry.timeout
        }
    }

    $pythonTokens = @()
    if ($Launcher) {
        $pythonTokens += (Format-CommandToken -Token $Launcher.Exe)
        foreach ($item in $Launcher.Prefix) {
            $pythonTokens += (Format-CommandToken -Token $item)
        }
    }
    else {
        $pythonTokens += 'python3'
    }
    $pythonPrefix = ($pythonTokens -join ' ')
    $wrapperToken = Format-CommandToken -Token $WrapperPath

    $lines = New-Object System.Collections.Generic.List[string]
    $lines.Add('{')
    $lines.Add('  "version": 1,')
    $lines.Add('  "hooks": {')
    for ($i = 0; $i -lt $events.Count; $i++) {
        $name = $events[$i]
        $posix = "$pythonPrefix -m kaios.hooks $name"
        $windows = "powershell -NoProfile -ExecutionPolicy Bypass -File $wrapperToken $name"
        $lines.Add('    ' + (ConvertTo-JsonStringLiteral -Value $name) + ': [')
        $lines.Add('      {')
        $lines.Add('        "type": "command",')
        $lines.Add('        "command": ' + (ConvertTo-JsonStringLiteral -Value $posix) + ',')
        $lines.Add('        "windows": ' + (ConvertTo-JsonStringLiteral -Value $windows) + ',')
        $lines.Add('        "timeout": ' + $timeout)
        $lines.Add('      }')
        if ($i -lt ($events.Count - 1)) { $lines.Add('    ],') } else { $lines.Add('    ]') }
    }
    $lines.Add('  }')
    $lines.Add('}')
    return (($lines -join "`n") + "`n")
}

# ----------------------------------------------------------------------------
# Resolve locations
# ----------------------------------------------------------------------------

$repoRoot = $PSScriptRoot
if (-not $repoRoot) { $repoRoot = (Get-Location).Path }
$repoRoot = (Resolve-Path -LiteralPath $repoRoot).Path

$githubDir = Join-Path -Path $repoRoot -ChildPath '.github'
if (-not (Test-Path -LiteralPath $githubDir)) {
    Write-Error "Install.ps1 must run from the KaiOS repository root; no .github directory under $repoRoot"
    exit 2
}

$userHome = Get-UserHome
if (-not $CopilotHome) { $CopilotHome = Join-Path -Path $userHome -ChildPath '.copilot' }
if (-not $KaiosHome) {
    if ($env:KAIOS_HOME) { $KaiosHome = $env:KAIOS_HOME }
    else { $KaiosHome = Join-Path -Path $userHome -ChildPath '.kaios' }
}

Write-Host ''
Write-Host '════ KaiOS install ═══════════════════════════'
Write-Host ''
Write-Host ("  repository   : {0}" -f $repoRoot)
Write-Host ("  copilot home : {0}" -f $CopilotHome)
Write-Host ("  kaios home   : {0}" -f $KaiosHome)
Write-Host ''

# ----------------------------------------------------------------------------
# Copilot surfaces
# ----------------------------------------------------------------------------

New-DirectoryIfMissing -Path $CopilotHome

$surfaces = @(
    @{ Source = 'agents';       Target = 'agents' },
    @{ Source = 'skills';       Target = 'skills' },
    @{ Source = 'instructions'; Target = 'instructions' }
)
foreach ($surface in $surfaces) {
    $from = Join-KaiosPath -Base $githubDir -Relative $surface.Source
    $to = Join-KaiosPath -Base $CopilotHome -Relative $surface.Target
    Copy-TreeIfDifferent -Source $from -Destination $to -Label (".github/" + $surface.Source)
}

# ----------------------------------------------------------------------------
# KaiOS home tree
# ----------------------------------------------------------------------------

$homeDirs = @(
    'CONFIG',
    'USER',
    'MEMORY/WORK',
    'MEMORY/STATE',
    'MEMORY/KNOWLEDGE',
    'MEMORY/LEARNING/REFLECTIONS',
    'MEMORY/LEARNING/INCIDENTS',
    'MEMORY/OBSERVABILITY',
    'SYSTEM'
)
New-DirectoryIfMissing -Path $KaiosHome
foreach ($relative in $homeDirs) {
    New-DirectoryIfMissing -Path (Join-KaiosPath -Base $KaiosHome -Relative $relative)
}

$doctrineDirs = @('ALGORITHM', 'RULES', 'TEMPLATES', 'CONFIG', 'DOCUMENTATION')

# The doctrine tree is SYSTEM. Older checkouts still carry it as KAIOS, so read
# from that when SYSTEM is absent and say so in the summary. The install target
# is SYSTEM either way, so a fallback never changes where doctrine lands.
$doctrineSource = Join-Path -Path $repoRoot -ChildPath 'SYSTEM'
if (-not (Test-Path -LiteralPath $doctrineSource)) {
    $legacySource = Join-Path -Path $repoRoot -ChildPath 'KAIOS'
    if (Test-Path -LiteralPath $legacySource) {
        $doctrineSource = $legacySource
        $script:Notes.Add('doctrine read from the legacy KAIOS directory because SYSTEM is absent — it still installs to SYSTEM')
    }
}
$sourceLabel = Split-Path -Leaf $doctrineSource
$doctrineTarget = Join-KaiosPath -Base $KaiosHome -Relative 'SYSTEM'
foreach ($name in $doctrineDirs) {
    $from = Join-KaiosPath -Base $doctrineSource -Relative $name
    $to = Join-KaiosPath -Base $doctrineTarget -Relative $name
    Copy-TreeIfDifferent -Source $from -Destination $to -Label ($sourceLabel + '/' + $name)
}

# ----------------------------------------------------------------------------
# Python package copy, so hooks import `kaios` from ANY workspace
# ----------------------------------------------------------------------------

$packageSource = Join-KaiosPath -Base $repoRoot -Relative 'kaios'
$packageTarget = Join-KaiosPath -Base $KaiosHome -Relative 'lib/kaios'
Copy-TreeIfDifferent -Source $packageSource -Destination $packageTarget -Label 'kaios (package)'

# ----------------------------------------------------------------------------
# User-level hook registry, rendered with absolute paths
# ----------------------------------------------------------------------------

$hookTemplate = Join-KaiosPath -Base $githubDir -Relative 'hooks/kaios.json'
$hookWrapper = Join-KaiosPath -Base $githubDir -Relative 'hooks/kaios.ps1'
$hookTarget = Join-KaiosPath -Base $CopilotHome -Relative 'hooks/kaios.json'

$launcher = Resolve-PythonLauncher
if (-not $launcher) {
    $script:Notes.Add('python not found on PATH — hook registry rendered with a bare python3 command')
}

if (Test-Path -LiteralPath $hookTemplate) {
    $rendered = Format-HookRegistry -TemplatePath $hookTemplate -WrapperPath $hookWrapper -Launcher $launcher
    $existing = ''
    if (Test-Path -LiteralPath $hookTarget) {
        $existing = [System.IO.File]::ReadAllText($hookTarget)
    }
    if ($script:ForceWrite -or ($existing -ne $rendered)) {
        Write-Utf8NoBom -Path $hookTarget -Text $rendered
        $script:FilesChanged++
    }
    else {
        $script:FilesUnchanged++
    }
}
else {
    $script:Notes.Add('skipped hooks/kaios.json — template not present in this checkout')
}

# ----------------------------------------------------------------------------
# KAIOS_HOME environment variable (Windows only, never overwritten)
# ----------------------------------------------------------------------------

$envNote = 'skipped — not a Windows host'
if (Test-WindowsHost) {
    $current = [Environment]::GetEnvironmentVariable('KAIOS_HOME', 'User')
    if ($current) {
        $envNote = ("already set to {0} — left alone" -f $current)
    }
    else {
        [Environment]::SetEnvironmentVariable('KAIOS_HOME', $KaiosHome, 'User')
        $envNote = ("set to {0} — open a new terminal to pick it up" -f $KaiosHome)
    }
    # KAIOS_REPO always points at this checkout so the hook wrapper can find the
    # package even before the lib copy exists; refreshed on every install.
    [Environment]::SetEnvironmentVariable('KAIOS_REPO', $repoRoot, 'User')
}

# ----------------------------------------------------------------------------
# Self-check
# ----------------------------------------------------------------------------

$doctorLine = 'not run — python not found on PATH'
if ($launcher) {
    $doctorArgs = @()
    foreach ($item in $launcher.Prefix) { $doctorArgs += $item }
    $doctorArgs += '-m'
    $doctorArgs += 'kaios'
    $doctorArgs += 'doctor'
    Push-Location -LiteralPath $repoRoot
    try {
        $env:KAIOS_HOME = $KaiosHome
        $doctorOutput = & $launcher.Exe $doctorArgs 2>&1
        $code = $LASTEXITCODE
        if ($code -eq 0) {
            $doctorLine = 'PASS'
        }
        else {
            $doctorLine = ("exit {0} — the Python package is not ready yet, this is a warning only" -f $code)
        }
        if ($doctorOutput) {
            $script:Notes.Add('doctor output: ' + (($doctorOutput | Out-String).Trim()))
        }
    }
    catch {
        $doctorLine = ('could not run — {0}' -f $_.Exception.Message)
    }
    finally {
        Pop-Location
    }
}

# ----------------------------------------------------------------------------
# Summary
# ----------------------------------------------------------------------------

Write-Host ("  files changed        : {0}" -f $script:FilesChanged)
Write-Host ("  files unchanged      : {0}" -f $script:FilesUnchanged)
Write-Host ("  directories created  : {0}" -f $script:DirsCreated)
Write-Host ("  KAIOS_HOME variable  : {0}" -f $envNote)
Write-Host ("  kaios doctor         : {0}" -f $doctorLine)
Write-Host ''

if ($script:Notes.Count -gt 0) {
    Write-Host '  notes:'
    foreach ($note in $script:Notes) {
        Write-Host ("    - {0}" -f $note)
    }
    Write-Host ''
}

Write-Host ("KaiOS install complete — {0} files changed, {1} unchanged." -f $script:FilesChanged, $script:FilesUnchanged)
Write-Host ''
exit 0
