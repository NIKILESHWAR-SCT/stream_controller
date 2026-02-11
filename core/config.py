import os
from typing import Literal


class Settings:
    DB_NAME: str = os.getenv("DB_NAME", "streaming_controller")
    DB_HOST: str = os.getenv("DB_HOST", "192.168.1.144")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "vigilxdev")
    # Async driver
    DB_DRIVER: str = os.getenv("DB_DRIVER", "asyncpg")

    SERVICE_DEVICE_ONBOARDING_URL: str = os.getenv(
        "SERVICE_DEVICE_ONBOARDING_URL", "http://localhost:8001/api/v1/cameras/capabilities"
    )


settings = Settings()
