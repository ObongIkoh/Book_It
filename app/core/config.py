from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, Field
from typing import Optional
import secrets
import logging

# Configure logger
logger = logging.getLogger("bookit.config")
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class Settings(BaseSettings):
    # Application
    project_name: str = "BookIt"
    environment: str
    debug: bool = False

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")
    test_database_url: Optional[str] = Field(None, alias="TEST_DATABASE_URL")

    # Security
    secret_key: str = Field(..., alias="SECRET_KEY")
    algorithm: str = "HS256"

    # Token Expiration
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        alias="CORS_ORIGINS",
        description="Allowed CORS origins"
    )

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60

    # ✅ New Pydantic v2 config
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # ----------------------------
    # Validators
    # ----------------------------
    @field_validator("secret_key")
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    @field_validator("database_url")
    def validate_database_url(cls, v):
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            logger.warning("⚠️ Database URL should start with postgresql://")
        return v

    @field_validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()

    @field_validator("environment")
    def validate_environment(cls, v):
        valid_envs = ["development", "staging", "production"]
        if v.lower() not in valid_envs:
            raise ValueError(f"environment must be one of: {', '.join(valid_envs)}")
        return v.lower()

    @field_validator("cors_origins", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    # Helpers
    def is_production(self) -> bool:
        return self.environment == "production"

    def is_development(self) -> bool:
        return self.environment == "development"

    def get_database_url(self, for_testing: bool = False) -> str:
        return self.test_database_url if for_testing and self.test_database_url else self.database_url


# Singleton instance
try:
    settings = Settings()
    logger.info(f"✅ Loaded config for {settings.project_name} ({settings.environment})")
except Exception as e:
    logger.error(f"❌ Failed to load configuration: {e}")
    logger.error("Please check your .env file and environment variables")
    raise


# Helper function to generate a secure secret key
def generate_secret_key() -> str:
    return secrets.token_hex(32)


if __name__ == "__main__":
    print(f"Generated SECRET_KEY={generate_secret_key()}")
