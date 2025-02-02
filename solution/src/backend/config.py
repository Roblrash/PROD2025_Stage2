from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SERVER_ADDRESS: str
    SERVER_PORT: int
    POSTGRES_USERNAME: str
    POSTGRES_PASSWORD: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    POSTGRES_DATABASE: str
    REDIS_HOST: str
    REDIS_PORT: int
    ANTIFRAUD_ADDRESS: str
    RANDOM_SECRET: str

    @property
    def database_url(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USERNAME}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
