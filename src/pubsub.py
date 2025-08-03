import asyncio
from typing import Generic, TypeVar
from uuid import UUID, uuid4

from events import Event, EventType

T = TypeVar("T")


class TimeoutQueue(Generic[T]):
    def __init__(self):
        self.q = asyncio.Queue()

    async def get(self, timeout: float = 1.0) -> T:
        async with asyncio.timeout(timeout):
            result = await self.q.get()
            return result

    async def put(self, item: T, timeout: float = 1.0):
        async with asyncio.timeout(timeout):
            await self.q.put(item)


class EventQueue(TimeoutQueue[Event]):
    pass


class Publisher:
    _instance: "Publisher" = None

    def __init__(self):
        self.subscribers: dict[UUID, "Subscriber"] = {}

    @classmethod
    def instance(cls) -> "Publisher":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def subscribe(cls, subscriber: "Subscriber"):
        cls.instance().subscribers[subscriber.uid] = subscriber

    @classmethod
    def unsubscribe(cls, subscriber: "Subscriber"):
        if subscriber.uid in cls.instance().subscribers:
            cls.instance().subscribers.pop(subscriber.uid)

    @classmethod
    async def notify(cls, event: Event):
        await asyncio.gather(
            *[
                subscriber.update(event)
                for subscriber in cls.instance().subscribers.values()
            ]
        )

    @classmethod
    async def notify_by_uid(cls, uid: UUID, event: Event):
        if uid in cls.instance().subscribers:
            await cls.instance().subscribers[uid].update(event)


class Subscriber:
    def __init__(self):
        self.uid = uuid4()
        self.events = EventQueue()
        self._stopped = False

    def stop(self):
        self._stopped = True

    async def update(self, event: Event):
        await self.events.put(event, 2.0)

    async def listen(self):
        while not self._stopped:
            try:
                event = await self.events.get(2.0)
            except asyncio.TimeoutError:
                continue
            if event._type == EventType.STREAM_STOP:
                return
            yield event.dump()
