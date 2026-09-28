#!/bin/sh
# POSIX entry point for one KaiOS hook event.
#
# The Copilot CLI hook engine runs the `bash` command line of a registry entry
# on a non-Windows host, which is why this exists beside kaios.ps1. Both
# wrappers keep the same contract: read the JSON event on stdin, forward it to
# `python -m kaios.hooks <Event>` with the package root as the working
# directory, and pass the answer back on stdout unchanged.
#
# The one invariant: always valid JSON on stdout, never a byte on stderr,
# always exit 0. A missing interpreter, a missing package, a crashing hook or a
# hung child all degrade to {"continue": true}, because the Copilot CLI engine
# fails a preToolUse hook CLOSED — an erroring hook there denies the tool call.
# Diagnostics go to $KAIOS_HOME/MEMORY/OBSERVABILITY/hook-errors.log.
#
# Usage: sh kaios.sh sessionStart < event.json
#        KAIOS_HOOKS_DISABLED=1 turns every hook into {"continue": true}.

FALLBACK='{"continue": true}'

# Nothing this script says may reach the harness as stderr.
exec 2>/dev/null

event=$1
kaios_home=${KAIOS_HOME:-$HOME/.kaios}

log_line() {
    [ -n "$1" ] || return 0
    log_dir=$kaios_home/MEMORY/OBSERVABILITY
    mkdir -p "$log_dir" || return 0
    printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$event" "$1" \
        >> "$log_dir/hook-errors.log"
    return 0
}

answer() {
    printf '%s\n' "$1"
    exit 0
}

# A terminal has nothing piped into it; reading would block until EOF.
payload=''
if [ ! -t 0 ]; then
    payload=$(cat)
fi

if [ "$KAIOS_HOOKS_DISABLED" = "1" ]; then
    answer "$FALLBACK"
fi

# The event name becomes an argument to the runner, so accept only a bare
# identifier. Anything else is treated as an unknown event and short-circuits.
case "$event" in
    ""|*[!A-Za-z0-9_]*) answer "$FALLBACK" ;;
esac
case "$event" in
    [A-Za-z]*) ;;
    *) answer "$FALLBACK" ;;
esac

# Where `import kaios` resolves from, in priority order:
#   1. $KAIOS_REPO/.github                (KAIOS_REPO names the checkout root)
#   2. $KAIOS_REPO                        (or it already names the .github dir)
#   3. $KAIOS_HOME/lib                    (package copy Install.ps1 refreshes)
#   4. the directory above this wrapper   (.github itself, since the wrapper
#                                          lives in .github/hooks)
# The whole framework lives under .github, so candidate 4 needs no environment at
# all: the package sits beside this script's parent.
script_dir=$(cd "$(dirname "$0")" && pwd -P)
framework_dir=''
if [ -n "$script_dir" ]; then
    framework_dir=$(cd "$script_dir/.." && pwd -P)
fi

kaios_repo=${KAIOS_REPO:-}
repo_framework=''
if [ -n "$kaios_repo" ]; then
    repo_framework=$kaios_repo/.github
fi

package_root=''
for candidate in "$repo_framework" "$kaios_repo" "$kaios_home/lib" "$framework_dir"; do
    [ -n "$candidate" ] || continue
    if [ -f "$candidate/kaios/__init__.py" ]; then
        package_root=$candidate
        break
    fi
done
if [ -z "$package_root" ]; then
    log_line 'kaios package not found: set KAIOS_REPO or re-run Install.ps1'
    answer "$FALLBACK"
fi

python_bin=''
for name in python3 python; do
    if command -v "$name" >/dev/null 2>&1; then
        python_bin=$(command -v "$name")
        break
    fi
done
if [ -z "$python_bin" ]; then
    log_line 'no python interpreter found on PATH'
    answer "$FALLBACK"
fi

PYTHONPATH=$package_root${PYTHONPATH:+:$PYTHONPATH}
PYTHONIOENCODING=utf-8
PYTHONUTF8=1
export PYTHONPATH PYTHONIOENCODING PYTHONUTF8

err_file=$(mktemp) || err_file=/tmp/kaios-hook-$$.err
timeout_bin=''
if command -v timeout >/dev/null 2>&1; then
    timeout_bin=$(command -v timeout)
fi

if [ -n "$timeout_bin" ]; then
    out=$(printf '%s' "$payload" | (cd "$package_root" && "$timeout_bin" 18 \
        "$python_bin" -m kaios.hooks "$event") 2>"$err_file")
else
    out=$(printf '%s' "$payload" | (cd "$package_root" && \
        "$python_bin" -m kaios.hooks "$event") 2>"$err_file")
fi
status=$?

child_stderr=$(cat "$err_file")
rm -f "$err_file"
log_line "$child_stderr"

if [ "$status" -ne 0 ]; then
    log_line "runner exited $status"
    answer "$FALLBACK"
fi
if [ -z "$out" ]; then
    answer "$FALLBACK"
fi
answer "$out"
