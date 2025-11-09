#!/bin/sh
set -e

# Optional: print env for debug
echo "[entrypoint] RUN_MODE=${RUN_MODE:-local}"

# (Optional) Run DB migrations if you want (uncomment if alembic configured)
# if [ -n "$DATABASE_URL" ]; then
#   echo "[entrypoint] running alembic migrations"
#   alembic upgrade head || true
# fi

# Replace the current process with whatever command Docker is asked to run
exec "$@"
