#!/bin/bash

# Script to gradually improve code quality
# Usage: ./scripts/lint-progress.sh [file_or_directory]

echo "🔍 Code Quality Improvement Script"
echo "================================="

if [ $# -eq 0 ]; then
    echo "Usage: $0 [file_or_directory]"
    echo "Example: $0 app/core/agents/workflows/auto_response/workflow.py"
    echo "Example: $0 app/core/agents/"
    exit 1
fi

TARGET="$1"

echo "📁 Target: $TARGET"
echo ""

# Check if target exists
if [ ! -e "$TARGET" ]; then
    echo "❌ Error: $TARGET does not exist"
    exit 1
fi

echo "🔧 Running pre-commit hooks on $TARGET..."
echo ""

# Run pre-commit on the specific file/directory
poetry run pre-commit run --files "$TARGET"

echo ""
echo "✅ Pre-commit check completed!"
echo ""
echo "💡 Tips for gradual improvement:"
echo "   1. Fix one file at a time"
echo "   2. Start with the most critical files"
echo "   3. Use 'git commit --no-verify' to bypass if needed"
echo "   4. Gradually enable more pylint rules in .pylintrc"
echo ""
echo "📊 To see all linting issues: poetry run pylint $TARGET"
echo "🎯 To fix specific issues: poetry run pre-commit run --files $TARGET"
