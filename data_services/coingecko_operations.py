"""CoinGecko operations module.

This module handles all CoinGecko-related operations including trending tokens and price data.
"""

from typing import Dict, List, Optional, Any
from agentipy.agent import SolanaAgentKit
from agentipy.tools.use_coingecko import CoingeckoManager
from agentipy.tools.get_token_data import TokenDataManager

async def get_trending_tokens(agent: SolanaAgentKit) -> List[Dict[str, Any]]:
    """Fetch trending tokens from CoinGecko.

    Args:
        agent: Initialized SolanaAgentKit instance.

    Returns:
        List[Dict[str, Any]]: List of trending tokens with their data.

    Raises:
        Exception: If trending token fetch fails.
    """
    trending_data = await CoingeckoManager.get_trending_tokens(agent)
    return trending_data.get('coins', []) if trending_data else []

async def get_token_metrics(
    agent: SolanaAgentKit,
    token_ticker: str
) -> Optional[Dict[str, Any]]:
    """Fetch detailed metrics for a specific token.

    Args:
        agent: Initialized SolanaAgentKit instance.
        token_ticker: Token ticker symbol (e.g., 'SOL', 'USDC').

    Returns:
        Optional[Dict[str, Any]]: Token metrics if found, None otherwise.

    Raises:
        ValueError: If token ticker cannot be resolved.
        Exception: If token data fetch fails.
    """
    token_address = TokenDataManager.get_token_address_from_ticker(token_ticker)
    if not token_address:
        raise ValueError(f"Could not resolve ticker '{token_ticker}' to a Contract Address.")

    price_data = await CoingeckoManager.get_token_price_data(agent, [token_address])
    return price_data.get(token_address)
