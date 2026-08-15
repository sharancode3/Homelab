# Phase 19 Chaos Runbook (Manual Infrastructure Testing)

This runbook contains destructive infrastructure tests for Phase 19. It is designed to verify system resilience, recovery, and audit trails when the underlying infrastructure fails.

> [!WARNING]
> DO NOT hardcode container or network names. Always run the discovery commands to find the dynamic names created by Docker Compose.
> Execute Scenario 2 (Docker Unavailable) absolutely LAST, as it brings down the entire stack.

---

## Pre-requisites

Ensure the application is running via Docker Compose:
```bash
docker-compose ps
```

Verify current restart policies for the containers. Do NOT assume `restart: unless-stopped`. Record the output:
```bash
docker inspect homelab-auth --format '{{.HostConfig.RestartPolicy.Name}}'
docker inspect homelab-postgres --format '{{.HostConfig.RestartPolicy.Name}}'
docker inspect homelab-caddy --format '{{.HostConfig.RestartPolicy.Name}}'
```

Establish your Caddy ingress URL (e.g., `https://your-tunnel-domain.com`). **Do NOT use `http://localhost:8000`** as Phase 17 removed the host port mapping. All API verification must go through the Caddy ingress.

Export your ingress URL and an API key/token (if you have one) for easy testing:
```bash
export API_URL="https://<YOUR_CADDY_INGRESS_DOMAIN>"
export DEV_TOKEN="<YOUR_DEVELOPER_TOKEN>"
```

---

## Scenario 1: Database Unavailable

**Goal**: Verify that when PostgreSQL fails, the API gracefully handles the connection drop, and recovers automatically when the DB returns. We use an authenticated, DB-dependent route to ensure the test is valid.

1. **Discover**: Find the database container name.
   ```bash
   docker ps -f name=postgres -q | xargs docker inspect --format='{{.Name}}'
   ```
2. **Pre-Check (DB Healthy)**: Execute a database-dependent operation (e.g., list projects).
   ```bash
   curl -i -H "Authorization: Bearer $DEV_TOKEN" $API_URL/api/v1/baas/projects/
   ```
   *Expected: 200 OK with a list of projects.*
3. **Inject Failure**: Stop the actual PostgreSQL container.
   ```bash
   docker stop <DISCOVERED_PG_CONTAINER>
   ```
4. **Verify Expected Error**: Re-run the DB-dependent request. You should receive a 500 error indicating a database connection issue.
   ```bash
   curl -i -H "Authorization: Bearer $DEV_TOKEN" $API_URL/api/v1/baas/projects/
   ```
5. **Recover**: Start the container.
   ```bash
   docker start <DISCOVERED_PG_CONTAINER>
   ```
6. **Verify Recovery**: Re-run the DB-dependent request. It should succeed again.
   ```bash
   curl -i -H "Authorization: Bearer $DEV_TOKEN" $API_URL/api/v1/baas/projects/
   ```

---

## Scenario 3: Network Disappears

**Goal**: Verify behavior when the API backend becomes unreachable from Caddy.

1. **Discover**: Find the Caddy container, the backend API container (`homelab-auth`), and their shared network.
   ```bash
   # Find the backend container name
   docker ps -f name=auth -q | xargs docker inspect --format='{{.Name}}'
   
   # Discover its network membership
   docker inspect <DISCOVERED_BACKEND_CONTAINER> --format '{{range $k, $v := .NetworkSettings.Networks}}{{$k}}{{end}}'
   ```
2. **Inject Failure**: Disconnect the `<DISCOVERED_BACKEND_CONTAINER>` from the `<DISCOVERED_NETWORK>`. **Do NOT disconnect Caddy itself.**
   ```bash
   docker network disconnect <DISCOVERED_NETWORK> <DISCOVERED_BACKEND_CONTAINER>
   ```
3. **Verify Expected Error**: Hit the API through Caddy. Record the actual Caddy response without assuming it will strictly be a 502 Bad Gateway.
   ```bash
   curl -i $API_URL/health
   ```
4. **Recover**: Reconnect the container to the network.
   ```bash
   docker network connect <DISCOVERED_NETWORK> <DISCOVERED_BACKEND_CONTAINER>
   ```
5. **Verify Recovery**: Caddy should successfully route traffic to the API again.
   ```bash
   curl -i $API_URL/health
   ```

---

## Scenario 4: Container Crashes

**Goal**: Verify Docker's restart policies and orchestrator recovery when the backend process unexpectedly dies.

1. **Discover**: Find the API backend container ID and verify its restart policy.
   ```bash
   docker ps -f name=auth -q
   docker inspect <DISCOVERED_API_CONTAINER> --format '{{.HostConfig.RestartPolicy.Name}}'
   ```
2. **Inject Failure**: Forcefully kill the API container.
   ```bash
   docker kill <DISCOVERED_API_CONTAINER>
   ```
3. **Verify Expected Error**: Requests should temporarily fail (502 from Caddy).
   ```bash
   curl -i $API_URL/health
   ```
4. **Verify Recovery**: Based on the discovered restart policy, Docker should automatically recreate/restart the container. Monitor with `docker ps`.
5. **Verify State Integrity**: Once restarted, hit a DB-dependent endpoint to confirm full recovery.
   ```bash
   curl -i -H "Authorization: Bearer $DEV_TOKEN" $API_URL/api/v1/baas/projects/
   ```

---

## Scenario 10: Process Restarts

**Goal**: Verify graceful shutdown and recovery when the root process is terminated via signal.

1. **Discover**: Find the API backend container and verify PID 1 is Uvicorn.
   ```bash
   docker exec <DISCOVERED_API_CONTAINER> ps aux
   ```
2. **Inject Failure**: Send `SIGTERM` to PID 1 inside the container.
   ```bash
   docker exec <DISCOVERED_API_CONTAINER> kill -15 1
   ```
3. **Verify Expected Error**: The application should gracefully terminate current requests, flush logs, and exit. Docker will then restart it (according to its discovered restart policy).
4. **Verify Recovery**: Wait for Docker to spin the container back up (`docker ps`).
5. **Verify State Integrity**: Confirm no zombie connections were left by asserting successful API interaction.
   ```bash
   curl -i -H "Authorization: Bearer $DEV_TOKEN" $API_URL/api/v1/baas/projects/
   ```

---

## Scenario 2: Docker Unavailable (FINAL DESTRUCTIVE TEST)

> [!CAUTION]
> This is a full-system outage test. Ensure all previous scenarios are completed (Automated, Scenarios 1, 3, 4, 10 must all be GREEN) and the system is fully healthy before running this. Do not proceed if anything is unhealthy!

**Goal**: Verify full host-level stack recovery after a Docker daemon crash/restart.

1. **Explicit Checkpoint**: Verify the entire platform is healthy AND the Phase 18 lock is intact.
   - Verify the exact Phase 18 lock commit (`ff79262`) remains intact before stopping Docker.
     ```bash
     git status --short
     git rev-parse HEAD
     git log -n 3 --oneline
     ```
   - Verify the working tree contains only the intended Phase 19 changes and no secrets or temporary artifacts exist.
   - `curl -i $API_URL/health` succeeds.
   - DB-dependent request (`curl -i -H "Authorization: Bearer $DEV_TOKEN" $API_URL/api/v1/baas/projects/`) succeeds.
   **STOP** if any of the above fails. Do NOT commit Phase 19 before manual verification is complete.
2. **Inject Failure**: Stop the Docker daemon.
   ```bash
   sudo systemctl stop docker
   ```
3. **Verify Expected Error**: The entire platform goes dark. `docker ps` and Caddy ingress will fail.
4. **Recover**: Start the Docker daemon.
   ```bash
   sudo systemctl start docker
   ```
5. **Verify Recovery Chain**: 
   - Prove Docker is healthy: `docker info`
   - Prove Containers are up: `docker ps`
   - Prove DB is connected & Backend handles requests via Caddy:
     ```bash
     curl -i -H "Authorization: Bearer $DEV_TOKEN" $API_URL/api/v1/baas/projects/
     ```
