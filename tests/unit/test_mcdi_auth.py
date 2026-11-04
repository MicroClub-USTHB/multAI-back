import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from app.core.config import settings
from app.router.web.auth import mcdi_callback
from app.service.mcdi import McdiService


@pytest.fixture
def mcdi_service() -> McdiService:
    return McdiService()


def test_get_sso_authorize_url(mcdi_service: McdiService) -> None:
    redirect_uri = "https://app.example.com/callback"
    state = "random-state-123"
    url = mcdi_service.get_sso_authorize_url(redirect_uri, state)

    assert "/auth/sso/authorize?" in url
    assert f"client_id={settings.MCDI_PROJECT_ID}" in url
    assert f"server_id={settings.MCDI_SERVER_ID}" in url
    assert "state=random-state-123" in url
    assert "redirect_uri=https%3A%2F%2Fapp.example.com%2Fcallback" in url


@pytest.mark.asyncio
async def test_exchange_code_success(mcdi_service: McdiService) -> None:
    expected_response = {
        "token": "sess_123456",
        "member": {
            "id": "discord_999",
            "username": "alice",
            "email": "alice@microclub.info",
            "isClubMember": True,
        },
        "roles": [{"roleId": "r1", "roleName": "Bureau"}],
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = expected_response

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        res = await mcdi_service.exchange_code("code_abc", "https://redirect.uri")

        assert res["token"] == "sess_123456"
        assert res["member"]["id"] == "discord_999"
        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        assert kwargs["json"]["code"] == "code_abc"
        assert kwargs["json"]["clientId"] == settings.MCDI_PROJECT_ID


@pytest.mark.asyncio
async def test_exchange_code_failure(mcdi_service: McdiService) -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 400
    mock_resp.json.return_value = {"message": "Invalid callback code"}

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        with pytest.raises(HTTPException) as exc_info:
            await mcdi_service.exchange_code("bad_code", "https://redirect.uri")
        assert "Invalid callback code" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_validate_token_cached_hit(mcdi_service: McdiService) -> None:
    redis = AsyncMock()
    cached_payload = {
        "member": {"id": "123", "email": "alice@club.net"},
        "roles": [],
    }
    redis.get.return_value = json.dumps(cached_payload)

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        data = await mcdi_service.validate_token_cached(
            redis, "token_xyz", ttl_seconds=60
        )
        assert data == cached_payload
        mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_validate_token_cached_miss_populates_cache(
    mcdi_service: McdiService,
) -> None:
    redis = AsyncMock()
    redis.get.return_value = None

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    remote_payload = {
        "member": {"id": "123", "email": "alice@club.net"},
        "roles": [],
    }
    mock_resp.json.return_value = remote_payload

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        data = await mcdi_service.validate_token_cached(
            redis, "token_xyz", ttl_seconds=60
        )

        assert data == remote_payload
        mock_post.assert_called_once()
        redis.set.assert_called_once()
        call_args = redis.set.call_args
        assert call_args[1]["expire"] == 60


@pytest.mark.asyncio
async def test_logout_invalidates_cache_and_calls_mcdi(
    mcdi_service: McdiService,
) -> None:
    redis = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        ok = await mcdi_service.logout("token_to_kill", redis=redis)

        assert ok is True
        redis.delete.assert_called_once()
        mock_post.assert_called_once()
        assert "/auth/logout" in mock_post.call_args[0][0]


@pytest.mark.asyncio
async def test_cookie_auth_get_current_staff_user_success_normalized_email() -> None:
    from app.deps.cookie_auth import get_current_staff_user

    container = MagicMock()
    container.redis = AsyncMock()
    container.mcdi_service = AsyncMock()
    container.staff_user_querier = AsyncMock()

    # Discord returns email with mixed case
    container.mcdi_service.validate_token_cached.return_value = {
        "member": {"email": "Admin.User@Microclub.info", "id": "111"},
        "roles": [{"roleName": "Admin"}],
    }

    mock_staff = MagicMock()
    mock_staff.email = "admin.user@microclub.info"
    container.staff_user_querier.get_staff_user_by_email.return_value = mock_staff

    staff = await get_current_staff_user(container=container, token="valid_staff_tok")
    assert staff == mock_staff
    # Verify email was normalized to lowercase
    container.staff_user_querier.get_staff_user_by_email.assert_called_once_with(
        email="admin.user@microclub.info"
    )


@pytest.mark.asyncio
async def test_cookie_auth_get_current_staff_user_unauthorized_if_not_staff() -> None:
    from app.deps.cookie_auth import get_current_staff_user

    container = MagicMock()
    container.redis = AsyncMock()
    container.mcdi_service = AsyncMock()
    container.staff_user_querier = AsyncMock()

    container.mcdi_service.validate_token_cached.return_value = {
        "member": {"email": "stranger@discord.com", "id": "999"},
        "roles": [],
    }

    container.staff_user_querier.get_staff_user_by_email.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await get_current_staff_user(container=container, token="valid_mcdi_tok")
    assert exc_info.value.status_code == 401
    assert "not authorized" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_mcdi_callback_handles_oauth_error() -> None:
    request = MagicMock()
    container = MagicMock()

    res = await mcdi_callback(
        request=request,
        code=None,
        state="some_state",
        error="access_denied",
        error_description="User cancelled",
        container=container,
    )

    assert isinstance(res, RedirectResponse)
    assert "error=access_denied" in res.headers["location"]


@pytest.mark.asyncio
async def test_mcdi_callback_success() -> None:
    request = MagicMock()
    request.cookies = {"mcdi_state": "expected_state"}
    container = MagicMock()
    container.mcdi_service = AsyncMock()
    container.mcdi_service.exchange_code.return_value = {
        "token": "new_mcdi_session_token",
        "member": {"email": "Leader@microclub.info"},
    }

    mock_staff = MagicMock()
    mock_staff.email = "leader@microclub.info"
    container.staff_user_querier.get_staff_user_by_email = AsyncMock(return_value=mock_staff)

    res = await mcdi_callback(
        request=request,
        code="auth_code_123",
        state="expected_state",
        container=container,
    )

    assert isinstance(res, RedirectResponse)
    assert "/admin" in res.headers["location"]
    container.staff_user_querier.get_staff_user_by_email.assert_called_once_with(
        email="leader@microclub.info"
    )


@pytest.mark.asyncio
async def test_mcdi_callback_invalid_state() -> None:
    request = MagicMock()
    request.cookies = {"mcdi_state": "real_state"}
    container = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await mcdi_callback(
            request=request,
            code="code123",
            state="forged_state",
            container=container,
        )

    assert exc_info.value.status_code == 401
    assert "Invalid state" in exc_info.value.detail
