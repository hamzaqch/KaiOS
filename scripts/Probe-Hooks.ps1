<#
.SYNOPSIS
    Fires every registered hook event through the Windows wrapper.

.DESCRIPTION
    For each event in .github/hooks/kaios.json, pipes a sample event object
    into .github/hooks/kaios.ps1 and checks two things: the wrapper exited 0,
    and what it wrote to stdout is parseable JSON. Those are the only two
    promises the chat harness depends on, and a wrapper that breaks either one
    can break a chat session.

    The probe passes before the Python hook package exists. With no runner to
    call, the wrapper falls back to {"continue": true} and exits 0, which is
    the designed behaviour rather than a skipped test.

.EXAMPLE
    pwsh -NoProfile -File scripts/Probe-Hooks.ps1

.NOTES
    Exit codes: 0 every event passed, 1 at least one failed, 2 usage.
#>
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DefaultEvents = @(
    'SessionStart',
    'UserPromptSubmit',
    'PreToolUse',
    'PostToolUse',
    'PreCompact',
    'SubagentStart',
    'SubagentStop',
    'Stop'
)

function Test-WindowsHost {
    [CmdletBinding()]
    param()

    if ($env:OS -eq 'Windows_NT') { return $true }
    if (Test-Path -LiteralPath 'variable:IsWindows') {
        return [bool](Get-Variable -Name 'IsWindows' -ValueOnly)
    }
    return $false
}

function Format-CommandToken {
    [CmdletBinding()]
    param([string]$Token)

    if ($Token -match '\s') { return '"' + $Token + '"' }
    return $Token
}

function Get-PowerShellHostPath {
    [CmdletBinding()]
    param()

    $process = Get-Process -Id $PID
    if ($process.Path) { return $process.Path }
    return [System.Diagnostics.Process]::GetCurrentProcess().MainModule.FileName
}

$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not $repoRoot) { $repoRoot = (Get-Location).Path }
$repoRoot = (Resolve-Path -LiteralPath $repoRoot).Path

$wrapper = Join-Path -Path (Join-Path -Path (Join-Path -Path $repoRoot -ChildPath '.github') -ChildPath 'hooks') -ChildPath 'kaios.ps1'
if (-not (Test-Path -LiteralPath $wrapper)) {
    Write-Error "hook wrapper not found at $wrapper"
    exit 2
}

$registry = Join-Path -Path (Join-Path -Path (Join-Path -Path $repoRoot -ChildPath '.github') -ChildPath 'hooks') -ChildPath 'kaios.json'
$events = $DefaultEvents
if (Test-Path -LiteralPath $registry) {
    try {
        $document = [System.IO.File]::ReadAllText($registry) | ConvertFrom-Json
        $names = @($document.hooks.PSObject.Properties.Name)
        if ($names.Count -gt 0) { $events = $names }
    }
    catch {
        Write-Host ("  could not read {0} — probing the default event list" -f $registry)
    }
}

$hostPath = Get-PowerShellHostPath
$argumentPrefix = '-NoProfile'
if (Test-WindowsHost) {
    $argumentPrefix = '-NoProfile -ExecutionPolicy Bypass'
}

Write-Host ''
Write-Host '════ KaiOS hook probe ════════════════════════'
Write-Host ''
Write-Host ("  wrapper : {0}" -f $wrapper)
Write-Host ("  host    : {0}" -f $hostPath)
Write-Host ''

$rows = New-Object System.Collections.Generic.List[object]
$failures = 0

foreach ($name in $events) {
    $sample = [ordered]@{
        hook_event_name = $name
        tool_name       = 'runCommands'
        tool_input      = [ordered]@{ command = 'git status' }
        prompt          = 'hello'
        cwd             = $repoRoot
    }
    $payload = $sample | ConvertTo-Json -Depth 5 -Compress

    $exitCode = -1
    $stdout = ''
    $note = ''

    try {
        $psi = New-Object System.Diagnostics.ProcessStartInfo
        $psi.FileName = $hostPath
        $psi.Arguments = ("{0} -File {1} {2}" -f $argumentPrefix, (Format-CommandToken -Token $wrapper), $name)
        $psi.WorkingDirectory = $repoRoot
        $psi.UseShellExecute = $false
        $psi.CreateNoWindow = $true
        $psi.RedirectStandardInput = $true
        $psi.RedirectStandardOutput = $true
        $psi.RedirectStandardError = $true

        $proc = [System.Diagnostics.Process]::Start($psi)
        $outTask = $proc.StandardOutput.ReadToEndAsync()
        $errTask = $proc.StandardError.ReadToEndAsync()
        $proc.StandardInput.Write($payload)
        $proc.StandardInput.Close()
        if (-not $proc.WaitForExit(30000)) {
            try { $proc.Kill() } catch { }
            $note = 'timed out'
        }
        else {
            $stdout = $outTask.Result
            $null = $errTask.Result
            $exitCode = $proc.ExitCode
        }
    }
    catch {
        $note = $_.Exception.Message
    }

    $validJson = 'no'
    try {
        if ($stdout) {
            $null = $stdout | ConvertFrom-Json
            $validJson = 'yes'
        }
    }
    catch {
        $validJson = 'no'
        if (-not $note) { $note = 'stdout is not JSON' }
    }

    $passed = ($exitCode -eq 0) -and ($validJson -eq 'yes')
    if (-not $passed) { $failures++ }

    $rows.Add([PSCustomObject]@{
        Event     = $name
        Exit      = $exitCode
        ValidJson = $validJson
        Result    = $(if ($passed) { 'PASS' } else { 'FAIL' })
        Note      = $note
    })
}

$rows | Format-Table -AutoSize | Out-String | Write-Host

if ($failures -gt 0) {
    Write-Host ("FAIL — {0} of {1} event(s) did not satisfy the contract." -f $failures, $rows.Count)
    Write-Host ''
    exit 1
}

Write-Host ("PASS — all {0} event(s) exited 0 with valid JSON on stdout." -f $rows.Count)
Write-Host ''
exit 0
