import json
import os
import streamlit as st
import asyncio
import aiohttp
from typing import List, Dict, Any
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
from langchain.tools import tool

# Main coins to display
MAIN_COINS = ["bitcoin", "ethereum", "ripple", "cardano", "dogecoin"]

# File-based Storage Setup
DATA_FILEPATH = "crypto_sentiments.json"

# Session state initialization
if 'crypto_sentiments' not in st.session_state:
    st.session_state.crypto_sentiments = {}
    if os.path.exists(DATA_FILEPATH):
        try:
            with open(DATA_FILEPATH, "r", encoding="utf-8") as f:
                st.session_state.crypto_sentiments = json.load(f)
        except json.JSONDecodeError:
            pass

# Helper to save sentiments to file
def save_sentiments_to_file(data: Dict[str, str]):
    with open(DATA_FILEPATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Load credentials from environment
load_dotenv()

# Tool setup
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
    BRAVE_SEARCH_API_KEY = os.getenv("BRAVE_SEARCH_API_KEY")
    if not BRAVE_SEARCH_API_KEY:
        return [{"error": "BRAVE_SEARCH_API_KEY not found in environment"}]

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

# LLM and Agent setup
@st.cache_resource
def get_agent():
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0
    )
    tools = [brave_search]
    return create_react_agent(llm, tools=tools)

# Helper Functions
def classify_sentiment(sentiment_text: str) -> str:
    """
    A naive classification that checks for bullish, bearish,
    and related sentiment keywords. Defaults to 'Neutral'.
    """
    text_lower = sentiment_text.lower()

    bullish_keywords = ["bullish", "positive", "optimistic", "uptrend", "buy", "long"]
    bearish_keywords = ["bearish", "negative", "pessimistic", "downtrend", "sell", "short"]

    if any(word in text_lower for word in bullish_keywords):
        return "Bullish"
    elif any(word in text_lower for word in bearish_keywords):
        return "Bearish"
    return "Neutral"

def ask_for_coin_sentiment(coin_name: str) -> str:
    """
    Uses the agent to get sentiment for a specific coin
    """
    agent = get_agent()
    query = f"What is the current crypto sentiment for {coin_name}?"
    messages = [HumanMessage(content=query)]
    result = agent.invoke({"messages": messages})

    # Extract the final AIMessage
    for msg in reversed(result["messages"]):
        if isinstance(msg, AIMessage):
            return msg.content

    return "Unable to retrieve sentiment."

def fetch_and_store_crypto_sentiments():
    """
    Fetches sentiment for all main coins and stores them
    """
    new_data = {}
    for coin in MAIN_COINS:
        with st.status(f"Analyzing {coin}..."):
            sentiment = ask_for_coin_sentiment(coin)
            new_data[coin] = sentiment
    
    # Update both session state and JSON file
    st.session_state.crypto_sentiments.update(new_data)
    save_sentiments_to_file(st.session_state.crypto_sentiments)
    return new_data

def update_single_sentiment(coin: str):
    """
    Updates sentiment for a specific coin
    """
    with st.status(f"Analyzing {coin}..."):
        sentiment = ask_for_coin_sentiment(coin)
        st.session_state.crypto_sentiments[coin] = sentiment
        save_sentiments_to_file(st.session_state.crypto_sentiments)
    return sentiment

def display_sentiment_box(coin_name: str, classification: str, sentiment_text: str):
    if classification == "Bullish":
        emoji = "🚀"
        color_box = "darkgreen"
    elif classification == "Bearish":
        emoji = "🔻"
        color_box = "tomato"
    else:
        emoji = "🤔"
        color_box = "#292929"

    st.markdown(
        f"""
        <div style="
            background-color: {color_box}; 
            padding: 1rem; 
            border-radius: 0.5rem;
        ">
            <h4 style="margin-top: 0; margin-bottom: 0.5rem;">
                {coin_name.capitalize()} {emoji}
            </h4>
            <strong>{classification}</strong><br>
            <small>{sentiment_text}</small>
        </div>
        """,
        unsafe_allow_html=True
    )

def show_home_page():
    st.title("SentiFi")
    st.write(
        """
        A market sentiment analyzer for your DeFi portfolio.  
        
        **Click on a coin in the sidebar** to see a detailed page 
        and to re-run the sentiment analysis for that specific coin.
        
        You can also check **Custom Coin** to analyze any cryptocurrency.
        """
    )
    st.markdown("---")

    # Show refresh button for all sentiment data
    if st.button("Refresh All Sentiments"):
        with st.spinner("Fetching sentiment data for all coins..."):
            fetch_and_store_crypto_sentiments()
        st.success("All sentiments updated!")
        st.rerun()

    st.header("Overall Sentiments")
    # Display coins in a row-based layout
    num_cols = 3
    cols = st.columns(num_cols)

    for idx, coin in enumerate(MAIN_COINS):
        sentiment_text = st.session_state.crypto_sentiments.get(coin, "No sentiment found.")
        classification = classify_sentiment(sentiment_text)

        # Put each coin card in the appropriate column
        with cols[idx % num_cols]:
            display_sentiment_box(coin, classification, sentiment_text)
            if st.button(f"View {coin.capitalize()}", key=f"view_{coin}"):
                st.session_state.page_selection = coin
                st.rerun()

def show_custom_coin_page():
    st.title("Custom Coin Analysis")
    st.write("Enter any cryptocurrency name to analyze its sentiment.")
    
    custom_coin = st.text_input("Cryptocurrency Name:", 
                               placeholder="e.g., solana, polkadot, litecoin",
                               value=st.session_state.get('custom_coin', ''))
    
    if custom_coin:
        st.session_state.custom_coin = custom_coin
        
        # Button to run sentiment analysis on custom coin
        if st.button(f"Analyze {custom_coin}") or 'custom_analysis_done' in st.session_state:
            st.session_state.custom_analysis_done = True
            
            with st.spinner(f"Analyzing {custom_coin}..."):
                sentiment = ask_for_coin_sentiment(custom_coin)
            
            classification = classify_sentiment(sentiment)
            
            st.subheader(f"Analysis for {custom_coin.capitalize()}")
            display_sentiment_box(custom_coin, classification, sentiment)
            
            # Option to save this sentiment
            if st.button("Store this sentiment"):
                coin_key = custom_coin.lower()
                st.session_state.crypto_sentiments[coin_key] = sentiment
                save_sentiments_to_file(st.session_state.crypto_sentiments)
                st.success(f"Sentiment for {custom_coin} has been stored!")

def show_coin_page(coin: str):
    st.title(f"{coin.capitalize()} Detailed Sentiment")
    current_sentiment = st.session_state.crypto_sentiments.get(coin, "No sentiment available.")

    # Show stored sentiment
    st.subheader("Stored Sentiment")
    stored_classification = classify_sentiment(current_sentiment)
    display_sentiment_box(coin, stored_classification, current_sentiment)
    
    st.write("---")

    # Button to refresh sentiment analysis
    st.subheader("Refresh / Re-run Sentiment Analysis")
    st.write("Click the button below to fetch the latest LLM-based sentiment:")

    if st.button("Re-run sentiment analysis"):
        with st.spinner(f"Analyzing {coin}..."):
            new_sentiment = update_single_sentiment(coin)
        
        new_classification = classify_sentiment(new_sentiment)
        
        st.markdown("**Fresh Analysis**")
        display_sentiment_box(coin, new_classification, new_sentiment)

def main():
    # Set a page title & layout
    st.set_page_config(page_title="SentiFi", layout="wide")

    # Initialize session state variables
    if 'custom_coin' not in st.session_state:
        st.session_state.custom_coin = ""
    if 'page_selection' not in st.session_state:
        st.session_state.page_selection = "Home"

    # Sidebar: set some branding or a simple image
    st.sidebar.title("Navigation")
    page_options = ["Home", "Custom Coin"] + MAIN_COINS
    st.session_state.page_selection = st.sidebar.selectbox(
        "Go to page:", 
        page_options,
        index=page_options.index(st.session_state.page_selection)
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**© 2025 SentiFi**")

    # Check if we need to initialize sentiments
    if not st.session_state.crypto_sentiments and os.path.exists(DATA_FILEPATH):
        with open(DATA_FILEPATH, "r", encoding="utf-8") as f:
            try:
                st.session_state.crypto_sentiments = json.load(f)
            except json.JSONDecodeError:
                pass

    # Display the selected page
    if st.session_state.page_selection == "Home":
        show_home_page()
    elif st.session_state.page_selection == "Custom Coin":
        show_custom_coin_page()
    else:
        show_coin_page(st.session_state.page_selection)

if __name__ == "__main__":
    main()
