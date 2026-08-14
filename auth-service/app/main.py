from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.config import config
from app.observability.logger import StructuredLogger


from app.api.routes import get_api_service
from app.api.auth_routes import get_auth_service
from app.api.dependencies import get_user_repository, get_authz_repo, get_baas_project_service
from app.api.baas_project_routes import router as baas_project_router
from app.api.baas_service import BaaSProjectServiceLayer
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
    health_engine = HealthEngine(registry=registry_manager, lifecycle_manager=lifecycle_manager)
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
        health=health_engine
    )

    # 8. Auth Service Layer
    auth_service = AuthServiceLayer(user_repo=user_repo)

    # 9. BaaS Service Layer
    authz_repo = SQLiteProjectAuthorizationRepository(db_path="data/authz.db")
    baas_service = BaaSProjectServiceLayer(
        internal_service=api_service,
        authz_repo=authz_repo,
        registry=registry_manager,
        user_repo=user_repo
    )

    app.dependency_overrides[get_api_service] = lambda: api_service
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_user_repository] = lambda: user_repo
    app.dependency_overrides[get_authz_repo] = lambda: authz_repo
    app.dependency_overrides[get_baas_project_service] = lambda: baas_service

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

# Register routes
app.include_router(router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(baas_project_router, prefix="/api/v1/baas")



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
    )