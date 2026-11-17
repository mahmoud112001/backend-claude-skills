#!/usr/bin/env bash
# Install the backend skills pack by COPYING (never symlinking) its skills and agents.
#
# Usage: scripts/install.sh [--project [DIR] | --user] [--apply]
#   --project [DIR]  install into DIR/.claude/ (default: ./.claude/ of the current folder)
#   --user           install into ~/.claude/ (every project on this machine)
#   --apply          really copy. Without it, this is a dry run that only prints the plan.
# What is copied: skills/<name>/ -> <target>/skills/<name>/, agents/*.md -> <target>/agents/.
# Never copied: _work/, _quarantine/, tests/, scripts/, __pycache__/.
# A skill or agent that already exists and differs is MOVED to
# <target>/.backend-skills-pack-backup/<timestamp>/ first, so nothing is lost.
# Undo: delete the installed names (listed in <target>/.backend-skills-pack-installed.txt)
# and move the backup folders back. No network, no hooks, no settings changes.
set -euo pipefail

PACK=$(cd "$(dirname "$0")/.." && pwd)
TARGET="$PWD/.claude"; APPLY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --project) if [ $# -gt 1 ] && [ "${2#--}" = "$2" ]; then TARGET="$(cd "$2" && pwd)/.claude"; shift; fi ;;
    --user) TARGET="$HOME/.claude" ;;
    --apply) APPLY=1 ;;
    -h|--help) sed -n '2,14p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (see --help)" >&2; exit 2 ;;
  esac
  shift
done

STAMP=$(date +%Y%m%d-%H%M%S)
BACKUP="$TARGET/.backend-skills-pack-backup/$STAMP"
LIST="$TARGET/.backend-skills-pack-installed.txt"
counts_new=0; counts_same=0; counts_changed=0

same() {  # same SRC DEST: 0 when identical, ignoring __pycache__
  diff -rq -x __pycache__ "$1" "$2" >/dev/null 2>&1
}

copy_dir() {  # copy_dir SRC_PARENT NAME DEST_PARENT, without __pycache__
  mkdir -p "$3"
  (cd "$1" && tar --exclude=__pycache__ -cf - "$2") | (cd "$3" && tar -xf -)
}

plan() {  # plan KIND NAME SRC DEST
  local kind=$1 name=$2 src=$3 dest=$4 state
  if [ ! -e "$dest" ]; then state=NEW; counts_new=$((counts_new + 1))
  elif same "$src" "$dest"; then state=SAME; counts_same=$((counts_same + 1))
  else state=CHANGED; counts_changed=$((counts_changed + 1)); fi
  printf '%-8s %-6s %s\n' "$state" "$kind" "$name"
  [ "$APPLY" = 1 ] || return 0
  [ "$state" = SAME ] && { echo "$kind $name" >> "$LIST"; return 0; }
  if [ "$state" = CHANGED ]; then
    mkdir -p "$BACKUP/$kind"
    mv "$dest" "$BACKUP/$kind/"
  fi
  if [ "$kind" = skill ]; then copy_dir "$PACK/skills" "$name" "$TARGET/skills"
  else mkdir -p "$TARGET/agents"; cp "$src" "$dest"; fi
  echo "$kind $name" >> "$LIST"
}

echo "pack:   $PACK"
echo "target: $TARGET"
[ "$APPLY" = 1 ] && { mkdir -p "$TARGET"; : > "$LIST"; } || echo "mode:   DRY RUN (nothing is written; add --apply)"
for d in "$PACK"/skills/*/; do
  n=$(basename "$d"); plan skill "$n" "$PACK/skills/$n" "$TARGET/skills/$n"
done
for f in "$PACK"/agents/*.md; do
  n=$(basename "$f"); plan agent "$n" "$f" "$TARGET/agents/$n"
done
echo "new: $counts_new  same: $counts_same  changed: $counts_changed"
if [ "$APPLY" = 1 ]; then
  echo "installed list: $LIST"
  [ "$counts_changed" -gt 0 ] && echo "replaced copies were moved to: $BACKUP"
  echo "Start a new Claude Code session (or /clear) to load them."
fi
