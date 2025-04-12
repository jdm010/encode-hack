import streamlit as st
import requests

# Adjust these to point to your FastAPI service
API_BASE_URL = "http://localhost:8000"

# Main coins to display
MAIN_COINS = ["bitcoin", "ethereum", "ripple", "cardano", "dogecoin"]

###############################
# 1. Helper Functions
###############################
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

def get_stored_sentiments() -> dict:
    """
    Calls the /crypto-sentiments endpoint to retrieve stored sentiments.
    """
    try:
        resp = requests.get(f"{API_BASE_URL}/crypto-sentiments")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Error retrieving sentiments: {e}")
    return {}

def ask_for_coin_sentiment(coin_name: str) -> str:
    """
    Calls the /ask endpoint with a query: "What is the current crypto sentiment for {coin_name}?"
    Returns the LLM-based response as a string.
    """
    query = f"What is the current crypto sentiment for {coin_name}?"
    payload = {"query": query}
    try:
        resp = requests.post(f"{API_BASE_URL}/ask", json=payload)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("response", "No response.")
    except Exception as e:
        st.error(f"Error calling /ask: {e}")
    return "Unable to retrieve sentiment."

###############################
# 2. Main Streamlit App
###############################
def main():
    # Set a page title & layout
    st.set_page_config(page_title="Crypto Sentiment Dashboard", layout="wide")

    # Sidebar: set some branding or a simple image
    st.sidebar.title("Navigation")
    page_selection = st.sidebar.selectbox("Go to page:", ["Home"] + MAIN_COINS)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**© 2025 MyCryptoApp**")

    if page_selection == "Home":
        show_home_page()
    else:
        show_coin_page(page_selection)

def show_home_page():
    st.title("Crypto Sentiment Dashboard")
    st.write(
        """
        Welcome! This dashboard displays the most recent sentiment for
        some of the major cryptocurrencies.  
        
        **Click on a coin in the sidebar** to see a detailed page 
        and to re-run the semantic analysis for that specific coin.
        """
    )
    st.markdown("---")

    # Fetch stored sentiments
    sentiments = get_stored_sentiments()

    st.header("Overall Sentiments")
    # We'll display coins in a row-based layout
    num_cols = 3
    cols = st.columns(num_cols)

    for idx, coin in enumerate(MAIN_COINS):
        sentiment_text = sentiments.get(coin, "No sentiment found.")
        classification = classify_sentiment(sentiment_text)

        # Decide how to display the classification
        if classification == "Bullish":
            emoji = "🚀"
            color_box = "darkgreen"
        elif classification == "Bearish":
            emoji = "🔻"
            color_box = "tomato"
        else:
            emoji = "🤔"
            color_box = "#292929"

        # Put each coin card in the appropriate column
        with cols[idx % num_cols]:
            st.markdown(
                f"""
                <div style="
                    background-color: {color_box}; 
                    padding: 1rem; 
                    border-radius: 0.5rem;
                    margin-bottom: 1rem;
                ">
                    <h4 style="margin-top: 0; margin-bottom: 0.5rem;">
                        {coin.capitalize()} {emoji}
                    </h4>
                    <strong>{classification}</strong><br>
                    <small>{sentiment_text}</small>
                </div>
                """,
                unsafe_allow_html=True
            )

def show_coin_page(coin: str):
    st.title(f"{coin.capitalize()} Detailed Sentiment")
    stored_sentiments = get_stored_sentiments()
    current_sentiment = stored_sentiments.get(coin, "No sentiment available.")

    # Show stored sentiment
    st.subheader("Stored Sentiment")
    stored_classification = classify_sentiment(current_sentiment)
    display_sentiment_box(coin, stored_classification, current_sentiment)
    
    st.write("---")

    # Button to refresh sentiment analysis
    st.subheader("Refresh / Re-run Sentiment Analysis")
    st.write("Click the button below to fetch the latest LLM-based sentiment:")

    if st.button("Re-run semantic analysis"):
        new_sentiment = ask_for_coin_sentiment(coin)
        new_classification = classify_sentiment(new_sentiment)
        
        st.markdown("**Fresh Analysis**")
        display_sentiment_box(coin, new_classification, new_sentiment)

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

if __name__ == "__main__":
    main()
