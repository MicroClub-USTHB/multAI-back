from pydantic import BaseModel, EmailStr


class MobileAuthRequest(BaseModel):
    email: EmailStr
    password: str
    device_id: str
    device_name: str
    device_type: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class MobileAuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    session_id: str
    expires_in: int


class LogoutRequest(BaseModel):
    session_id: str
    user_id: str
