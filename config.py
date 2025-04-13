"""Configuration module for Solana Agent.

This module contains configuration settings and constants used across the application.
"""

from solders.pubkey import Pubkey

# Solana Network Configuration
MAINNET_RPC_URL = "https://api.mainnet-beta.solana.com"

# Token Configuration
USDC_MINT = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
SOL_MINT = Pubkey.from_string("So11111111111111111111111111111111111111112")

# Default Trade Configuration
DEFAULT_SWAP_AMOUNT_SOL = 0.0001

# AI Configuration
DEFAULT_AI_MODEL = "gpt-4o"
DEFAULT_AI_TEMPERATURE = 0
