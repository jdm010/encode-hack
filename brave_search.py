import asyncio
import aiohttp
import os
from dotenv import load_dotenv
load_dotenv()

BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")


async def brave_search(search_query: str, session: aiohttp.ClientSession, brave_semaphore: asyncio.Semaphore):
    """
    Query the Brave Search API asynchronously.
    Enforces one request per second using a semaphore.
    """
    url = "https://api.search.brave.com/res/v1/news/search"
    headers = {
        "Accept": "application/json",
        "Accept-encoding": "gzip",
        "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
    }
    # params = {"q": search_query, "freshness": "pw"} # searches past week
    params = {"q": search_query}
    async with brave_semaphore:
        async with session.get(url, headers=headers, params=params) as response:
            if response.status == 200:
                data = await response.json()
                extracted_data = []
                for item in data.get("results", []):
                    extracted_data.append({
                        "title": item.get("title", "N/A"),
                        "url": item.get("url", "N/A"),
                        "description": item.get("description", "N/A"),
                        "page_age": item.get("page_age", "N/A"),
                        "age": item.get("age", "N/A"),
                        "extra_snippets": item.get("extra_snippets", []),
                    })
            else:
                extracted_data = {"error": f"Request failed with status code {response.status}"}
        # Wait 1 second to respect Brave API rate limits.
        await asyncio.sleep(1)
    return extracted_data


async def run():
    async with aiohttp.ClientSession() as session:
        query = await brave_search(search_query="tell me news about crypto",session=session,brave_semaphore=asyncio.Semaphore(1))
        print(query)
        return query

result = asyncio.run(run())
