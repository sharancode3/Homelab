#!/bin/bash
set -e

echo "=== ZERO-LOAD VALIDATION GATE ==="

echo "[1/4] Bringing up test environment..."
docker compose -p phase20test -f tests/performance/docker-compose.test.yml up -d

echo "Waiting for test Caddy to initialize..."
sleep 15

echo "[2/4] Validating Test HTTPS Ingress"
curl -k --max-time 10 -s -o /dev/null -w "%{http_code}" https://localhost:8443/api/v1/baas/projects/ > ingress_status.txt
STATUS=$(cat ingress_status.txt)
if [ "$STATUS" == "401" ] || [ "$STATUS" == "200" ]; then
    echo "Test Ingress Reachable: HTTP $STATUS (Backend connected)"
else
    echo "FAILED: Expected 401 or 200 from Auth backend, got $STATUS"
    exit 1
fi

echo "[3/4] Verifying Test Container Separation"
docker ps --filter "name=homelab-" --format "{{.Names}}" | sort > all_containers.txt
if grep -q "homelab-auth$" all_containers.txt && grep -q "homelab-auth-test$" all_containers.txt; then
    echo "Both production and test containers are running."
else
    echo "FAILED: Container isolation mismatch."
    cat all_containers.txt
    exit 1
fi

echo "[4/4] Verifying Production State"
./tests/performance/verify_safety.sh

echo "=== ZERO-LOAD VALIDATION PASSED ==="
