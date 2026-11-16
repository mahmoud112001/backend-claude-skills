#!/usr/bin/env bash
# Run the backend design team end to end on a fixture, in a throwaway copy.
# Usage: run_fixture.sh <fixture-dir> <work-dir> <git|none> <prompt-file> <log-path-without-ext>
#   First call creates <work-dir>: copies the fixture, installs ONLY this pack's design skills and
#   agents into <work-dir>/.claude/, and (git) makes one commit. Later calls reuse it (resume).
# Each call is a fresh headless session (like /clear): state must come from <out>/00-state.md.
# Needs: claude CLI, python3 on PATH (put a shim first in PATH if your Python has another name).
set -euo pipefail
export MSYS_NO_PATHCONV=1   # Git Bash on Windows would otherwise rewrite "/backend-design-team" into a path
PACK=$(cd "$(dirname "$0")/.." && pwd)
FIX=$1; WORK=$2; VCS=$3; PROMPT=$4; LOG=$5
SKILLS="backend-design-team project-understanding ddd-strategic ddd-tactical db-design-erd design-diagrams api-endpoints design-review-fix design-docs-organizer"
if [ ! -d "$WORK" ]; then
  mkdir -p "$WORK/.claude/skills" "$WORK/.claude/agents"
  cp -r "$FIX"/. "$WORK"/
  for s in $SKILLS; do cp -r "$PACK/skills/$s" "$WORK/.claude/skills/"; done
  cp "$PACK"/agents/*.md "$WORK/.claude/agents/"
  if [ "$VCS" = git ]; then
    (cd "$WORK" && git init -q && git add -A && git -c user.name=fixture -c user.email=fixture@example.invalid commit -qm fixture)
  fi
fi
cd "$WORK"
start=$(date +%s)
claude -p "$(cat "$PROMPT")" --model sonnet --setting-sources project --permission-mode acceptEdits \
  --allowedTools Read Glob Grep Write Edit Agent Skill "Bash(python3 *)" "Bash(python *)" \
  "Bash(git rev-parse*)" "Bash(git status*)" "Bash(git ls-files*)" \
  --output-format stream-json --verbose > "$LOG.jsonl" 2> "$LOG.err" || echo "claude exited $?" >> "$LOG.err"
echo "seconds=$(( $(date +%s) - start ))" >> "$LOG.err"
