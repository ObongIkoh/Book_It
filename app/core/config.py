from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    project_name: str = "BookIt"
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 60  # 1 hour
    refresh_token_expire_days: int = 7  # 7 days
    algorithm: str = "HS256"
    log_level: str = "INFO"
    test_database_url: Optional[str] = None  # For testing purposes
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"