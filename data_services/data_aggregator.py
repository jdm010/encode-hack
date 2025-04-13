"""Data aggregation module.

This module combines data from multiple sources (Santiment, CoinGecko) into a unified format
suitable for LLM processing.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
from agentipy.agent import SolanaAgentKit
from santiment_operations import SantimentAPI
import coingecko_operations
from logging_config import setup_logger
import json
import os

logger = setup_logger(__name__)

class DataAggregator:
    """Class to aggregate data from multiple sources."""

    def __init__(self, agent: SolanaAgentKit):
        """Initialize data aggregator.

        Args:
            agent: Initialized SolanaAgentKit instance for CoinGecko operations.
        """
        self.agent = agent
        self.santiment = SantimentAPI()
        logger.info("DataAggregator initialized with Santiment and CoinGecko connections")

    async def get_combined_metrics(self, token: str) -> Dict[str, Any]:
        """Get combined metrics from all data sources.

        Args:
            token: Token symbol (e.g., 'ETH', 'BTC').

        Returns:
            Dict[str, Any]: Combined metrics from all sources in a structured format.
        """
        logger.info(f"Fetching combined metrics for {token}")
        
        # Initialize result structure
        result = {
            "token": token,
            "timestamp": datetime.utcnow().isoformat(),
            "data_sources": {
                "santiment": None,
                "coingecko": None
            }
        }

        try:
            # Get Santiment data
            santiment_token = token.lower()
            if token.upper() == "ETH":
                santiment_token = "ethereum"
            elif token.upper() == "BTC":
                santiment_token = "bitcoin"
            elif token.upper() == "SOL":
                santiment_token = "solana"
            
            result["data_sources"]["santiment"] = self.santiment.get_token_metrics(santiment_token)
            logger.debug(f"Successfully fetched Santiment data for {token}")

        except Exception as e:
            logger.error(f"Failed to fetch Santiment data: {str(e)}")
            result["data_sources"]["santiment"] = {"error": str(e)}

        try:
            # Get CoinGecko data
            coingecko_data = await coingecko_operations.get_token_metrics(self.agent, token)
            if coingecko_data:
                result["data_sources"]["coingecko"] = {
                    "current_price": coingecko_data.get("usd"),
                    "market_cap": coingecko_data.get("usd_market_cap"),
                    "volume_24h": coingecko_data.get("usd_24h_vol"),
                    "price_change_24h": coingecko_data.get("usd_24h_change")
                }
                logger.debug(f"Successfully fetched CoinGecko data for {token}")
            else:
                logger.warning(f"No CoinGecko data available for {token}")

        except Exception as e:
            logger.error(f"Failed to fetch CoinGecko data: {str(e)}")
            result["data_sources"]["coingecko"] = {"error": str(e)}

        return result

    def format_for_llm(self, data: Dict[str, Any]) -> str:
        """Format the combined data in a way that's optimal for LLM processing.

        Args:
            data: Combined metrics data dictionary.

        Returns:
            str: Formatted string suitable for LLM input.
        """
        logger.debug("Formatting data for LLM consumption")
        
        # Convert to formatted JSON string
        formatted_data = json.dumps(data, indent=2)
        
        # Add a header with instructions for the LLM
        llm_format = f"""
# Token Analysis Data
The following JSON contains comprehensive token metrics from multiple sources.
Each metric includes historical data points, trends, and current values where available.
All numerical values are preserved in their original precision for accurate analysis.

{formatted_data}
"""
        return llm_format

async def main():
    """Main entry point for data aggregation."""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize agent
    agent = SolanaAgentKit(
        private_key=os.getenv("SOLANA_PRIV_KEY"),
        rpc_url="https://api.mainnet-beta.solana.com"
    )
    
    # Initialize aggregator
    aggregator = DataAggregator(agent)
    
    # Get token input
    token = input("Enter token symbol (e.g., ETH, BTC): ").strip().upper()
    
    try:
        # Get and format data
        data = await aggregator.get_combined_metrics(token)
        formatted_output = aggregator.format_for_llm(data)
        
        # Ensure the output directory exists
        os.makedirs("data/json_output", exist_ok=True)
        
        # Save to file
        output_file = f"data/json_output/{token.lower()}_analysis.json"
        with open(output_file, 'w') as f:
            f.write(formatted_output)
        
        print(f"\nAnalysis complete! Data saved to {output_file}")
        print("\nSummary of data sources:")
        print("- Santiment: " + ("✅ Success" if data["data_sources"]["santiment"] and "error" not in data["data_sources"]["santiment"] else "❌ Failed"))
        print("- CoinGecko: " + ("✅ Success" if data["data_sources"]["coingecko"] and "error" not in data["data_sources"]["coingecko"] else "❌ Failed"))
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
