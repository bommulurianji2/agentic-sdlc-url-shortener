#!/bin/sh
set -e

# Idempotent - safe to run on every container start (Alembic no-ops if
# already at head).
alembic upgrade head

exec "$@"
