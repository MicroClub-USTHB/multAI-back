from db.generated import session as session_queries
from app.core.exceptions import DBException
import uuid
from db.generated.models import Session as Session_querier
class SessionService :
    session_querier : session_queries.AsyncQuerier

    def init(self,session:session_queries.AsyncQuerier):
        self.session_querier = session
    
    @staticmethod
    async def create_session(user_id:uuid.UUID,device_id:uuid.UUID)->Session:
        try :
            return await SessionService.session_querier.
        except Exception as e :
            DBException.handle(e)