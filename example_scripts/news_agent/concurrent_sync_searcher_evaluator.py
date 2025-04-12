import asyncio
import aiohttp
import json
import os
import pandas as pd
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

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
    params = {"q": search_query, "freshness": "pw"}
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

async def evaluate_result(result, company, openai_semaphore: asyncio.Semaphore):
    """
    Evaluate a single search result with OpenAI to check its relevance.
    Uses a semaphore to allow up to 5 concurrent OpenAI requests.
    """
    prompt = (
        "Determine if the following news article is actually about the specified company. "
        "Your response should focus only on whether the article is relevant to the company and nothing else. "
        "If the article is about the company, at the end of your answer include a separate line with 'Relevance: Yes'.\n"
        "If the article is not about the company, include two separate lines at the end: one with 'Relevance: No' "
        "and another line with 'Article Topic: <brief summary of what the article is about>'.\n\n"
        f"Company: {company}\n"
        f"Title: {result['title']}\n"
        f"Description: {result['description']}\n"
        f"URL: {result['url']}\n"
        f"Extra Snippets: {result.get('extra_snippets', [])}"
    )
    try:
        async with openai_semaphore:
            response = await client.chat.completions.create(
                model="gpt-4o-mini",  # or use gpt-4 if available
                messages=[
                    {"role": "system", "content": "You are a financial news evaluation assistant."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=150,
            )
            evaluation = response.choices[0].message.content.strip()
            # Wait briefly to maintain rate limits (approx. 5 per second)
            await asyncio.sleep(0.2)
    except Exception as e:
        logger.error(f"OpenAI evaluation error: {e}")
        evaluation = "Evaluation failed. Relevance: No\nArticle Topic: Evaluation error."
    return evaluation

async def process_query(company: str, query: str, session: aiohttp.ClientSession,
                        brave_semaphore: asyncio.Semaphore, openai_semaphore: asyncio.Semaphore):
    """
    For one search query:
      - Call the Brave Search API with the brave_semaphore.
      - Evaluate each returned article concurrently using OpenAI with the openai_semaphore.
    """
    evaluated_results = []
    search_response = await brave_search(query, session, brave_semaphore)
    if isinstance(search_response, dict) and "error" in search_response:
        logger.error(f"Search error for query '{query}': {search_response['error']}")
        return evaluated_results

    # Prepare evaluation tasks for each unique article.
    tasks = []
    result_mapping = []
    seen_urls = set()
    for result in search_response:
        url = result.get("url", "N/A")
        if url in seen_urls:
            continue
        seen_urls.add(url)
        tasks.append(asyncio.create_task(evaluate_result(result, company, openai_semaphore)))
        result_mapping.append(result)
    
    if tasks:
        evaluations = await asyncio.gather(*tasks)
        for result, eval_text in zip(result_mapping, evaluations):
            result["evaluation"] = eval_text
            if "Relevance: Yes" in eval_text:
                evaluated_results.append(result)
            else:
                logger.info(f"Filtered out article for {company}. Evaluation:\n{eval_text}")
    return evaluated_results

async def process_company(company: str, session: aiohttp.ClientSession,
                          brave_semaphore: asyncio.Semaphore, openai_semaphore: asyncio.Semaphore):
    """
    For one company, process the search query using only the company name.
    """
    results = await process_query(company, company, session, brave_semaphore, openai_semaphore)
    return results

async def scraper(company_names: pd.DataFrame):
    """
    Main asynchronous scraper:
      - Reads companies from a DataFrame.
      - Processes each company concurrently.
      - Returns the aggregated news results.
    """
    all_news = {}
    # Create semaphores for rate limiting.
    brave_semaphore = asyncio.Semaphore(1)   # One Brave API request per second.
    openai_semaphore = asyncio.Semaphore(5)    # Allow up to 5 concurrent OpenAI requests.

    async with aiohttp.ClientSession() as session:
        # Create a concurrent task for each company.
        tasks = []
        company_list = []
        for _, row in company_names.iterrows():
            company = row["company"]
            company_list.append(company)
            tasks.append(asyncio.create_task(
                process_company(company, session, brave_semaphore, openai_semaphore)
            ))
        
        company_results = await asyncio.gather(*tasks)
        for company, results in zip(company_list, company_results):
            all_news[company] = results
            logger.info(f"Completed processing for {company}")

    # Optionally, write to a JSON file.
    # with open("march_06_news_past_week_concurrent_full.json", "w", encoding="utf-8") as f:
    #     json.dump(all_news, f, indent=4, ensure_ascii=False)

    return all_news
