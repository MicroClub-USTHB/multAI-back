from pydantic import BaseModel
from app.core.exceptions import AppException
from db.generated import session as session_queries
from app.core.exceptions import DBException
import uuid
from db.generated.models import UserSession 
from datetime import datetime,timedelta,timezone
from redis.asyncio import Redis
from app.infra.redis import RedisClient
from app.core.constant import RedisKey


class SessionRedis(BaseModel):
    session_id:uuid.UUID
    user_id:uuid.UUID
    device_id:uuid.UUID
    last_active:datetime
    expires_at:datetime

class SessionService :
    session_querier : session_queries.AsyncQuerier
    redis : RedisClient

    def init(self,session:session_queries.AsyncQuerier,redis:Redis):
        self.session_querier = session
        self.redis = redis
    
    @staticmethod
    async def create_session(user_id:uuid.UUID,device_id:uuid.UUID)->UserSession:
        try :
            session = await SessionService.session_querier.upsert_session(
                user_id=user_id,
                device_id=device_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            )
            
            result = await SessionService.redis.set(
                key=RedisKey.UserSessionByUser.format(user_id=user_id),
                value=SessionRedis(
                    session_id=session.id,
                    user_id=session.user_id,
                    device_id=session.device_id,
                    last_active=session.last_active,
                    expires_at=session.expires_at,
                ).model_dump_json(),
                expire=60*60*5,
                nx=True
            )
            if not result:
                AppException.forbidden("You already logged in in another device")
            return session
        except Exception as e :
            DBException.handle(e)
        

    @staticmethod
    async def get_session_by_id(session_id:uuid.UUID)->UserSession:
        try :
            return await SessionService.session_querier.get_session_by_id(id=session_id)
        except Exception as e :
            DBException.handle(e)

            
    @staticmethod
    async def Check_Session(session_id:uuid.UUID,user_id:uuid.UUID,device_id :uuid.UUID)->bool:
        try :
            Sessioninfo = SessionRedis.model_validate_json(await SessionService.redis.get(RedisKey.UserSessionByUser.format(user_id=user_id)))
            if  Sessioninfo:
                if Sessioninfo.device_id != device_id and Sessioninfo.session_id != session_id:
                    AppException.forbidden("You already logged in in another device")
                else:
                    await SessionService.redis.set(
                        key=RedisKey.UserSessionByUser.format(user_id=user_id),
                        value=SessionRedis(
                            session_id=session.id,
                            user_id=session.user_id,
                            device_id=session.device_id,
                            last_active=session.last_active,
                            expires_at=session.expires_at,
                        ).model_dump_json(),
                        expire=60*60*5,
                        nx=False
                    )
            else:
                session = await SessionService.session_querier.get_session_by_id(id=session_id)
                if not session:
                    AppException.forbidden("You already logged in in another device")
                await SessionService.redis.set(
                    key=RedisKey.UserSessionByUser.format(user_id=user_id),
                    value=SessionRedis(
                        session_id=session.id,
                        user_id=session.user_id,
                        device_id=session.device_id,
                        last_active=session.last_active,
                        expires_at=session.expires_at,
                    ).model_dump_json(),
                    expire=60*60*5,
                    nx=True
                )
            return True
        except Exception as e :
            DBException.handle(e)


    @staticmethod
    async def delete_session(session_id:uuid.UUID,user_id:uuid.UUID):
        try :
            await SessionService.session_querier.delete_session_by_device(id=session_id,user_id=user_id)
        except Exception as e :
            DBException.handle(e)
    
    
    @staticmethod
    async def delete_expired_sessions():
        try :
            await SessionService.session_querier.delete_expired_sessions()
        except Exception as e :
            DBException.handle(e)
    
    @staticmethod
    async def count_user_sessions(user_id:uuid.UUID)->int:
        try :
            return await SessionService.session_querier.count_user_sessions(user_id=user_id)
        except Exception as e :
            DBException.handle(e)
