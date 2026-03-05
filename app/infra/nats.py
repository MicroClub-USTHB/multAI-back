from enum import Enum
from typing import Any, Callable, Optional
from nats.aio.client import Client as NATS
from nats.js.client import JetStreamContext
from nats.js.api import DeliverPolicy, AckPolicy
from app.core.config import settings

class NatsSubjects(Enum):
    USER_SIGNUP = "user.signup"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"

class NatsClient:
    _nc: Optional[NATS] = None
    _js: Optional[JetStreamContext] = None

    @staticmethod
    async def connect() -> None:
        if NatsClient._nc is None:
            NatsClient._nc = NATS()
            await NatsClient._nc.connect(
                servers=[f"nats://{settings.NATS_HOST}:{settings.NATS_PORT}"],
                user=settings.NATS_USER,
                password=settings.NATS_PASSWORD,
            )
            NatsClient._js = NatsClient._nc.jetstream()

    @staticmethod
    async def close() -> None:
        if NatsClient._nc and not NatsClient._nc.is_closed:
            await NatsClient._nc.drain()
            await NatsClient._nc.close()
            NatsClient._nc = None
            NatsClient._js = None


    @staticmethod
    async def publish(subject: NatsSubjects, message: bytes) -> None:
        if NatsClient._nc is None:
            await NatsClient.connect()
        await NatsClient._nc.publish(subject.value, message)

    @staticmethod
    async def subscribe(subject: NatsSubjects, callback: Callable[[Any], Any]) -> None:
        if NatsClient._nc is None:
            await NatsClient.connect()

        async def _wrapper(msg):
            await callback(msg.data)

        await NatsClient._nc.subscribe(subject.value, cb=_wrapper)


    @staticmethod
    async def js_publish(subject: NatsSubjects, message: bytes, stream_name: str) -> None:
        if NatsClient._js is None:
            await NatsClient.connect()
        await NatsClient._js.publish(subject.value, message, stream=stream_name)

    @staticmethod
    async def js_subscribe(
        subject: NatsSubjects,
        callback: Callable[[Any], Any],
        stream_name: str,
        durable_name: str,
        ack_policy: AckPolicy = AckPolicy.EXPLICIT
    ) -> None:
        if NatsClient._js is None:
            await NatsClient.connect()

        async def _wrapper(msg):
            await callback(msg.data)
            await msg.ack()

        await NatsClient._js.subscribe(
            subject=subject.value,
            stream=stream_name,
            durable=durable_name,
            cb=_wrapper,
            deliver_policy=DeliverPolicy.NEW,
            ack_policy=ack_policy
        )