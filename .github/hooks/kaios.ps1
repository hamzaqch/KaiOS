<#
.SYNOPSIS
    Windows entry point for one KaiOS hook event.

.DESCRIPTION
    The chat harness pipes a JSON event on stdin and reads a JSON decision on
    stdout. All hook logic lives in Python; this wrapper only locates an
    interpreter, forwards stdin to `python -m kaios.hooks <Event>` with the
    repository root as the working directory, and passes the answer back
    unchanged.

    The one invariant: this script always writes valid JSON and always exits 0.
    A missing interpreter, a missing package, a crashing hook, or a hung child
    all degrade to {"continue": true} so that a broken hook can never break a
    chat session.

.PARAMETER Event
    The hook event name, for example SessionStart or PreToolUse.

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File kaios.ps1 SessionStart < event.json

.NOTES
    Windows PowerShell 5.1 compatible. No null-coalescing, no ternary, no
    statement chaining, no cmdlets newer than 5.1.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Event
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$FallbackJson = '{"continue": true}'
$ChildTimeoutMs = 18000

function Get-KaiosHome {
    [CmdletBinding()]
    param()
    if ($env:KAIOS_HOME) { return $env:KAIOS_HOME }
    return (Join-Path $HOME '.kaios')
}

function Write-HookLog {
    # Errors never go to the console: a harness that sees stderr may treat the
    # hook as failed and fail closed. They go to a log file under KAIOS_HOME.
    [CmdletBinding()]
    param([string]$Text)
    if ([string]::IsNullOrWhiteSpace($Text)) { return }
    try {
        $dir = Join-Path (Get-KaiosHome) 'MEMORY\OBSERVABILITY'
        if (-not (Test-Path -LiteralPath $dir)) {
            New-Item -ItemType Directory -Force -Path $dir | Out-Null
        }
        $line = (Get-Date -Format 'o') + ' ' + $Event + ' ' + $Text.Trim()
        Add-Content -LiteralPath (Join-Path $dir 'hook-errors.log') -Value $line -Encoding UTF8
    }
    catch { }
}

function Resolve-PackageRoot {
    # Where `import kaios` resolves from, in priority order:
    #   1. $env:KAIOS_REPO                      (set by Install.ps1)
    #   2. <KAIOS_HOME>\lib                     (package copy made by Install.ps1)
    #   3. the repo this wrapper lives in       (the KaiOS checkout itself)
    [CmdletBinding()]
    param([string]$RepoRoot)
    $candidates = @()
    if ($env:KAIOS_REPO) { $candidates += $env:KAIOS_REPO }
    $candidates += (Join-Path (Get-KaiosHome) 'lib')
    if ($RepoRoot) { $candidates += $RepoRoot }
    foreach ($candidate in $candidates) {
        if (Test-Path -LiteralPath (Join-Path (Join-Path $candidate 'kaios') '__init__.py')) {
            return $candidate
        }
    }
    return $null
}

function Write-HookResult {
    [CmdletBinding()]
    param([string]$Text)

    if ([string]::IsNullOrWhiteSpace($Text)) {
        [Console]::Out.WriteLine($FallbackJson)
        return
    }
    [Console]::Out.Write($Text)
    if (-not $Text.EndsWith("`n")) {
        [Console]::Out.WriteLine('')
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

function Format-ArgumentToken {
    [CmdletBinding()]
    param([string]$Token)

    if ($Token -match '\s') {
        return '"' + $Token + '"'
    }
    return $Token
}

$payload = ''
try {
    $payload = [Console]::In.ReadToEnd()
}
catch {
    $payload = ''
}
if (-not $payload) {
    $payload = '{}'
}

if ($env:KAIOS_HOOKS_DISABLED -eq '1') {
    Write-HookResult -Text $FallbackJson
    exit 0
}

# The event name becomes part of a command line, so accept only a bare
# identifier. Anything else is treated as an unknown event and short-circuits.
if ($Event -notmatch '^[A-Za-z][A-Za-z0-9_]*$') {
    Write-HookResult -Text $FallbackJson
    exit 0
}

try {
    $scriptDir = $PSScriptRoot
    if (-not $scriptDir) {
        $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
    }
    $repoRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)
    if (-not $repoRoot) {
        $repoRoot = (Get-Location).Path
    }

    $launcher = Resolve-PythonLauncher
    if (-not $launcher) {
        Write-HookLog -Text 'no python interpreter found on PATH'
        Write-HookResult -Text $FallbackJson
        exit 0
    }

    $packageRoot = Resolve-PackageRoot -RepoRoot $repoRoot
    if (-not $packageRoot) {
        Write-HookLog -Text 'kaios package not found: set KAIOS_REPO or re-run Install.ps1'
        Write-HookResult -Text $FallbackJson
        exit 0
    }

    $tokens = @()
    foreach ($item in $launcher.Prefix) {
        $tokens += (Format-ArgumentToken -Token $item)
    }
    $tokens += '-m'
    $tokens += 'kaios.hooks'
    $tokens += $Event

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $launcher.Exe
    $psi.Arguments = ($tokens -join ' ')
    $psi.WorkingDirectory = $packageRoot
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    try {
        $psi.StandardOutputEncoding = New-Object System.Text.UTF8Encoding($false)
        $psi.StandardErrorEncoding = New-Object System.Text.UTF8Encoding($false)
    }
    catch {
        # Older hosts may not expose the encoding properties; the default is fine.
    }
    $psi.EnvironmentVariables['PYTHONIOENCODING'] = 'utf-8'
    $existingPath = $env:PYTHONPATH
    if ($existingPath) {
        $psi.EnvironmentVariables['PYTHONPATH'] = $packageRoot + [System.IO.Path]::PathSeparator + $existingPath
    }
    else {
        $psi.EnvironmentVariables['PYTHONPATH'] = $packageRoot
    }
    $psi.EnvironmentVariables['PYTHONUTF8'] = '1'
    if ($env:KAIOS_HOME) {
        $psi.EnvironmentVariables['KAIOS_HOME'] = $env:KAIOS_HOME
    }

    $proc = [System.Diagnostics.Process]::Start($psi)

    # Read both streams asynchronously so a chatty child cannot deadlock on a
    # full pipe buffer while we are still writing its stdin.
    $outTask = $proc.StandardOutput.ReadToEndAsync()
    $errTask = $proc.StandardError.ReadToEndAsync()

    $proc.StandardInput.Write($payload)
    $proc.StandardInput.Close()

    if (-not $proc.WaitForExit($ChildTimeoutMs)) {
        try { $proc.Kill() } catch { }
        Write-HookResult -Text $FallbackJson
        exit 0
    }

    $stdout = $outTask.Result
    $stderr = $errTask.Result

    if ($stderr) {
        Write-HookLog -Text $stderr
    }
    if ($proc.ExitCode -ne 0) {
        Write-HookResult -Text $FallbackJson
        exit 0
    }

    Write-HookResult -Text $stdout
    exit 0
}
catch {
    Write-HookLog -Text $_.Exception.Message
    Write-HookResult -Text $FallbackJson
    exit 0
}
