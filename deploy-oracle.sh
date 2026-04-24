#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "UYARI: .env dosyası bulunamadı, .env.example kopyalandı."
  echo "Lütfen .env dosyasını düzenleyip gerçek değerleri girin."
  exit 1
fi

docker compose --env-file .env -f docker-compose.oracle.yml config >/dev/null
docker compose --env-file .env -f docker-compose.oracle.yml up -d --build
docker compose --env-file .env -f docker-compose.oracle.yml ps

echo
echo "Oracle deployment is up."
echo "Open: https://${DOMAIN_OR_PUBLIC_IP}/"
