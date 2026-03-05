from redis.asyncio import Redis
from app.core.constant import RedisKey


class RedisClient:
    client: Redis

    def __init__(self, host: str, port: int, password: str):
        self.client = Redis.from_url(
            f"redis://{host}:{port}", password=password, decode_responses=True
        )

    async def set(self, key: RedisKey, value: str, expire: int | None = None):
        await self.client.set(key, value, ex=expire)

    async def get(self, key: RedisKey) -> str | None:
        return await self.client.get(key)

    async def delete(self, key: RedisKey):
        await self.client.delete(key)

    async def close(self):
        await self.client.close()