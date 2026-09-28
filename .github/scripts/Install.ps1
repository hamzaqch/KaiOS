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
    powershell -ExecutionPolicy Bypass -File .github\scripts\Install.ps1

.NOTES
    Windows PowerShell 5.1 compatible. The whole framework lives under .github,
    so this script sits two levels below the repository root.
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

function ConvertTo-KaiosJson {
    # A small deterministic serializer, used instead of ConvertTo-Json so the
    # rendered registry comes out byte-identical on every run of every host:
    # 5.1 and 7 differ in depth handling and in how they treat a one-element
    # array, and this file has to be idempotent on 5.1.
    [CmdletBinding()]
    param($Value, [int]$Depth = 0)

    $pad = ' ' * ($Depth * 2)
    $inner = ' ' * (($Depth + 1) * 2)

    if ($null -eq $Value) { return 'null' }
    if ($Value -is [string]) { return (ConvertTo-JsonStringLiteral -Value $Value) }
    if ($Value -is [bool]) {
        if ($Value) { return 'true' }
        return 'false'
    }
    if ($Value -is [int] -or $Value -is [long] -or $Value -is [double] -or $Value -is [decimal]) {
        return ([string]$Value)
    }

    $parts = New-Object System.Collections.Generic.List[string]

    if ($Value -is [System.Collections.IDictionary]) {
        foreach ($key in $Value.Keys) {
            $rendered = ConvertTo-KaiosJson -Value $Value[$key] -Depth ($Depth + 1)
            $parts.Add($inner + (ConvertTo-JsonStringLiteral -Value ([string]$key)) + ': ' + $rendered)
        }
        if ($parts.Count -eq 0) { return '{}' }
        return "{`n" + ($parts -join ",`n") + "`n" + $pad + '}'
    }

    if ($Value -is [System.Collections.IEnumerable]) {
        foreach ($item in $Value) {
            $parts.Add($inner + (ConvertTo-KaiosJson -Value $item -Depth ($Depth + 1)))
        }
        if ($parts.Count -eq 0) { return '[]' }
        return "[`n" + ($parts -join ",`n") + "`n" + $pad + ']'
    }

    foreach ($property in $Value.PSObject.Properties) {
        $rendered = ConvertTo-KaiosJson -Value $property.Value -Depth ($Depth + 1)
        $parts.Add($inner + (ConvertTo-JsonStringLiteral -Value $property.Name) + ': ' + $rendered)
    }
    if ($parts.Count -eq 0) { return '{}' }
    return "{`n" + ($parts -join ",`n") + "`n" + $pad + '}'
}

function Set-AbsoluteFileArgument {
    # `powershell … -File <path> <Event>`: the token after -File becomes absolute.
    [CmdletBinding()]
    param([string]$CommandLine, [string]$WrapperPath)

    $tokens = @($CommandLine -split ' ')
    for ($i = 0; $i -lt $tokens.Count; $i++) {
        if ($tokens[$i].ToLowerInvariant() -eq '-file') {
            if (($i + 1) -lt $tokens.Count) {
                $tokens[$i + 1] = Format-CommandToken -Token $WrapperPath
                return ($tokens -join ' ')
            }
        }
    }
    return $CommandLine
}

function Set-AbsoluteShellArgument {
    # `sh <path> <Event>`: the token after the shell becomes absolute.
    [CmdletBinding()]
    param([string]$CommandLine, [string]$WrapperPath)

    $shells = @('sh', 'bash', 'sh.exe', 'bash.exe')
    $tokens = @($CommandLine -split ' ')
    for ($i = 0; $i -lt $tokens.Count; $i++) {
        $leaf = ([System.IO.Path]::GetFileName($tokens[$i])).ToLowerInvariant()
        if ($shells -contains $leaf) {
            if (($i + 1) -lt $tokens.Count) {
                $tokens[$i + 1] = Format-CommandToken -Token $WrapperPath
                return ($tokens -join ' ')
            }
        }
    }
    return $CommandLine
}

function Set-AbsolutePythonArgument {
    # A bare `python -m kaios.hooks <Event>` gets this machine's interpreter.
    [CmdletBinding()]
    param([string]$CommandLine, [string]$PythonPrefix)

    if (-not $PythonPrefix) { return $CommandLine }
    $names = @('python', 'python3', 'py', 'python.exe', 'python3.exe', 'py.exe')
    $tokens = @($CommandLine -split ' ')
    if ($tokens.Count -eq 0) { return $CommandLine }
    $leaf = ([System.IO.Path]::GetFileName($tokens[0])).ToLowerInvariant()
    if ($names -contains $leaf) {
        $tokens[0] = $PythonPrefix
        return ($tokens -join ' ')
    }
    return $CommandLine
}

function Set-HookEntryPaths {
    # Every command line in one registry entry, pointed at an absolute wrapper.
    # Four keys can carry one: `bash` and `powershell` on a Copilot CLI entry,
    # `command` inside a Claude nested entry, and `command`/`windows` on an entry
    # in the shape KaiOS shipped before the two dialects were reconciled.
    [CmdletBinding()]
    param($Entry, [string]$WrapperPath, [string]$ShellWrapperPath, [string]$PythonPrefix)

    if ($null -eq $Entry) { return }
    $names = @($Entry.PSObject.Properties.Name)

    if ($names -contains 'hooks') {
        foreach ($nested in @($Entry.hooks)) {
            Set-HookEntryPaths -Entry $nested -WrapperPath $WrapperPath -ShellWrapperPath $ShellWrapperPath -PythonPrefix $PythonPrefix
        }
        return
    }
    if ($names -contains 'command') {
        $line = Set-AbsolutePythonArgument -CommandLine ([string]$Entry.command) -PythonPrefix $PythonPrefix
        $Entry.command = Set-AbsoluteFileArgument -CommandLine $line -WrapperPath $WrapperPath
    }
    if ($names -contains 'windows') {
        $Entry.windows = Set-AbsoluteFileArgument -CommandLine ([string]$Entry.windows) -WrapperPath $WrapperPath
    }
    if ($names -contains 'powershell') {
        $Entry.powershell = Set-AbsoluteFileArgument -CommandLine ([string]$Entry.powershell) -WrapperPath $WrapperPath
    }
    if ($names -contains 'bash') {
        $Entry.bash = Set-AbsoluteShellArgument -CommandLine ([string]$Entry.bash) -WrapperPath $ShellWrapperPath
    }
}

function Format-HookRegistry {
    # The checked-in registry with absolute wrapper paths and nothing else
    # changed. Its event-key spelling and its two entry shapes are what decide
    # whether each of Copilot's two hook engines can read the file at all, so
    # this rewrites the paths in place rather than rebuilding the structure.
    [CmdletBinding()]
    param(
        [string]$RegistryPath,
        [string]$WrapperPath,
        [string]$ShellWrapperPath,
        [hashtable]$Launcher
    )

    $registry = [System.IO.File]::ReadAllText($RegistryPath) | ConvertFrom-Json
    if (-not $registry) {
        throw "hook registry $RegistryPath does not parse"
    }
    if (-not (@($registry.PSObject.Properties.Name) -contains 'hooks')) {
        throw "hook registry $RegistryPath has no hooks object"
    }
    $events = @($registry.hooks.PSObject.Properties.Name)
    if ($events.Count -eq 0) {
        throw "hook registry $RegistryPath registers no events"
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

    foreach ($name in $events) {
        foreach ($entry in @($registry.hooks.$name)) {
            Set-HookEntryPaths -Entry $entry -WrapperPath $WrapperPath -ShellWrapperPath $ShellWrapperPath -PythonPrefix $pythonPrefix
        }
    }

    return ((ConvertTo-KaiosJson -Value $registry) + "`n")
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

$githubDir = Join-Path -Path $repoRoot -ChildPath '.github'
if (-not (Test-Path -LiteralPath $githubDir)) {
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

# The doctrine tree is .github\SYSTEM. A checkout made before the framework moved
# under .github carries it at the repository root, as SYSTEM or as the older
# KAIOS, so those are read as fallbacks. The install target is $KAIOS_HOME\SYSTEM
# in every case, so a fallback never changes where doctrine lands.
$doctrineCandidates = @(
    (Join-Path -Path $githubDir -ChildPath 'SYSTEM'),
    (Join-Path -Path $githubDir -ChildPath 'KAIOS'),
    (Join-Path -Path $repoRoot -ChildPath 'SYSTEM'),
    (Join-Path -Path $repoRoot -ChildPath 'KAIOS')
)
$doctrineSource = $doctrineCandidates[0]
foreach ($candidate in $doctrineCandidates) {
    if (Test-Path -LiteralPath $candidate) {
        $doctrineSource = $candidate
        break
    }
}
if ($doctrineSource -ne $doctrineCandidates[0]) {
    $script:Notes.Add(('doctrine read from {0} because .github\SYSTEM is absent — it still installs to SYSTEM' -f $doctrineSource))
}
$sourceLabel = Split-Path -Leaf $doctrineSource
$doctrineTarget = Join-KaiosPath -Base $KaiosHome -Relative 'SYSTEM'
foreach ($name in $doctrineDirs) {
    $from = Join-KaiosPath -Base $doctrineSource -Relative $name
    $to = Join-KaiosPath -Base $doctrineTarget -Relative $name
    Copy-TreeIfDifferent -Source $from -Destination $to -Label ($sourceLabel + '/' + $name)
}

# ----------------------------------------------------------------------------
# Python package copy from .github\kaios, so hooks import `kaios` from ANY workspace
# ----------------------------------------------------------------------------

$packageSource = Join-KaiosPath -Base $githubDir -Relative 'kaios'
$packageTarget = Join-KaiosPath -Base $KaiosHome -Relative 'lib/kaios'
Copy-TreeIfDifferent -Source $packageSource -Destination $packageTarget -Label 'kaios (package)'

# ----------------------------------------------------------------------------
# User-level hook registry, rendered with absolute paths
# ----------------------------------------------------------------------------

$hookSource = Join-KaiosPath -Base $githubDir -Relative 'hooks/kaios.json'
$hookDir = Join-KaiosPath -Base $CopilotHome -Relative 'hooks'
$hookTarget = Join-KaiosPath -Base $hookDir -Relative 'kaios.json'

# Both wrappers are copied beside the user-level registry, and the registry
# points at those copies, so hooks keep working when the checkout moves. The
# wrappers find the Python package from KAIOS_REPO or from $KAIOS_HOME\lib, both
# of which this installer sets, so they do not need to sit inside a checkout.
$hookWrapper = Join-KaiosPath -Base $hookDir -Relative 'kaios.ps1'
$hookShellWrapper = Join-KaiosPath -Base $hookDir -Relative 'kaios.sh'
$wrapperFiles = @(
    @{ Name = 'kaios.ps1'; Target = $hookWrapper },
    @{ Name = 'kaios.sh';  Target = $hookShellWrapper }
)
foreach ($item in $wrapperFiles) {
    $from = Join-KaiosPath -Base $githubDir -Relative ('hooks/' + $item.Name)
    if (Test-Path -LiteralPath $from) {
        Copy-FileIfDifferent -Source $from -Destination $item.Target
    }
    else {
        $script:Notes.Add(('skipped hooks/{0} — not present in this checkout' -f $item.Name))
    }
}

$launcher = Resolve-PythonLauncher
if (-not $launcher) {
    $script:Notes.Add('python not found on PATH — hook registry rendered with a bare python3 command')
}

if (Test-Path -LiteralPath $hookSource) {
    $rendered = Format-HookRegistry -RegistryPath $hookSource -WrapperPath $hookWrapper -ShellWrapperPath $hookShellWrapper -Launcher $launcher
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
    $script:Notes.Add('skipped hooks/kaios.json — not present in this checkout')
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
    # `python -m kaios` needs the framework directory on PYTHONPATH, because the
    # package lives at .github\kaios rather than beside the repository root. The
    # previous value is restored so this script leaves the session as it found it.
    $previousPythonPath = $env:PYTHONPATH
    Push-Location -LiteralPath $repoRoot
    try {
        $env:KAIOS_HOME = $KaiosHome
        $env:PYTHONPATH = $githubDir
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
        if ($null -eq $previousPythonPath) {
            Remove-Item -LiteralPath 'env:PYTHONPATH' -ErrorAction SilentlyContinue
        }
        else {
            $env:PYTHONPATH = $previousPythonPath
        }
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
