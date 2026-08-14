import os

class AppSettings:
    """Application configuration settings from environment variables."""

    def __init__(self) -> None:
        self.app_name = os.getenv("PLATFORM_APP_NAME", "Auth Service Platform")
        self.environment = os.getenv("PLATFORM_ENVIRONMENT", "development")
        self.debug = os.getenv("PLATFORM_DEBUG", "false").lower() == "true"

        self.api_host = os.getenv("PLATFORM_API_HOST", "0.0.0.0")
        self.api_port = int(os.getenv("PLATFORM_API_PORT", "8000"))

        self.storage_path = os.getenv("PLATFORM_STORAGE_PATH", "/var/lib/auth-service/data")

        # Phase 14.2 Storage Service Limits
        self.storage_max_file_size_bytes = int(os.getenv("PLATFORM_STORAGE_MAX_FILE_SIZE", 5 * 1024 * 1024))
        self.storage_max_project_quota_bytes = int(os.getenv("PLATFORM_STORAGE_MAX_PROJECT_QUOTA", 100 * 1024 * 1024))

        self.secret_key = os.getenv("PLATFORM_SECRET_KEY", "change-me-in-production")

        internal_token = os.getenv("PLATFORM_INTERNAL_API_TOKEN")
        if not internal_token:
            raise ValueError("PLATFORM_INTERNAL_API_TOKEN must be explicitly configured")
        self.internal_api_token = internal_token

    def is_production(self) -> bool:
        return self.environment.lower() == "production"

# Singleton config instance
config = AppSettings()
