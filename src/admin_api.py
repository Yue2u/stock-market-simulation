from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from stock import StockMarketController

secret_uid = uuid4().hex

print(f"Secret admin_url is /__admin__/{secret_uid}", flush=True)

router = APIRouter(prefix=f"/__admin__/{secret_uid}")


@router.get("/service_info")
async def get_service_info():
    return {
        "current_prices": StockMarketController.get_current_step_chart(),
        "current_news": StockMarketController.get_current_step_news(),
        "current_round_number": StockMarketController.stock().current_step,
        "next_prices": StockMarketController.get_next_step_chart(),
        "next_news": StockMarketController.get_next_step_news(),
    }


@router.post("/next_round")
async def next_round():
    """Start next round + publish chart data for round"""

    await StockMarketController.next_step()
    await StockMarketController.publish_current_chart_data()

    return {"status": "OK"}


@router.post("/publish_news")
async def publish_news():
    await StockMarketController.publish_current_news()
    return {"status": "OK"}


class RoundUpdateData(BaseModel):
    round_number: int
    chart_data: dict[str, int] | None = None
    news: list[str] | None = None


@router.post("/edit_round")
async def edit_round(data: RoundUpdateData):
    if data.chart_data:
        await StockMarketController.stock().update_step_data(
            data.round_number, data.chart_data
        )
    if data.news:
        await StockMarketController.stock().update_step_news(
            data.round_number, data.news
        )

    return {"status": "OK"}


@router.post("/go_to_step/{step}")
async def go_to_step(step: int):
    StockMarketController.stock().set_step(step)
    await StockMarketController.publish_until_current_step_data_all()
    await StockMarketController.publish_until_current_step_news_all()


@router.post("/finish_game")
async def stop_game():
    await StockMarketController.publish_stop_game()


@router.post("/reset")
async def reset():
    await StockMarketController.reset()
