from fastapi import FastAPI, Request
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from typing import List,Dict,Any

# Reuse your existing LLM and tool setup
# (Assuming llm and brave_search tool have already been defined as in your code)
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)
# Create FastAPI app
app = FastAPI()

# Input schema for requests
class QueryRequest(BaseModel):
    query: str

from langchain.tools import tool


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
            params = {"q": query,
                      "freshness": "pd"}
            
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


# Initialize the agent
tools = [brave_search]
agent = create_react_agent(llm, tools=tools)

@app.post("/ask")
async def ask_question(request: QueryRequest):
    query = request.query
    messages = [HumanMessage(content=query)]
    result = agent.invoke({"messages": messages})
    
    formatted_response = []
    
    for msg in result["messages"]:
        message_type = type(msg).__name__
        content = getattr(msg, "content", str(msg))
        formatted_response.append({
            "type": message_type,
            "content": content
        })
    
    return {
        "query": query,
        "responses": formatted_response
    }

