from fastapi import APIRouter, Depends
import sqlalchemy.ext.asyncio

from app.deps.auth import get_current_mobile_user
from app.infra.database import get_db
from app.infra.redis import RedisClient
from app.schema.auth.mobile.auth import (
    MobileAuthRequest,
    MobileAuthResponse,
    RefreshTokenRequest,
    LogoutRequest,
)
from app.service.users import AuthService


router = APIRouter(prefix="/auth", tags=["mobile-auth"])


@router.post("/register-login", response_model=MobileAuthResponse)
async def mobile_register_login(
    req: MobileAuthRequest,
    conn: sqlalchemy.ext.asyncio.AsyncConnection = Depends(get_db),
    redis: RedisClient = Depends(),
):
    return await AuthService.mobile_register_login(conn, redis, req)


@router.post("/refresh", response_model=MobileAuthResponse)
async def refresh_token(
    req: RefreshTokenRequest,
    conn: sqlalchemy.ext.asyncio.AsyncConnection = Depends(get_db),
    redis: RedisClient = Depends(),
):
    return await AuthService.refresh_token(conn, redis, req.refresh_token)


@router.post("/logout")
async def logout(
    req: LogoutRequest,
    redis: RedisClient = Depends(),
):
    return await AuthService.logout(redis, req.user_id, req.session_id)


@router.get("/me")
async def get_me(
    user: dict = Depends(get_current_mobile_user),
):
    return user
