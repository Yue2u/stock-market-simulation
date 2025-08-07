import logging
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

logger = logging.getLogger(__name__)


class StockMarket:
    def __init__(self):
        try:
            self.data, self.news = self.load_chart_data()
            self.current_step_chart = 0
            self.current_step_news = -1
        except Exception as e:
            logger.error(f"Failed to initialize StockMarket: {e}")
            raise

    @property
    def current_step_chart_str(self):
        return str(self.current_step_chart)

    @property
    def current_step_news_str(self):
        return str(self.current_step_news)

    def load_chart_data(self) -> tuple[list[dict[str, int]], list[list[str]]]:
        """Load both chart data and news from file once to avoid duplicate reads"""
        from config import CHART_DATA_FILE

        chart_file = CHART_DATA_FILE

        if not chart_file.exists():
            raise FileNotFoundError(f"Chart data file not found: {chart_file}")

        try:
            with open(chart_file, "r", encoding="utf-8") as f:
                js = orjson.loads(f.read())

            # Extract chart data and news data
            chart_data = [data["chart"] for data in js.values()]
            news_data = [data["news"] or [] for data in js.values()]

            return chart_data, news_data

        except orjson.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in chart data file: {e}")
        except KeyError as e:
            raise ValueError(f"Missing required key in chart data: {e}")
        except IOError as e:
            raise IOError(f"Failed to read chart data file: {e}")

    def set_chart_step(self, step: int):
        """Set current chart step with bounds checking"""
        if 0 <= step < len(self.data):
            self.current_step_chart = step
            if self.current_step_news >= self.current_step_chart:
                self.current_step_news = self.current_step_chart - 1
        else:
            logger.warning(
                f"Invalid chart step {step}, must be between 0 and {len(self.data)-1}"
            )

    def set_news_step(self, step: int):
        """Set current news step with constraint validation"""
        if step + 1 > self.current_step_chart:
            logger.warning(
                f"Invalid news step {step}, must satisfy: news_step + 1 <= chart_step ({self.current_step_chart})"
            )
            return False
        if 0 <= step < len(self.news):
            self.current_step_news = step
            return True
        else:
            logger.warning(
                f"Invalid news step {step}, must be between 0 and {len(self.news)-1}"
            )
            return False

    def next_chart_step(self):
        """Move to next chart step with bounds checking"""
        if self.current_step_chart >= len(self.data) - 1:
            logger.info("Already at the last chart step, cannot advance further")
            return False
        self.current_step_chart += 1
        if self.current_step_news >= self.current_step_chart:
            self.current_step_news = self.current_step_chart - 1
        return True

    def next_news_step(self):
        """Move to next news step with constraint validation"""
        if self.current_step_news + 1 > self.current_step_chart:
            logger.warning(
                f"Cannot advance news step: would violate constraint (news_step + 1 <= chart_step {self.current_step_chart})"
            )
            return False
        if self.current_step_news + 1 >= len(self.news):
            logger.info("Already at the last news step, cannot advance further")
            return False
        self.current_step_news += 1
        return True

    def get_current_step_data(self) -> dict[str, dict[str, int]]:
        """Returns dict with string keys, not int keys"""
        return {self.current_step_chart_str: self.data[self.current_step_chart]}

    def get_until_current_step_data(self) -> dict[str, dict[str, int]]:
        """Returns dict with string keys, not int keys"""
        return {
            str(i): data
            for i, data in enumerate(self.data[: self.current_step_chart + 1])
        }

    def get_current_step_news(self) -> dict[str, list[str]]:
        """Returns dict with string keys, not int keys"""
        if self.current_step_news < 0:
            return {}
        return {self.current_step_news_str: self.news[self.current_step_news]}

    def get_until_current_step_news(self) -> dict[str, list[str]]:
        """Returns dict with string keys, not int keys"""
        if self.current_step_news < 0:
            return {}
        return {
            str(i): news
            for i, news in enumerate(self.news[: self.current_step_news + 1])
        }

    def update_step_data(self, step_num: int, data: dict[str, int]):
        """Update step data with bounds checking"""
        if not (0 <= step_num < len(self.data)):
            logger.warning(f"Cannot update step {step_num}: out of bounds")
            return False
        self.data[step_num] = data
        return True

    def update_step_news(self, step_num: int, news: list[str]):
        """Update step news with bounds checking"""
        if not (0 <= step_num < len(self.news)):
            logger.warning(f"Cannot update step {step_num}: out of bounds")
            return False
        self.news[step_num] = news
        return True

    def get_step_data(self, step_num: int) -> dict[str, int]:
        """Get step data with bounds checking"""
        if not (0 <= step_num < len(self.data)):
            logger.warning(f"Invalid step number {step_num}")
            return {}
        return self.data[step_num]

    def get_step_news(self, step_num: int) -> list[str]:
        """Get step news with bounds checking"""
        if not (0 <= step_num < len(self.news)):
            logger.warning(f"Invalid step number {step_num}")
            return []
        return self.news[step_num]

    def reset(self):
        self.data, self.news = self.load_chart_data()
        self.current_step_chart = 0
        self.current_step_news = -1


class StockMarketController:
    _stock: StockMarket = None

    @classmethod
    def stock(cls) -> StockMarket:
        if not cls._stock:
            cls._stock = StockMarket()
            logger.info("StockMarket instance created")
        return cls._stock

    @classmethod
    async def next_chart_step(cls):
        """Move to next chart step with error handling"""
        try:
            success = cls.stock().next_chart_step()
            if not success:
                logger.warning(
                    "Cannot advance to next chart step: already at last step"
                )
            return success
        except Exception as e:
            logger.error(f"Error advancing to next chart step: {e}")
            raise

    @classmethod
    async def next_news_step(cls):
        """Move to next news step with error handling"""
        try:
            success = cls.stock().next_news_step()
            if not success:
                logger.warning(
                    "Cannot advance to next news step: constraint violation or at last step"
                )
            return success
        except Exception as e:
            logger.error(f"Error advancing to next news step: {e}")
            raise

    @classmethod
    async def publish_current_chart_data(cls):
        """Publish current chart data with error handling"""
        try:
            data = cls.stock().get_current_step_data()
            await Publisher.notify(ChartUpdateEvent(data))
        except Exception as e:
            logger.error(f"Error publishing chart data: {e}")
            raise

    @classmethod
    async def publish_current_news(cls):
        """Publish current news with error handling"""
        try:
            success = cls.stock().next_news_step()
            if not success:
                logger.warning("Cannot publish news: unable to advance news step")
                return False
            news = cls.stock().get_current_step_news()
            await Publisher.notify(NewsUpdateEvent(news))
            return True
        except Exception as e:
            logger.error(f"Error publishing news: {e}")
            raise

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
        return cls.stock().get_step_data(cls.stock().current_step_chart + 1)

    @classmethod
    def get_next_step_news(cls):
        return cls.stock().get_step_news(cls.stock().current_step_news + 1)
