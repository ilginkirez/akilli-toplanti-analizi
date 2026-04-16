#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f compose.oracle.env ]; then
  cp compose.oracle.env.example compose.oracle.env
fi

docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml config >/dev/null
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml up -d --build
docker compose --env-file compose.oracle.env -f docker-compose.oracle.yml ps

echo
echo "Oracle deployment is up."
echo "Open: https://${DOMAIN_OR_PUBLIC_IP}/"
