from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os

from admin_api import router, secret_uid
from pubsub import Publisher, Subscriber
from stock import StockMarketController

app = FastAPI()
app.include_router(router)


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


@app.get("/stream")
async def stream_data():
    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    return FileResponse("frontend/index.html")


@app.get(f"/__admin__/{secret_uid}", response_class=HTMLResponse)
async def serve_admin():
    with open("frontend/admin.html", "r") as f:
        content = f.read()
    
    # Inject the admin URL into the HTML
    content = content.replace(
        "adminBaseUrl = '';", 
        f"adminBaseUrl = '/__admin__/{secret_uid}';"
    )
    
    return HTMLResponse(content=content)
