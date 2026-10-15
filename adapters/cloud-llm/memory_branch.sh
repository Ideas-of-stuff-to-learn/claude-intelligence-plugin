#!/bin/sh
# memory_branch.sh — Helper for Mode A (repo-access cloud LLM)
# Run this to set up or update the ci/memory branch structure.
#
# Usage:
#   sh memory_branch.sh setup      # create ci/memory/main branch from current HEAD
#   sh memory_branch.sh new         # create today's session branch
#   sh memory_branch.sh merge        # merge today's branch into ci/memory/main
#   sh memory_branch.sh status       # show memory branch status

set -e

DATE=$(date +%Y-%m-%d)
SESSION_BRANCH="ci/memory/$DATE"
MEMORY_MAIN="ci/memory/main"

case "$1" in
  setup)
    echo "Setting up memory branch structure..."
    git checkout -b "$MEMORY_MAIN" 2>/dev/null || git checkout "$MEMORY_MAIN"
    git checkout -
    echo "✓ Created $MEMORY_MAIN"
    echo "Run 'sh memory_branch.sh new' at the start of each session."
    ;;

  new)
    echo "Creating session branch: $SESSION_BRANCH"
    git fetch origin "$MEMORY_MAIN" 2>/dev/null || true
    git checkout "$MEMORY_MAIN" 2>/dev/null || true
    git checkout -b "$SESSION_BRANCH" 2>/dev/null || git checkout "$SESSION_BRANCH"
    echo "✓ On branch $SESSION_BRANCH"
    echo "Work here. At session end, run: sh memory_branch.sh merge"
    ;;

  merge)
    echo "Merging $SESSION_BRANCH into $MEMORY_MAIN..."
    CURRENT=$(git rev-parse --abbrev-ref HEAD)
    if [ "$CURRENT" != "$SESSION_BRANCH" ]; then
      git checkout "$SESSION_BRANCH" 2>/dev/null
    fi
    git checkout "$MEMORY_MAIN"
    git merge --no-ff "$SESSION_BRANCH" -m "Memory: session $DATE"
    echo "✓ Merged $SESSION_BRANCH into $MEMORY_MAIN"
    echo "Push with: git push origin $MEMORY_MAIN"
    ;;

  status)
    echo "Memory branches:"
    git branch -a | grep 'ci/memory' || echo "  (none found)"
    ;;

  *)
    echo "Usage: $0 setup|new|merge|status"
    exit 1
    ;;
esac
