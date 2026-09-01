#!/bin/bash
set -e

echo "=== PHASE 20 PRODUCTION SAFETY VERIFICATION ==="

echo "[1/4] Verifying Production Containers"
docker ps --filter "name=homelab-" --format "ID: {{.ID}} | Name: {{.Names}} | Status: {{.Status}}" > prod_containers_before.txt
cat prod_containers_before.txt

echo "[2/4] Verifying Production Volumes"
docker volume ls --filter "name=postgres_data" --filter "name=minio_data" --filter "name=platform_data" > prod_volumes_before.txt
cat prod_volumes_before.txt

echo "[3/4] Recording Platform Data Size"
if [ -d "/var/lib/auth-service/data" ]; then
    du -sh /var/lib/auth-service/data > prod_data_size_before.txt
    cat prod_data_size_before.txt
else
    echo "/var/lib/auth-service/data not found"
fi

echo "[4/4] Recording Git State"
git rev-parse HEAD > git_state_before.txt
cat git_state_before.txt

echo "=== Verification Base Recorded ==="
