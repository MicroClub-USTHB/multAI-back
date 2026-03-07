from fastapi import Depends
import sqlalchemy.ext.asyncio
from app.infra.database import get_db
from db.generated import user as user_queries,session as session_queries,devices as device_queries

async def init_repo(conn: sqlalchemy.ext.asyncio.AsyncConnection = Depends(get_db)):
    user_querier:user_queries.AsyncQuerier = user_queries.AsyncQuerier(conn)
    session_querier:session_queries.AsyncQuerier = session_queries.AsyncQuerier(conn)
    device_querier :device_queries.AsyncQuerier = device_queries.AsyncQuerier(conn)
    return user_querier,session_querier,device_querier

