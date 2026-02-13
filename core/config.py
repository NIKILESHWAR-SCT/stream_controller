import os
from dotenv import load_dotenv

load_dotenv(".env.development")  

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/streaming_controller"
    )

    SERVICE_DEVICE_ONBOARDING_URL: str = os.getenv(
        "SERVICE_DEVICE_ONBOARDING_URL",
        "http://localhost:8001/api/v1/cameras/capabilities"
    )

print("DATABASE_URL =", os.getenv("DATABASE_URL"))

settings = Settings()
