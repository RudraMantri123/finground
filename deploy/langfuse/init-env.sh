#!/usr/bin/env sh
# Generate deploy/langfuse/.env with fresh random local-only secrets.
# Refuses to overwrite an existing .env (that would orphan the data volumes,
# whose passwords were set on first start).
set -eu
cd "$(dirname "$0")"
if [ -e .env ]; then
  echo "deploy/langfuse/.env already exists; not overwriting." >&2
  exit 1
fi
rnd() { openssl rand -hex "$1"; }
umask 077
cat > .env <<ENV
LANGFUSE_PORT=3100
LANGFUSE_MINIO_PORT=9190
POSTGRES_PASSWORD=$(rnd 24)
CLICKHOUSE_PASSWORD=$(rnd 24)
REDIS_AUTH=$(rnd 24)
MINIO_ROOT_PASSWORD=$(rnd 24)
NEXTAUTH_SECRET=$(rnd 32)
SALT=$(rnd 32)
ENCRYPTION_KEY=$(rnd 32)
LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-lf-$(rnd 16)
LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-lf-$(rnd 16)
LANGFUSE_INIT_USER_EMAIL=admin@finground.local
LANGFUSE_INIT_USER_PASSWORD=$(rnd 12)
ENV
echo "wrote deploy/langfuse/.env (mode 600)"
