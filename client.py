import httpx
import uvloop
import asyncio


async def client():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            "https://stock-market-simulation.onrender.com/stream",
            timeout=None
        ) as stream:
            async for msg in stream.aiter_lines():
                print(msg)


async def main(clients: int = 1):
    await asyncio.gather(
        *[
            client()
            for _ in range(clients)
        ]
    )

uvloop.run(main(100))