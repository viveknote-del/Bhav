#!/usr/bin/env bash
set -euo pipefail

# AI Starter Kit — Project setup script
# Run this once after copying the template to a new project directory.

echo "=== AI Starter Kit — Project Setup ==="
echo ""

# Prompt for project details
read -p "Project name (lowercase, hyphens OK, e.g. 'my-app'): " PROJECT_NAME
read -p "Project display name (e.g. 'My App'): " PROJECT_DISPLAY_NAME
read -p "Project description (one sentence): " PROJECT_DESCRIPTION
read -p "Database name (e.g. 'myapp'): " DB_NAME
read -p "GitHub repo (e.g. 'username/repo-name'): " GITHUB_REPO

TODAY=$(date +%Y-%m-%d)

echo ""
echo "Replacing placeholders..."

# Files to process
FILES=(
  "CLAUDE.md"
  "ARCHITECTURE.md"
  "README.md"
  "DOCS/KANBAN.md"
  "DOCS/BUGS.md"
  "DOCS/DEFERRED.md"
  "DOCS/BACKLOG.md"
  "DOCS/DECISIONS.md"
  "DOCS/DEPLOYMENT.md"
  "DOCS/REGRESSION.md"
  "plans/forward.md"
  "apps/web/package.json"
  "apps/web/src/app/layout.tsx"
  "apps/web/src/app/page.tsx"
  "packages/shared-types/package.json"
  "packages/database/package.json"
  "packages/database/migrations/0000_initial.sql"
  "package.json"
  "docker-compose.yml"
  ".env.example"
  "services/api/main.py"
  "services/api/config.py"
)

for file in "${FILES[@]}"; do
  if [ -f "$file" ]; then
    sed -i.bak \
      -e "s/{{PROJECT_NAME}}/$PROJECT_NAME/g" \
      -e "s/{{PROJECT_DISPLAY_NAME}}/$PROJECT_DISPLAY_NAME/g" \
      -e "s/{{PROJECT_DESCRIPTION}}/$PROJECT_DESCRIPTION/g" \
      -e "s/{{DB_NAME}}/$DB_NAME/g" \
      -e "s/{{GITHUB_REPO}}/$GITHUB_REPO/g" \
      -e "s/{{DATE}}/$TODAY/g" \
      "$file"
    rm -f "$file.bak"
    echo "  ✓ $file"
  fi
done

# Initialize git if not already a repo
if [ ! -d ".git" ]; then
  echo ""
  echo "Initializing git repository..."
  git init
  git add -A
  git commit -m "chore: initialize $PROJECT_DISPLAY_NAME from ai-starter template"
  echo "  ✓ Git initialized"
fi

echo ""
echo "=== Setup complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env.local and fill in your values"
echo "  2. Run: docker compose up -d"
echo "  3. Run: pnpm install"
echo "  4. Run: cd apps/web && pnpm dev"
echo "  5. Open Claude Code and type /next to see what to build first"
echo ""
echo "To build the first step:"
echo '  /pipeline "Step 0 — Project Scaffold & Setup"'
