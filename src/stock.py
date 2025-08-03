from uuid import UUID

import orjson

from events import (
    ChartLoadEvent,
    ChartUpdateEvent,
    NewsLoadEvent,
    NewsUpdateEvent,
    StopStreamEvent,
)
from pubsub import Publisher


class StockMarket:
    def __init__(self):
        self.data = self.load_data()
        self.news = self.load_news()
        self.current_step = 0

    @property
    def current_step_str(self):
        return str(self.current_step)

    def load_data(self) -> list[dict[str, int]]:
        with open("chart_data.json") as f:
            js = orjson.loads(f.read())
        return [data["chart"] for data in js.values()]

    def load_news(self) -> list[list[str]]:
        with open("chart_data.json") as f:
            js = orjson.loads(f.read())
        return [data["news"] or [] for data in js.values()]

    def set_step(self, step: int):
        if step < len(self.data):
            self.current_step = step

    def next_step(self):
        if self.current_step == len(self.data):
            return
        self.current_step += 1

    def get_current_step_data(self) -> dict[int, dict[str, int]]:
        return {self.current_step_str: self.data[self.current_step]}

    def get_until_current_step_data(self) -> dict[int, dict[str, int]]:
        return {
            str(i): data for i, data in enumerate(self.data[: self.current_step + 1])
        }

    def get_current_step_news(self) -> dict[int, list[str]]:
        return {self.current_step_str: self.news[self.current_step]}

    def get_until_current_step_news(self) -> dict[int, list[str]]:
        return {
            str(i): news for i, news in enumerate(self.news[: self.current_step + 1])
        }

    def update_step_data(self, step_num: int, data: dict[str, int]):
        if step_num >= len(self.data):
            return
        self.data[step_num] = data

    def update_step_news(self, step_num: int, news: list[str]):
        if step_num >= len(self.news):
            return
        self.news[step_num] = news

    def get_step_data(self, step_num: int) -> dict[str, int]:
        if step_num >= len(self.data):
            return {}
        return self.data[step_num]

    def get_step_news(self, step_num: int) -> list[str]:
        if step_num >= len(self.news):
            return []
        return self.news[step_num]

    def reset(self):
        self.current_step = 0


class StockMarketController:
    _stock: StockMarket = None

    @classmethod
    def stock(cls) -> StockMarket:
        if not cls._stock:
            cls._stock = StockMarket()
        print(cls._stock, cls._stock.__dict__)
        return cls._stock

    @classmethod
    async def next_step(cls):
        cls.stock().next_step()

    @classmethod
    async def publish_current_chart_data(cls):
        await Publisher.notify(ChartUpdateEvent(cls.stock().get_current_step_data()))

    @classmethod
    async def publish_current_news(cls):
        await Publisher.notify(NewsUpdateEvent(cls.stock().get_current_step_news()))

    @classmethod
    async def publish_until_current_step_data(cls, uid: UUID):
        await Publisher.notify_by_uid(
            uid, ChartLoadEvent(cls.stock().get_until_current_step_data())
        )

    @classmethod
    async def publish_until_current_step_news(cls, uid: UUID):
        await Publisher.notify_by_uid(
            uid, NewsLoadEvent(cls.stock().get_until_current_step_news())
        )

    @classmethod
    async def publish_until_current_step_data_all(cls):
        await Publisher.notify(
            ChartLoadEvent(cls.stock().get_until_current_step_data())
        )

    @classmethod
    async def publish_until_current_step_news_all(cls):
        await Publisher.notify(NewsLoadEvent(cls.stock().get_until_current_step_news()))

    @classmethod
    async def publish_stop_game(cls):
        await Publisher.notify(StopStreamEvent())

    @classmethod
    async def reset(cls):
        cls.stock().reset()
        await cls.publish_until_current_step_data_all()
        await cls.publish_until_current_step_news_all()

    @classmethod
    def get_current_step_chart(cls):
        return cls.stock().get_current_step_data()

    @classmethod
    def get_current_step_news(cls):
        return cls.stock().get_current_step_news()

    @classmethod
    def get_next_step_chart(cls):
        return cls.stock().get_step_data(cls.stock().current_step + 1)

    @classmethod
    def get_next_step_news(cls):
        return cls.stock().get_step_news(cls.stock().current_step + 1)
