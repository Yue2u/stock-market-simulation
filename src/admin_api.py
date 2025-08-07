from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from stock import StockMarketController

secret_uid = uuid4().hex

print(f"Secret admin_url is /__admin__/{secret_uid}", flush=True)

router = APIRouter(prefix=f"/__admin__/{secret_uid}")


@router.get("/service_info")
async def get_service_info():
    from config import REQUIRED_CURRENCIES

    return {
        "current_prices": StockMarketController.get_current_step_chart(),
        "current_news": StockMarketController.get_current_step_news(),
        "current_round_number": StockMarketController.stock().current_step_chart,
        "next_prices": StockMarketController.get_next_step_chart(),
        "next_news": StockMarketController.get_next_step_news(),
        "available_currencies": REQUIRED_CURRENCIES,
    }


@router.post("/next_round")
async def next_round():
    """Start next round + publish chart data for round"""
    try:
        success = await StockMarketController.next_chart_step()
        if not success:
            return {"status": "warning", "message": "Already at last round"}

        await StockMarketController.publish_current_chart_data()
        return {"status": "success", "message": "Advanced to next round"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/publish_news")
async def publish_news():
    try:
        success = await StockMarketController.publish_current_news()
        if success:
            return {"status": "success", "message": "News published successfully"}
        else:
            return {
                "status": "warning",
                "message": "Cannot publish news: constraint violation or already at last news step",
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}


class RoundUpdateData(BaseModel):
    round_number: int
    chart_data: dict[str, int] | None = None
    news: list[str] | None = None


@router.post("/edit_round")
async def edit_round(data: RoundUpdateData):
    try:
        if data.round_number < 0:
            return {"status": "error", "message": "Round number must be non-negative"}

        stock = StockMarketController.stock()
        if data.round_number >= len(stock.data):
            return {
                "status": "error",
                "message": f"Round {data.round_number} exceeds available data",
            }

        if data.chart_data:
            # Validate chart data structure
            from config import REQUIRED_CURRENCIES

            required_currencies = REQUIRED_CURRENCIES
            if not all(currency in data.chart_data for currency in required_currencies):
                return {
                    "status": "error",
                    "message": f"Chart data must contain all currencies: {required_currencies}",
                }

            if not all(
                isinstance(price, (int, float)) and price >= 0
                for price in data.chart_data.values()
            ):
                return {
                    "status": "error",
                    "message": "All prices must be non-negative numbers",
                }

            success = stock.update_step_data(data.round_number, data.chart_data)
            if not success:
                return {"status": "error", "message": "Failed to update chart data"}

        if data.news:
            if not isinstance(data.news, list) or not all(
                isinstance(item, str) for item in data.news
            ):
                return {"status": "error", "message": "News must be a list of strings"}

            success = stock.update_step_news(data.round_number, data.news)
            if not success:
                return {"status": "error", "message": "Failed to update news data"}

        await StockMarketController.publish_until_current_step_data_all()
        await StockMarketController.publish_until_current_step_news_all()

        return {
            "status": "success",
            "message": f"Round {data.round_number} updated successfully",
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/go_to_step/{step}")
async def go_to_step(step: int):
    try:
        if step < 0:
            return {"status": "error", "message": "Step must be non-negative"}

        stock = StockMarketController.stock()
        if step >= len(stock.data):
            return {
                "status": "error",
                "message": f"Step {step} exceeds available data (max: {len(stock.data)-1})",
            }

        stock.set_chart_step(step)
        stock.set_news_step(step - 1)
        await StockMarketController.publish_until_current_step_data_all()
        await StockMarketController.publish_until_current_step_news_all()

        return {"status": "success", "current_step": step}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/finish_game")
async def stop_game():
    try:
        await StockMarketController.publish_stop_game()
        return {"status": "success", "message": "Game finished successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.post("/reset")
async def reset():
    try:
        await StockMarketController.reset()
        return {"status": "success", "message": "Game reset successfully"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
