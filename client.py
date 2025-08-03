import httpx
import uvloop


async def main():
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            "http://localhost:8000/stream",
            timeout=None
        ) as stream:
            async for msg in stream.aiter_lines():
                print(msg)


uvloop.run(main())