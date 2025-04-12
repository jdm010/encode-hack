import asyncio
import aiohttp
import os
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
brave_semaphore = asyncio.Semaphore(1)  # Limit to 1 request per second


async def brave_search(search_query: str, session: aiohttp.ClientSession):
    """
    Query the Brave Search API asynchronously with a rate limit.
    """
    url = "https://api.search.brave.com/res/v1/news/search"
    headers = {
        "Accept": "application/json",
        "Accept-encoding": "gzip",
        "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
    }
    params = {"q": search_query}

    async with brave_semaphore:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                extracted_data = [
                    {
                        "title": item.get("title", "N/A"),
                        "url": item.get("url", "N/A"),
                        "description": item.get("description", "N/A"),
                        "page_age": item.get("page_age", "N/A"),
                        "age": item.get("age", "N/A"),
                        "extra_snippets": item.get("extra_snippets", []),
                    }
                    for item in data.get("results", [])
                ]
            else:
                extracted_data = {"error": f"Request failed with status code {response.status}"}
        await asyncio.sleep(1)  # Enforce rate limit
    return extracted_data


@app.get("/search")
async def search_news(q: str = Query(..., description="Search query for Brave News API")):
    async with aiohttp.ClientSession() as session:
        result = await brave_search(search_query=q, session=session)
        return JSONResponse(content=result)
