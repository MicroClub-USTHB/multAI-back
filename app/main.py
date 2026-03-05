from app.infra.nats import NatsClient
from app.infra.redis import RedisClient
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.config import settings
from app.infra.minio import init_minio_client


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}



@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_minio_client(
        minio_host=settings.MINIO_HOST,
        minio_port=settings.MINIO_API_PORT,
        minio_root_user=settings.MINIO_ROOT_USER,
        minio_root_password=settings.MINIO_ROOT_PASSWORD,
    )
    RedisClient(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
    )
    await NatsClient.connect()
    yield
    await RedisClient.close()
    await NatsClient.close()

