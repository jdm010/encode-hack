from concurrent_sync_searcher_evaluator import scraper
from interim_evaluator import filter_articles
import asyncio
import pandas as pd
import requests
from loguru import logger
import json
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import select

from service.models import NewsArticleModel

COMPANY_NAMES = pd.read_csv("")
TEST_WEBHOOK = ""  # test channel
MAIN_WEBHOOK = ""  # main channel

def send_slack_message(news_items: dict, slack_webhook_url: str) -> None:
    """Send a Slack message for each client with news items."""
    # Iterate over each client in the news_items data
    for client, articles in news_items.items():
        # Only send a message if there is at least one news item
        if articles:
            # Build the message text. Here we list each news title as a bullet with a clickable URL.
            message = f"*News for {client}:*\n"
            for item in articles:
                # Slack format for clickable link: <URL|Title>
                message += f"- <{item['url']}|{item['title']}>\n"
            
            # Construct the payload for the Slack webhook
            payload = {"text": message}
            
            # Send the message via POST request
            response = requests.post(slack_webhook_url, json=payload)
            
            if response.status_code != 200:
                logger.error("Error sending message for %s: %s", client, response.text)
            else:
                logger.info("Message sent for %s", client)

async def process_article(company_name: str, article: dict, session):
    """Check if the article exists in the database and add it if new.
    
    Returns a minimal dict with the article details (for Slack) if inserted,
    otherwise returns None.
    """
    try:
        title = article['title']
        url = article['url']
        page_age_str = article['page_age']
        evaluation = article['evaluation']
        description = article.get('description')
    except KeyError as e:
        logger.error("Missing key %s for company '%s'", e, company_name)
        return None

    try:
        page_age = datetime.fromisoformat(page_age_str)
    except ValueError as e:
        logger.error("Invalid datetime format for article '%s': %s", title, e)
        return None

    extra_snippets = article.get('extra_snippets')
    if isinstance(extra_snippets, list):
        extra_snippets = "\n".join(extra_snippets)

    # Check if the article exists in the database
    statement = select(NewsArticleModel).where(NewsArticleModel.url == url)
    result = await session.exec(statement)
    if result.first():
        logger.info("Article '%s' already exists for company '%s'", title, company_name)
        return None

    # Create and add the new article
    news_article = NewsArticleModel(
        company_name=company_name,
        title=title,
        url=url,
        description=description,
        page_age=page_age,
        extra_snippets=extra_snippets,
        evaluation=evaluation
    )
    session.add(news_article)
    logger.info("Added article '%s' for company '%s'", title, company_name)
    
    # Return minimal information for the Slack message
    return {'title': title, 'url': url}

# @async_db_session
async def store_record(input_news, session):
    """Store new articles in the database and return a dict of newly added articles."""
    if session is None:
        logger.error("No session provided")
        raise HTTPException(status_code=500, detail="No database session provided")

    try:
        data = input_news
    except (FileNotFoundError, json.JSONDecodeError) as ex:
        logger.error("Error processing JSON file: %s", ex)
        raise HTTPException(status_code=500, detail=str(ex))

    new_articles = {}
    try:
        for company_name, articles in data.items():
            if not articles:
                logger.info("No articles found for company '%s'", company_name)
                continue
            new_articles[company_name] = []
            for article in articles:
                result = await process_article(company_name, article, session)
                if result:
                    new_articles[company_name].append(result)
        await session.commit()
        logger.info("All records committed successfully.")
        return new_articles
    except (IntegrityError, SQLAlchemyError) as ex:
        await session.rollback()
        logger.error("Database error occurred: %s", ex)
        raise HTTPException(status_code=500, detail=f"Error storing record: {ex}")
    except Exception as ex:
        logger.exception("An unexpected error occurred: %s", ex)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {ex}")

async def main(company_names, slack_webhook_url) -> None:
    """Run the entire process, storing new articles in the database before sending Slack messages."""
    logger.info("Started process")
    
    all_news = await scraper(company_names)
    logger.info("Retrieved news")
    
    filtered_news = await filter_articles(all_news)
    logger.info("Filtered news")
    
    # Store new articles in the database and get back those that were added
    new_articles = await store_record(filtered_news)
    logger.info("Stored new articles in database")
    
    # Only send Slack messages for companies with new articles
    if any(new_articles.values()):
        send_slack_message(new_articles, slack_webhook_url)
        count = sum(len(lst) for lst in new_articles.values())
        logger.info("Slack message sent for %d new item(s)", count)
    else:
        logger.info("No new articles to send")

# Example of running the main function with test webhook
if __name__ == "__main__":
    asyncio.run(main(COMPANY_NAMES, MAIN_WEBHOOK))
