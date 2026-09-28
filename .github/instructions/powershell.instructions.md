---
name: powershell
description: Rules for every .ps1 — Windows PowerShell 5.1 syntax only, strict mode, real exit codes, no newer-only tokens.
applyTo: "**/*.ps1"
version: 1.0.0
last_updated: 2026-09-28T00:00:00Z
convention: kaios-freshness-v1
---

# PowerShell

## 5.1 is the target, not a fallback

Every script must run on **Windows PowerShell 5.1**, which is what a work machine has and what nobody can upgrade without a ticket. Newer PowerShell may be used to test, but a script that only runs there is broken.

Banned tokens — each one parses on newer versions and is a syntax error on 5.1:

| Banned | Use instead |
|---|---|
| `??` and `??=` | `if ($null -eq $x) { $x = $default }` |
| `? :` ternary | a full `if`/`else` |
| `&&` and `\|\|` between statements | separate statements with an explicit `if ($LASTEXITCODE -ne 0)` check |
| `-not` chained as `!` on a pipeline | `-not (...)` |
| `Get-Error`, `Test-Json`, `ConvertFrom-Json -AsHashtable` | 5.1 equivalents, or do it in Python |
| `foreach -Parallel`, `ForEach-Object -Parallel` | a plain loop |
| `$PSStyle`, `Join-String`, `Get-Uptime` | none of these exist on 5.1 |

`.github/scripts/Test-PS51.ps1` runs the parser with these tokens banned. A hit fails the build.

## Every script starts the same way

```powershell
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Path,
    [switch]$WhatIfOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
```

`Set-StrictMode` catches the typo'd variable that otherwise evaluates to `$null` and silently does nothing. `$ErrorActionPreference = 'Stop'` makes a cmdlet failure actually stop instead of writing to the error stream and continuing.

## Exit codes

A script that fails must exit non-zero. This is the single most common defect in installer scripts, because PowerShell's default is to keep going and exit 0.

```powershell
try {
    # work
    exit 0
}
catch {
    Write-Error $_.Exception.Message
    exit 1
}
```

After calling an external executable, check `$LASTEXITCODE` explicitly. A cmdlet's `$ErrorActionPreference` does not apply to `git`, `python`, or any other `.exe`.

## Paths

Never hard-code a user directory. Use `$env:USERPROFILE`, `$env:KAIOS_HOME`, `$PSScriptRoot`, or a parameter. `$PSScriptRoot` is how a script finds its own repository, and it is right even when the session opened somewhere else.

`Join-Path` for composition, never string concatenation, because a path with a space is a path that breaks a concatenated string.

Quote every path that reaches an external command. `& python -m kaios @args` with an array is safer than building one command line.

## Idempotence

An installer runs twice. The second run must change nothing and still exit 0. Test for presence before creating, compare before copying, and say what was skipped rather than silently doing it again.

`New-Item -ItemType Directory -Force` is safe. Overwriting a file that already exists is not — if a target file exists and did not come from this script, leave it and report it.

## Output

`Write-Host` for progress a human reads. `Write-Output` only for the value the script returns, because anything on the output stream becomes the return value and pollutes a caller's pipeline. `Write-Error` for failures. Never `Write-Host` something a caller needs to parse — print JSON on the output stream for that.

## Hook wrappers specifically

The wrapper is thin on purpose: read all of stdin, pass it to Python, pass Python's stdout back unchanged, and exit with Python's exit code. No parsing, no logic, no formatting. Every hook rule lives in Python so it is testable without a Windows session.

Read stdin as raw text with `[Console]::In.ReadToEnd()` and do not let PowerShell reinterpret it as objects.
