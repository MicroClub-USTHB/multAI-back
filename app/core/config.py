from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "multAI"
    environment: str = "dev"
    debug: bool = True

    # Database
    database_url: str

    # Redis
    redis_url: str

    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_bucket: str

    # NATS
    nats_url: str

    # Security
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    encryption_key: str
    totp_issuer: str = "multAI"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings() # type: ignore