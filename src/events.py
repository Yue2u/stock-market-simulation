from typing import Any

import orjson


class EventType:
    LOAD = "load"
    UPDATE = "update"
    STREAM_STOP = "stream_stop"


class EventDataType:
    CHART = "chart"
    NEWS = "news"


class Event:
    _type: str

    def __init__(self, data: Any):
        self.data = data

    def make_data(self):
        return {"data": self.data, "event_type": self._type}

    def dump(self):
        return orjson.dumps(self.make_data()).decode()


class DataTypedEvent(Event):
    _data_type: str

    def make_data(self):
        return super().make_data() | {"data_type": self._data_type}


class LoadEvent(DataTypedEvent):
    """
    This type of event has to be sent after connection.
    It has list of data for chart or news
    """

    _type = EventType.LOAD


class NewsLoadEvent(LoadEvent):
    _data_type = EventDataType.NEWS


class ChartLoadEvent(LoadEvent):
    _data_type = EventDataType.CHART


class UpdateEvent(DataTypedEvent):
    """
    This type of event should be sent on update.
    It has single update of chart or news.
    """

    _type = EventType.UPDATE


class NewsUpdateEvent(UpdateEvent):
    _data_type = "news"


class ChartUpdateEvent(UpdateEvent):
    _data_type = "chart"


class StopStreamEvent(Event):
    """This event has to be sent on the end of the game."""

    _type = EventType.STREAM_STOP

    def __init__(self):
        super().__init__(None)
