#!/bin/sh
# Applies database migrations, then starts the server (or whatever command was given).
# With several replicas, run migrations as a one-off job instead and start the replicas with RUN_MIGRATIONS=false.
set -e
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Applying database migrations..."
    alembic upgrade head
fi
exec "$@"
