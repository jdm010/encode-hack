import json
import os
import asyncio
from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI, AsyncOpenAI

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# Make sure you set your API key in your environment variables or assign it directly here.
client = AsyncOpenAI(api_key=OPENAI_API_KEY)

async def acquire_rate_limit(rate_limiter):
    await rate_limiter.acquire()
    # Schedule a release after 1 second so that at most 5 calls start per second.
    asyncio.create_task(release_rate_limit(rate_limiter))

async def release_rate_limit(rate_limiter):
    await asyncio.sleep(1)
    rate_limiter.release()

async def evaluate_article(article, rate_limiter):
    """
    Uses the ChatGPT API to decide whether an article is relevant.
    Returns True if the article is relevant (the model answers "keep").
    """
    title = article.get("title", "")
    description = article.get("description", "")
    url = article.get("url", "")
    extra = article.get("extra_snippets", "")

    prompt = (
        "You are an expert financial news analyst. Evaluate the following news article and decide if it is relevant for a financial data company "
        "whose clients are mainly hedge funds, asset management firms, brokers, and sell side firms. Relevant news includes topics such as recruiting, "
        "investment in equities, mergers & acquisitions, regulatory updates, product launches, and other strategic financial moves. The article details are:\n\n"
        f"Title: {title}\n"
        f"Description: {description}\n"
        f"URL: {url}\n"
        f"Extra snippets: {extra}\n\n"
        "Respond with only 'keep' if the article is relevant and reliable, or 'remove' if it is irrelevant, a duplicate, or from an unreliable source."
    )

    try:
        await acquire_rate_limit(rate_limiter)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful financial news analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0  # making responses deterministic
        )
        answer = response.choices[0].message.content.strip().lower()
        return answer == "keep"
    except Exception as e:
        print(f"Error evaluating article '{title}': {e}")
        return False

async def score_article(article, rate_limiter):
    """
    Uses the ChatGPT API to return a relevance and reliability score from 1 to 10.
    Higher scores indicate that the article is both relevant and from a reliable source.
    """
    title = article.get("title", "")
    description = article.get("description", "")
    url = article.get("url", "")
    extra = article.get("extra_snippets", "")

    prompt = (
        "You are an expert financial news analyst. Evaluate the following news article and assign it a score "
        f"Title: {title}\n"
        f"Description: {description}\n"
        f"URL: {url}\n"
        f"Extra snippets: {extra}\n\n"
    )

    try:
        await acquire_rate_limit(rate_limiter)
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful financial news analyst."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0  # deterministic response
        )
        score_text = response.choices[0].message.content.strip()
        score = float(score_text)
        return score
    except Exception as e:
        print(f"Error scoring article '{title}': {e}")
        # In case of error, return a low score
        return 0.0

async def process_category(category, articles, seen_titles, rate_limiter):
    scored_articles = []
    for article in articles:
        title = article.get("title", "").strip()
        if not title:
            continue  # Skip articles without a title
        # Check for duplicates based on title
        if title in seen_titles:
            continue
        seen_titles.add(title)
        # First, determine if the article should be kept
        if await evaluate_article(article, rate_limiter):
            # If yes, then get its relevance score
            score = await score_article(article, rate_limiter)
            article["score"] = score  # store the score for later sorting
            scored_articles.append(article)
        else:
            print(f"Removed article: {title}")
    # Sort the articles by score (descending) and choose up to 3 articles
    scored_articles.sort(key=lambda a: a.get("score", 0), reverse=True)
    return category, scored_articles[:3]

async def filter_articles(input_news: dict):
    """
    Processes the input news dictionary, filtering and scoring articles for each category.
    """
    filtered_data = {}
    seen_titles = set()
    # Define the rate limiter here instead of at the global level.
    rate_limiter = asyncio.Semaphore(5)
    tasks = []
    # Process each category (e.g., companies) concurrently.
    for category, articles in input_news.items():
        tasks.append(process_category(category, articles, seen_titles, rate_limiter))
    results = await asyncio.gather(*tasks)
    for category, articles in results:
        filtered_data[category] = articles

    print("Filtered news processed")
    return filtered_data
