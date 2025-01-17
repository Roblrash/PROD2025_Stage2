from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    SERVER_ADDRESS: str = "0.0.0.0:8080"
    SERVER_PORT: int = 8080
    POSTGRES_CONN: str
    POSTGRES_JDBC_URL: str
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str
    REDIS_HOST: str
    REDIS_PORT: int = 6379
    ANTIFRAUD_ADDRESS: str
    RANDOM_SECRET: str = "default_secret"

    @property
    def database_url(self):
        return self.POSTGRES_CONN or (
            f"postgresql+asyncpg://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        )

    class Config:
        env_file = ".env"

settings = Settings()
