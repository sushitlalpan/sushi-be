import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "My App"
    APP_VERSION: str = "1.0.0"

    # Username and Password for login
    USER_NAME: str = ''
    PASSWORD: str = ''
    
    # Database URL (read from .env file)
    DATABASE_URL: str = ''
    
    # JWT Authentication settings
    JWT_SECRET_KEY: str = 'default-secret-key-change-in-production'
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # Client URL for CORS
    CLIENT_URL: str = 'http://localhost:3000'

    model_config = SettingsConfigDict(env_file=".env", extra='allow')

    @property
    def DB_URL(self):
        if self.ENV_MODE == "dev":
            return self.DEV_DB_URL
        else:
            if self.DATABASE_URL:
                return self.DATABASE_URL
            else:
                return '{}://{}:{}@{}:{}/{}'.format(
                    self.DB_ENGINE,
                    self.DB_USERNAME,
                    self.DB_PASS,
                    self.DB_HOST,
                    self.DB_PORT,
                    self.DB_NAME
                )

    @property
    def ASYNC_DB_URL(self):
        if self.ENV_MODE == "dev":
            # Check if we have a PostgreSQL DATABASE_URL in .env for dev mode
            if self.DATABASE_URL and self.DATABASE_URL.startswith('postgresql'):
                # Use psycopg for async connections - correct SQLAlchemy syntax for psycopg3
                URL_split = self.DATABASE_URL.split("://")
                return f"{URL_split[0]}+psycopg://{URL_split[1]}"
            else:
                # Fall back to SQLite for dev mode if no PostgreSQL URL provided
                return "sqlite+aiosqlite:///./dev.db"
        else:
            if self.DATABASE_URL:
                # Try asyncpg first, fallback to psycopg if asyncpg not available
                URL_split = self.DATABASE_URL.split("://")
                try:
                    import asyncpg
                    return f"{URL_split[0]}+asyncpg://{URL_split[1]}"
                except ImportError:
                    return f"{URL_split[0]}+psycopg://{URL_split[1]}"
            else:
                return '{}+psycopg://{}:{}@{}:{}/{}'.format(
                    self.DB_ENGINE,
                    self.DB_USERNAME,
                    self.DB_PASS,
                    self.DB_HOST,
                    self.DB_PORT,
                    self.DB_NAME
                )

    @property
    def API_BASE_URL(self) -> str:
        if self.ENV_MODE == "dev":
            return 'http://localhost:5000/'
        return self.HOST_URL

class DevSettings(Settings):
    # Environment mode: 'dev' or 'prod'
    ENV_MODE: str = 'dev'

    # Database settings for development
    @property  
    def DEV_DB_URL(self) -> str:
        # Use PostgreSQL in dev mode if DATABASE_URL is provided in .env
        # Otherwise fall back to SQLite
        return self.DATABASE_URL if self.DATABASE_URL else "sqlite:///./dev.db"

    model_config = SettingsConfigDict(env_file=".env", extra='allow')

class ProdSettings(Settings):
    # Environment mode: 'dev' or 'prod'
    ENV_MODE: str = 'prod'

    # Database settings for production
    DB_ENGINE: str = ''
    DB_USERNAME: str = ''
    DB_PASS: str = ''
    DB_HOST: str = ''
    DB_PORT: str = ''
    DB_NAME: str = ''

    # Define HOST_URL based on environment mode
    HOST_URL: str = ''

    # Database settings for production
    model_config = SettingsConfigDict(env_file=".env", extra='allow')

def get_settings(env_mode: str = "dev"):
    if env_mode == "dev":
        return DevSettings()
    return ProdSettings()