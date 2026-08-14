from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.config import config
from app.observability.logger import StructuredLogger


from app.api.routes import get_api_service
from app.api.auth_routes import get_auth_service
from app.api.dependencies import get_user_repository, get_authz_repo, get_baas_project_service
from app.api.baas_project_routes import router as baas_project_router
from app.api.baas_auth_routes import router as baas_auth_router, get_baas_auth_service
from app.api.baas_storage_routes import router as baas_storage_router, get_storage_service
from app.api.baas_service import BaaSProjectServiceLayer
from app.api.baas_auth_service import BaaSAuthService
from app.api.baas_storage_service import BaaSStorageService
from app.services.email_service import MockEmailProvider
from app.api.service import APIServiceLayer
from app.api.auth_service import AuthServiceLayer
from app.platform.audit.engine import AuditEngine
from app.platform.backup.engine import BackupEngine
from app.platform.deployment.engine import DeploymentEngine
from app.platform.events.engine import EventEngine
from app.platform.health.engine import HealthEngine
from app.platform.lifecycle.manager import LifecycleManager
from app.platform.operations.coordinator import PlatformOperationsCoordinator
from app.platform.restore.engine import RestoreEngine
from app.platform.validation.engine import ValidationEngine
from app.project_registry_manager import ProjectRegistryManager
from app.providers.deployment.docker_provider import DockerDeploymentProvider
from app.storage.providers.sqlite import (
    SQLiteAuditRepository,
    SQLiteOperationHistoryRepository,
    SQLiteProjectRepository,
    SQLiteUserRepository,
    SQLiteProjectAuthorizationRepository,
)
from app.storage.providers.sqlite_tenant import SQLiteTenantConnectionFactory, TenantDatabaseManager, BaaSAuthRepository

logger = StructuredLogger(component="app_runtime")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Application startup
    logger.info("system_startup", f"Starting {config.app_name} in {config.environment} mode.")

    import os
    os.makedirs("data", exist_ok=True)

    # 1. Repositories
    project_repo = SQLiteProjectRepository(db_path="data/projects.db")
    audit_repo = SQLiteAuditRepository(db_path="data/audit.db")
    history_repo = SQLiteOperationHistoryRepository(db_path="data/history.db")
    user_repo = SQLiteUserRepository(db_path="data/users.db")

    # 2. Managers
    registry_manager = ProjectRegistryManager(repository=project_repo)
    lifecycle_manager = LifecycleManager(registry=registry_manager)

    # 3. Engines
    audit_engine = AuditEngine(repository=audit_repo)
    event_engine = EventEngine()
    health_engine = HealthEngine(
        registry=registry_manager,
        lifecycle_manager=lifecycle_manager,
        tenant_db=None,            # wired below after tenant_factory is created
        storage_path=config.storage_path,
    )
    validation_engine = ValidationEngine(registry=registry_manager, lifecycle_manager=lifecycle_manager)
    backup_engine = BackupEngine(registry=registry_manager, lifecycle_manager=lifecycle_manager)
    restore_engine = RestoreEngine(registry=registry_manager, lifecycle_manager=lifecycle_manager, validation_engine=validation_engine)

    # 4. Providers
    docker_provider = DockerDeploymentProvider(simulate=False)

    # 5. Deployment Engine
    deployment_engine = DeploymentEngine(
        registry=registry_manager,
        lifecycle_manager=lifecycle_manager,
        validation_engine=validation_engine,
        deployment_adapter=docker_provider
    )

    # 6. Coordinator
    coordinator = PlatformOperationsCoordinator(
        lifecycle_manager=lifecycle_manager,
        validation_engine=validation_engine,
        deployment_engine=deployment_engine,
        backup_engine=backup_engine,
        restore_engine=restore_engine,
        health_engine=health_engine,
        event_engine=event_engine,
        audit_engine=audit_engine,
        history_repository=history_repo
    )

    # 7. API Service Layer
    api_service = APIServiceLayer(
        registry=registry_manager,
        coordinator=coordinator,
        lifecycle=lifecycle_manager,
        validation=validation_engine,
        health=health_engine,
        audit_engine=audit_engine,
        history_repository=history_repo,
        storage_path=str(config.storage_path),
    )

    # 8. Auth Service Layer
    auth_service = AuthServiceLayer(user_repo=user_repo)

    # 9. BaaS Service Layer
    authz_repo = SQLiteProjectAuthorizationRepository(db_path="data/authz.db")
    tenant_factory = SQLiteTenantConnectionFactory(storage_path="data")
    tenant_db = TenantDatabaseManager(factory=tenant_factory)
    # Late-bind tenant_db into health_engine (created before tenant_factory above)
    health_engine._tenant_db = tenant_db
    baas_service = BaaSProjectServiceLayer(
        internal_service=api_service,
        authz_repo=authz_repo,
        registry=registry_manager,
        user_repo=user_repo,
        tenant_db=tenant_db
    )

    # 10. BaaS Auth Service Layer
    baas_auth_repo = BaaSAuthRepository(factory=tenant_factory)
    email_provider = MockEmailProvider()
    baas_auth_service = BaaSAuthService(auth_repo=baas_auth_repo, email_provider=email_provider)

    # 11. BaaS Storage Service Layer
    from app.providers.storage.local_storage import LocalStorageProvider
    from app.storage.providers.sqlite_tenant import BaaSStorageRepository
    baas_storage_repo = BaaSStorageRepository(factory=tenant_factory)
    storage_adapter = LocalStorageProvider(base_dir=config.storage_path)
    baas_storage_service = BaaSStorageService(storage_repo=baas_storage_repo, storage_adapter=storage_adapter)

    # 12. Revocation Repository
    from app.storage.providers.sqlite import SQLiteRevocationRepository
    from app.api.dependencies import get_revocation_repo
    revocation_repo = SQLiteRevocationRepository(db_path="data/revocations.db")

    app.dependency_overrides[get_api_service] = lambda: api_service
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_authz_repo] = lambda: authz_repo
    app.dependency_overrides[get_baas_project_service] = lambda: baas_service
    app.dependency_overrides[get_baas_auth_service] = lambda: baas_auth_service
    app.dependency_overrides[get_storage_service] = lambda: baas_storage_service
    app.dependency_overrides[get_revocation_repo] = lambda: revocation_repo

    yield

    # Application shutdown
    logger.info("system_shutdown", f"Shutting down {config.app_name}.")


app = FastAPI(
    title=config.app_name,
    description="Platform Orchestration Framework",
    version="1.0.0",
    lifespan=lifespan,
    debug=config.debug,
)

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from app.storage.providers.sqlite_tenant import TenantDatabaseError
from fastapi.exception_handlers import http_exception_handler

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)

    import sqlite3
    from app.services.email_service import EmailDeliveryException
    if isinstance(exc, (sqlite3.OperationalError, OSError, EmailDeliveryException)):
        logger.error("service_unavailable", f"Service unavailable error: {str(exc)}")
        return JSONResponse(
            status_code=503,
            content={"error": "service_unavailable", "detail": "The service is temporarily unavailable. Please try again later."},
        )

    logger.error("internal_error", f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "detail": "An unexpected error occurred."},
    )

@app.exception_handler(TenantDatabaseError)
async def tenant_database_error_handler(request: Request, exc: TenantDatabaseError):
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )

# Register routes
app.include_router(router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(baas_project_router, prefix="/api/v1/baas")
app.include_router(baas_auth_router, prefix="/api/v1/baas/projects")
app.include_router(baas_storage_router)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow browser-based SDK / developer-console access.
# In production, restrict CORS_ALLOWED_ORIGINS to your actual domain(s).
import os as _os
_cors_origins_raw = _os.getenv("CORS_ALLOWED_ORIGINS", "*")
_cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
_allow_all = _cors_origins == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _cors_origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Platform-level health / readiness endpoint ─────────────────────────────────
from fastapi import Response as _Response

@app.get("/health", tags=["platform"], include_in_schema=True)
def platform_health() -> dict:
    """Unauthenticated readiness probe for load balancers and monitoring.

    Returns 200 when the platform is running.
    """
    return {"status": "ok", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
    )
