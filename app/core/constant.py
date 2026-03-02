from enum import Enum


class RedisKey(str,Enum):
    UserSession = "user_session"