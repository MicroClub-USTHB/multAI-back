from typing import Any
import uuid
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core import constant
from app.core.exceptions import AppException
from app.core.securite import decode_access_mobile_token
from app.infra.redis import RedisClient
from app.service.users import AuthService
from db.generated import user as user_queries
from db.generated import session as session_queries


security = HTTPBearer()

async def get_current_mobile_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn : Depends()
) -> dict[str, Any]:
    token = credentials.credentials
    payload = decode_access_mobile_token(token)
    session_id = payload.get("session_id")

    if not session_id:
        raise AppException.unauthorized("Invalid token")

    session_querier = session_queries.AsyncQuerier(conn)
    session = await session_querier.get_session_by_id(id=uuid.UUID(session_id))

    if not session:
        raise AppException.unauthorized("Session not found")

    if session.expires_at.replace(tzinfo=None) < payload.get("exp", 0):
        raise AppException.unauthorized("Session expired")

    session_key = constant.RedisKey.UserSessionByUser.value.format(
        user_id=session.user_id
    )
    redis_session = await redis.get(session_key)

    if not redis_session or redis_session != session_id:
        raise AppException.forbidden("Invalid session. Please login again.")

    await redis.expire(session_key, AuthService.REDIS_SESSION_TTL)

    user_querier = user_queries.AsyncQuerier(conn)
    user = await user_querier.get_user_by_id(id=session.user_id)

    if not user:
        raise AppException.unauthorized("User not found")

    return {
        "user_id": str(user.id),
        "email": user.email,
        "session_id": session_id,
    }
