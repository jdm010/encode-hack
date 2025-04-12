import streamlit as st
import requests

# Title and description
st.title("🧠 Crypto News Agent")
st.write("Ask about recent crypto news, sentiment, or regulations. The agent will search and reason based on fresh info.")

# Input field
query = st.text_input("Enter your query:", placeholder="e.g., What's the latest on Bitcoin ETFs?")

# API endpoint URL
API_URL = "http://localhost:8000/ask"  # Update if your FastAPI is hosted elsewhere

# Submit button
if st.button("Ask"):
    if not query.strip():
        st.warning("Please enter a query.")
    else:
        with st.spinner("Thinking..."):
            try:
                response = requests.post(API_URL, json={"query": query})
                if response.status_code == 200:
                    data = response.json()
                    st.success("Response:")
                    for msg in data.get("responses", []):
                        st.markdown(f"**{msg['type']}**: {msg['content']}")
                else:
                    st.error(f"API error: {response.status_code} - {response.text}")
            except Exception as e:
                st.error(f"Error: {e}")
