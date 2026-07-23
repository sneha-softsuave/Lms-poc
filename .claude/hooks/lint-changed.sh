#!/usr/bin/env bash
# lint-changed.sh — PostToolUse hook on Write|Edit. NON-BLOCKING by contract.
#
# Runs the project's OWN lint command(s) when files in the working tree change.
# The commands are not hardcoded: they are read from the "Lint" row(s) of
# .claude/stack-profile.md, which squad-setup generates per project. That is what
# makes this hook stack-agnostic — the same file works in a Node repo, a Python
# repo, or a Go repo with no edits.
#
# Contract: never blocks the session, always exits 0.
#
# The profile's Commands table looks like:
#   | Purpose        | Command          | Run from |
#   | Lint           | ruff check --fix | .        |
#   | Lint (backend) | make lint        | .        |
#   | Lint (frontend)| npm run lint     | frontend |
#
# Any row whose label STARTS WITH "Lint" is run, so polyglot repos can declare
# one per stack. The changed-file list decides WHETHER a row runs (were any files
# under its directory touched), not what gets passed to it.
#
# Deliberately does NOT append filenames to the command. Real profiles hold
# wrappers — `make lint`, `npm run lint` — where trailing paths are parsed as
# make targets or npm args and break. Running the project's command exactly as
# written is both simpler and correct; whole-project linters are fast enough.
#
# If the profile is missing, or every Lint row is an unfilled placeholder, this
# exits silently. A repo with no resolved lint command is not an error.

set -u

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$REPO_ROOT" || exit 0

PROFILE="$REPO_ROOT/.claude/stack-profile.md"
[ -f "$PROFILE" ] || exit 0

# --- Collect changed files ---------------------------------------------------
# Tracked modifications + staged + untracked, deduped. .claude/ is config, not
# source — never lint the agent's own folder.
CHANGED=$( (git diff --name-only --diff-filter=ACMR;
            git diff --cached --name-only --diff-filter=ACMR;
            git ls-files --others --exclude-standard) 2>/dev/null \
           | sort -u | grep -v '^\.claude/' || true)
[ -n "$CHANGED" ] || exit 0

# --- Run every "Lint*" row whose directory saw a change ----------------------
# Splitting "| Lint | ruff check | . |" on '|' gives $2=label, $3=command, $4=dir.
# Placeholder rows (<cmd>) and empty commands are skipped.
ROWS=$(awk -F'|' '
  {
    key = $2; gsub(/^[ \t]+|[ \t]+$/, "", key)
    if (tolower(key) ~ /^lint/) {
      cmd = $3; gsub(/^[ \t]+|[ \t]+$/, "", cmd); gsub(/^`|`$/, "", cmd)
      dir = $4; gsub(/^[ \t]+|[ \t]+$/, "", dir); gsub(/^`|`$/, "", dir)
      if (cmd != "" && cmd !~ /^</) {
        if (dir == "" || dir ~ /^</) dir = "."
        print dir "\t" cmd
      }
    }
  }
' "$PROFILE")

[ -n "$ROWS" ] || exit 0

while IFS=$'\t' read -r dir cmd; do
  [ -n "$cmd" ] || continue

  # A profile may name the root in prose rather than as a path.
  case "$dir" in
    root|"repo root"|"project root") dir="." ;;
  esac
  [ -d "$dir" ] || dir="."

  # Only run if something under this directory actually changed.
  if [ "$dir" = "." ]; then
    relevant=1
  else
    relevant=0
    while IFS= read -r f; do
      case "$f" in "$dir"/*) relevant=1; break ;; esac
    done <<EOF
$CHANGED
EOF
  fi
  [ "$relevant" = "1" ] || continue

  echo "Linting (${dir}): ${cmd}"
  # Unquoted $cmd on purpose: it carries its own arguments from the profile.
  (cd "$dir" && $cmd 2>&1 | tail -30) || true
done <<EOF
$ROWS
EOF

exit 0
