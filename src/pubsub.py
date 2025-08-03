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
        """Notify all subscribers with race condition protection"""
        # Create a snapshot of subscribers to avoid race conditions
        subscribers_snapshot = list(cls.instance().subscribers.values())

        if not subscribers_snapshot:
            return

        try:
            await asyncio.gather(
                *[subscriber.update(event) for subscriber in subscribers_snapshot],
                return_exceptions=True,  # Don't fail if one subscriber fails
            )
        except Exception as e:
            # Log the error but don't crash the whole system
            print(f"Error notifying subscribers: {e}")

    @classmethod
    async def notify_by_uid(cls, uid: UUID, event: Event):
        if uid in cls.instance().subscribers:
            await cls.instance().subscribers[uid].update(event)

    @classmethod
    async def cleanup_stale_subscribers(cls, timeout_seconds: int = 300):
        """Remove subscribers that haven't been active recently"""
        instance = cls.instance()
        stale_uids = [
            uid
            for uid, subscriber in instance.subscribers.items()
            if subscriber.is_stale(timeout_seconds)
        ]

        for uid in stale_uids:
            instance.subscribers.pop(uid, None)
            print(f"Cleaned up stale subscriber: {uid}")

        return len(stale_uids)

    @classmethod
    async def start_cleanup_task(cls):
        """Start periodic cleanup of stale subscribers"""
        while True:
            await asyncio.sleep(60)  # Check every minute
            try:
                await cls.cleanup_stale_subscribers()
            except Exception as e:
                print(f"Error in cleanup task: {e}")


class Subscriber:
    def __init__(self):
        self.uid = uuid4()
        self.events = EventQueue()
        self._stopped = False
        self._last_activity = asyncio.get_event_loop().time()

    def stop(self):
        self._stopped = True

    async def update(self, event: Event):
        """Update with activity tracking"""
        self._last_activity = asyncio.get_event_loop().time()
        try:
            await self.events.put(event, 2.0)
        except asyncio.TimeoutError:
            # Mark as potentially dead if queue is full
            print(f"Subscriber {self.uid} queue timeout - may be disconnected")

    def is_stale(self, timeout_seconds: int = 300) -> bool:
        """Check if subscriber has been inactive for too long"""
        current_time = asyncio.get_event_loop().time()
        return (current_time - self._last_activity) > timeout_seconds

    async def listen(self):
        while not self._stopped:
            try:
                event = await self.events.get(2.0)
            except asyncio.TimeoutError:
                continue
            if event._type == EventType.STREAM_STOP:
                return
            yield event.dump()
