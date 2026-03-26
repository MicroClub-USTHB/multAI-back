import time
from contextlib import asynccontextmanager
import asyncio
from typing import AsyncIterator
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from app.core.config import settings
from app.infra.minio import init_minio_client
from app.infra.nats import NatsClient
from app.infra.redis import RedisClient
from app.router.mobile import router as mobile_router
from app.router.staff import router as staff_router
from app.router.web import router as web_router
from app.deps.ai_deps import get_face_embedding_service
from app.core.logger import configure_logger, logger




configure_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:

        start_time = time.time()

        response = await call_next(request)

        process_time = time.time() - start_time

        logger.info(
            "%s %s status=%s time=%.3fs",
            request.method,
            request.url.path,
            response.status_code,
            process_time,
        )

        return response



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:

    for attempt in range(1, settings.MINIO_INIT_MAX_RETRIES + 1):
        try:
            await init_minio_client(
                minio_host=settings.MINIO_HOST,
                minio_port=settings.MINIO_API_PORT,
                minio_root_user=settings.MINIO_ROOT_USER,
                minio_root_password=settings.MINIO_ROOT_PASSWORD,
            )
            break
        except Exception as e:
            logger.warning(
                "MinIO init attempt %s/%s failed: %s",
                attempt,
                settings.MINIO_INIT_MAX_RETRIES,
                e,
            )
            if attempt == settings.MINIO_INIT_MAX_RETRIES:
                raise RuntimeError("Cannot connect to MinIO after multiple attempts") from e
            await asyncio.sleep(settings.MINIO_INIT_RETRY_BASE_SECONDS * attempt)

    RedisClient(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD,
    )

    await NatsClient.connect()
    get_face_embedding_service()

    yield

    await RedisClient.get_instance().close()
    await NatsClient.close()



app = FastAPI(
    title="multAI API",
    description="Mobile and Web API for multAI",
    version=settings.API_VERSION,
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root() -> dict[str, str]:
    return {"Hello": "World"}


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "healthy"}


app.include_router(mobile_router)
app.include_router(staff_router)
app.include_router(web_router)
