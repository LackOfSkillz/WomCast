#!/usr/bin/env bash
# Install git hooks for WomCast

set -e

HOOK_DIR=".git/hooks"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing git hooks..."

# Make pre-commit executable
chmod +x "$HOOK_DIR/pre-commit"

echo "✓ Git hooks installed successfully!"
echo ""
echo "The following hooks are now active:"
echo "  - pre-commit: Runs linting and type checks before commit"
echo ""
echo "To bypass hooks (not recommended), use: git commit --no-verify"
