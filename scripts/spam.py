import asyncio
from time import perf_counter
import aiohttp


async def fetch(s, url):
    async with s.get(url) as r:
        if r.status != 200:
            r.raise_for_status()
        return await r.text()


async def spam(s, count: int):
    tasks = []
    for _ in range(count):
        task = asyncio.create_task(fetch(s, "http://0.0.0.0:8555/add"))
        tasks.append(task)
    res = await asyncio.gather(*tasks)
    return res

async def main():
    async with aiohttp.ClientSession() as session:
        htmls = await spam(session, 1000)
        print(htmls)

if __name__ == '__main__':
    start = perf_counter()
    asyncio.run(main())
    stop = perf_counter()
    print("time taken:", stop - start)