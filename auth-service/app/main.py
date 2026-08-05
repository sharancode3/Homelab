from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.api.routes import router
from app.config import config
from app.observability.logger import StructuredLogger


logger = StructuredLogger(component="app_runtime")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Application startup
    logger.info("system_startup", f"Starting {config.app_name} in {config.environment} mode.")
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=config.api_host,
        port=config.api_port,
        reload=config.debug,
    )