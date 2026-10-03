#!/usr/bin/env bash
# =============================================================================
# Create an Alembic migration with a descriptive, auto-slugged revision id.
#
#   ./scripts/create_migration.sh "add citation logs"
#   make migration msg="add citation logs"     # same thing, inside Docker
# =============================================================================
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "usage: $0 <migration message>" >&2
    exit 1
fi

MESSAGE="$*"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"

cd "$BACKEND_DIR"

# Prefer an active virtualenv, fall back to the container/system alembic.
if [[ -x ".venv/bin/alembic" ]]; then
    ALEMBIC=".venv/bin/alembic"
else
    ALEMBIC="alembic"
fi

echo "==> Generating migration: ${MESSAGE}"
"$ALEMBIC" revision --autogenerate -m "${MESSAGE}"

echo "==> Review the generated file in migrations/versions/ before committing."
echo "    - Ensure CREATE EXTENSION statements are present for new extensions."
echo "    - Verify downgrade() really reverses upgrade()."
