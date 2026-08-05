# Platform Orchestrator Deployment Guide

This document describes how to deploy the Platform Orchestrator service into a production-like environment.

## Overview

The Platform Orchestrator is containerized and relies on standard Docker tooling.
It leverages local storage by default (mounted via Docker volumes) and handles all coordination without needing external brokers in this phase.

## Prerequisites

- Docker (v20+)
- Docker Compose (v2+)

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `PLATFORM_ENVIRONMENT` | `production` | Deployment mode (`development`, `staging`, `production`) |
| `PLATFORM_DEBUG` | `false` | Enable debug logs |
| `PLATFORM_API_HOST` | `0.0.0.0` | Bind host for FastAPI |
| `PLATFORM_API_PORT` | `8000` | Bind port for FastAPI |
| `PLATFORM_STORAGE_PATH` | `/var/lib/auth-service/data` | Path to persistent storage |
| `PLATFORM_SECRET_KEY` | `change-me-in-production` | Secret key for platform security layers |

## Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repo_url>
   cd auth-service
   ```

2. **Configure environment:**
   Create a `.env` file (optional if relying on defaults):
   ```bash
   PLATFORM_ENVIRONMENT=production
   PLATFORM_DEBUG=false
   PLATFORM_SECRET_KEY=super-secure-key
   ```

3. **Build and Run:**
   ```bash
   docker-compose up -d --build
   ```

4. **Verify Startup:**
   Check the application logs to ensure the startup lifecycle hooked correctly:
   ```bash
   docker-compose logs -f platform-orchestrator
   ```

## Health Verification

The orchestrator provides health checks on `/api/v1/health/platform` (assuming you have registered the `health_project` endpoint under this route, or use `/docs` to verify the API layer).
You can also run a test health evaluation:
```bash
curl -X GET "http://localhost:8000/api/v1/health/platform"
```

## Shutdown

To stop the service safely and allow FastAPI lifespan hooks to run:
```bash
docker-compose down
```
