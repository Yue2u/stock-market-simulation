import asyncio
import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from admin_api import router, secret_uid

# Import configuration
from config import FRONTEND_DIR, LOG_FORMAT, LOG_LEVEL
from pubsub import Publisher, Subscriber
from stock import StockMarketController

# Configure logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


async def stream():
    sub = Subscriber()
    Publisher.subscribe(sub)

    # Send current progress to user (chart and news by rounds)
    await StockMarketController.publish_until_current_step_data(sub.uid)
    await StockMarketController.publish_until_current_step_news(sub.uid)

    # Stream updates
    async for data in sub.listen():
        print("sending", data, flush=True)
        yield f"data: {data}\n\n"

    Publisher.unsubscribe(sub)


from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    cleanup_task = asyncio.create_task(Publisher.start_cleanup_task())
    logger.info("Stock market simulation server started")

    yield

    # Shutdown
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    await Publisher.cleanup_stale_subscribers(0)  # Remove all subscribers
    logger.info("Stock market simulation server stopped")


app = FastAPI(lifespan=lifespan)
app.include_router(router)


@app.get("/stream")
async def stream_data():
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Index file not found")
    return FileResponse(str(index_path))


@app.get(f"/__admin__/{secret_uid}", response_class=HTMLResponse)
async def serve_admin():
    admin_path = FRONTEND_DIR / "admin.html"
    if not admin_path.exists():
        raise HTTPException(status_code=404, detail="Admin file not found")

    try:
        with open(admin_path, "r", encoding="utf-8") as f:
            content = f.read()
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to read admin file: {e}")

    # Inject the admin URL into the HTML
    content = content.replace(
        "adminBaseUrl = '';", f"adminBaseUrl = '/__admin__/{secret_uid}';"
    )

    return HTMLResponse(content=content)


@app.get("/api/currencies")
async def get_currencies():
    """Get available currencies from chart data"""
    from config import REQUIRED_CURRENCIES

    return {"currencies": REQUIRED_CURRENCIES}
