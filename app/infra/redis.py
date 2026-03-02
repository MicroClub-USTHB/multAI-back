import aioredis

from app.core.constant import RedisKey


class RedisClient:
    client: aioredis.Redis
    async def __init__(self, host: str, port: int, password: str):
        self.client = aioredis.from_url(f"redis://{host}:{port}", password=password, decode_responses=True) # type: ignore
    async def set(self, key: RedisKey, value: str, expire: int | None = None):
        await self.client.set(key, value, ex=expire) # type: ignore
    async def get(self, key: RedisKey) -> str | None:
        return await self.client.get(key) # type: ignore
    async def delete(self, key: RedisKey):
        await self.client.delete(key) # type: ignore
    async def close(self):
        await self.client.close()