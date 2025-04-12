import json
import os
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from typing import List, Dict, Any
from langchain.tools import tool
from langchain_core.messages import AIMessage

app = FastAPI()

########################################
# 1. File-based Storage Setup
########################################

DATA_FILEPATH = "crypto_sentiments.json"

# Helper to load existing sentiments from file
def load_sentiments_from_file(filepath: str) -> Dict[str, str]:
    if not os.path.exists(filepath):
        return {}
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

# Helper to save sentiments to file
def save_sentiments_to_file(filepath: str, data: Dict[str, str]):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# In-memory dictionary is populated at app startup,
# but is always in-sync with the file.
crypto_sentiments: Dict[str, str] = load_sentiments_from_file(DATA_FILEPATH)

########################################
# 2. LLM and Tools Setup (Same as before)
########################################

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

@tool
def brave_search(query: str, result_count: int = 1) -> List[Dict[str, Any]]:
    """
    Searches BraveSearch for the recent crypto information/news
    
    Args:
        query: The search query for crypto info (The market sentiment, recent legislation etc.)
        result_count: The number of results to return
        
    Returns:
        A list of news articles with titles, desc, URL, and published date
    """
    import asyncio
    import aiohttp
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")

    async def _brave_search():
        async with aiohttp.ClientSession() as session:
            url = "https://api.search.brave.com/res/v1/news/search"
            headers = {
                "Accept": "application/json",
                "Accept-encoding": "gzip", 
                "X-Subscription-Token": BRAVE_SEARCH_API_KEY,
            }
            params = {"q": query, "freshness": "pd"}
            
            async with session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    extracted_data = []
                    for item in data.get("results", [])[:result_count]:
                        extracted_data.append({
                            "title": item.get("title", "N/A"),
                            "url": item.get("url", "N/A"),
                            "description": item.get("description", "N/A"),
                            "page_age": item.get("page_age", "N/A"),
                            "age": item.get("age", "N/A"),
                            "extra_snippets": item.get("extra_snippets", []),
                        })
                    return extracted_data
                else:
                    return [{"error": f"Request failed with status code {response.status}"}]

    return asyncio.run(_brave_search())

tools = [brave_search]
agent = create_react_agent(llm, tools=tools)

########################################
# 3. Request Body Schemas
########################################

class QueryRequest(BaseModel):
    query: str

########################################
# 4. Endpoint: General Query
########################################

@app.post("/ask")
async def ask_question(request: QueryRequest):
    query = request.query
    messages = [HumanMessage(content=query)]
    result = agent.invoke({"messages": messages})

    # Extract only the final AIMessage content
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            return {
                "query": query,
                "response": msg.content
            }

    return {
        "query": query,
        "response": "Sorry, I couldn't find a response."
    }

########################################
# 5. Endpoint: Fetch and Store Crypto Sentiments
########################################

@app.post("/fetch-crypto-sentiments")
async def fetch_and_store_crypto_sentiments():
    """
    Queries BraveSearch (through the agent) for the sentiment of the main cryptocurrencies
    and stores them in a local JSON file.
    """
    main_coins = ["bitcoin", "ethereum", "ripple", "cardano", "dogecoin"]
    new_data = {}

    for coin in main_coins:
        query = f"What is the current crypto sentiment for {coin}?"
        messages = [HumanMessage(content=query)]
        result = agent.invoke({"messages": messages})

        # Extract the final AIMessage
        ai_msg_content = "No sentiment found."
        for msg in reversed(result["messages"]):
            if isinstance(msg, AIMessage):
                ai_msg_content = msg.content
                break

        new_data[coin] = ai_msg_content

    # Update both in-memory dictionary and JSON file
    crypto_sentiments.update(new_data)
    save_sentiments_to_file(DATA_FILEPATH, crypto_sentiments)

    return {
        "updated_sentiments": new_data
    }

########################################
# 6. Endpoint: Retrieve Stored Crypto Sentiments
########################################

@app.get("/crypto-sentiments")
async def get_stored_crypto_sentiments():
    """
    Returns the stored sentiments from crypto_sentiments.json (loaded in memory).
    """
    return crypto_sentiments
