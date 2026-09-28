<#
.SYNOPSIS
    Rejects PowerShell syntax that Windows PowerShell 5.1 cannot run.

.DESCRIPTION
    Parses every .ps1 file in the repository with the PowerShell language
    parser, then inspects the token stream for constructs that only exist in
    PowerShell 7 and later. A file that parses cleanly under a newer host can
    still be a hard syntax error on 5.1, which is the only host the target
    machines have, so both checks run.

    Rejected constructs: the null-coalescing operators ?? and ??=, the ternary
    operator ? :, and the pipeline chain operators && and ||.

.PARAMETER Path
    Directory to scan. Defaults to the repository root, which is two levels above
    this script: every .ps1 KaiOS ships now lives under .github.

.EXAMPLE
    pwsh -NoProfile -File .github/scripts/Test-PS51.ps1

.NOTES
    Exit codes: 0 clean, 1 findings, 2 usage.
#>
[CmdletBinding()]
param(
    [string]$Path
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$BannedKinds = @{
    'QuestionQuestion'       = 'null-coalescing operator ??'
    'QuestionQuestionEquals' = 'null-coalescing assignment ??='
    'QuestionMark'           = 'ternary operator ? :'
    'AndAnd'                 = 'pipeline chain operator &&'
    'OrOr'                   = 'pipeline chain operator ||'
}

if (-not $Path) {
    $Path = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}
if (-not $Path) {
    $Path = (Get-Location).Path
}
if (-not (Test-Path -LiteralPath $Path)) {
    Write-Error "no such directory: $Path"
    exit 2
}
$root = (Resolve-Path -LiteralPath $Path).Path

$scripts = @(
    Get-ChildItem -LiteralPath $root -Recurse -Filter '*.ps1' -File -Force |
        Where-Object { $_.FullName -notmatch '(\\|/)\.git(\\|/)' } |
        Sort-Object FullName
)

if ($scripts.Count -eq 0) {
    Write-Host "no .ps1 files under $root"
    exit 0
}

$findings = New-Object System.Collections.Generic.List[object]
$results = New-Object System.Collections.Generic.List[object]

foreach ($file in $scripts) {
    $relative = $file.FullName.Substring($root.Length).TrimStart([char[]]@('\', '/'))
    $issues = 0

    $tokens = $null
    $errors = $null
    $null = [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$errors)

    if ($errors) {
        foreach ($parseError in $errors) {
            $issues++
            $findings.Add([PSCustomObject]@{
                File    = $relative
                Line    = $parseError.Extent.StartLineNumber
                Problem = 'parse error'
                Detail  = $parseError.Message
            })
        }
    }

    if ($tokens) {
        foreach ($token in $tokens) {
            $kind = [string]$token.Kind
            if ($BannedKinds.ContainsKey($kind)) {
                $issues++
                $findings.Add([PSCustomObject]@{
                    File    = $relative
                    Line    = $token.Extent.StartLineNumber
                    Problem = 'not valid on 5.1'
                    Detail  = $BannedKinds[$kind]
                })
            }
        }
    }

    $status = 'OK'
    if ($issues -gt 0) {
        $status = ("{0} issue(s)" -f $issues)
    }
    $results.Add([PSCustomObject]@{
        File   = $relative
        Result = $status
    })
}

Write-Host ''
Write-Host '════ KaiOS PowerShell 5.1 syntax check ═══════'
Write-Host ''
$results | Format-Table -AutoSize | Out-String | Write-Host

if ($findings.Count -gt 0) {
    Write-Host 'findings:'
    $findings | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host ("FAIL — {0} finding(s) across {1} file(s)." -f $findings.Count, $scripts.Count)
    Write-Host ''
    exit 1
}

Write-Host ("PASS — {0} file(s) are Windows PowerShell 5.1 compatible." -f $scripts.Count)
Write-Host ''
exit 0
