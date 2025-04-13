"""Santiment API operations module.

This module handles all Santiment-related operations including metrics and data analysis.
"""

import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import os
from dotenv import load_dotenv
from logging_config import setup_logger

logger = setup_logger(__name__)

load_dotenv()

class SantimentAPI:
    """Class to handle Santiment API operations."""

    def __init__(self):
        """Initialize Santiment API client."""
        self.api_key = os.getenv('SANTIMENT_API_KEY')
        if not self.api_key:
            raise ValueError("SANTIMENT_API_KEY not found in environment variables")
        
        self.url = "https://api.santiment.net/graphql"
        self.headers = {"Authorization": f"Apikey {self.api_key}"}
        
        # Define available metrics
        self.metrics = {
            "dev_activity": "Developer Activity",
            "social_volume_total": "Social Volume",
            "daily_active_addresses": "Daily Active Addresses",
            "price_usd": "Price (USD)",
            "marketcap_usd": "Market Capitalization (USD)"
        }

    def query_metric(self, token: str, metric_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """Query a specific metric for a token.

        Args:
            token: Token symbol (e.g., 'ethereum', 'bitcoin').
            metric_name: Name of the metric to query.
            days: Number of days of historical data to fetch.

        Returns:
            List[Dict[str, Any]]: List of data points with datetime and values.

        Raises:
            Exception: If API request fails.
        """
        to_date = datetime.utcnow()
        from_date = to_date - timedelta(days=days)

        query = f"""{{
          getMetric(metric: "{metric_name}") {{
            timeseriesData(
              slug: "{token}",
              from: "{from_date.strftime('%Y-%m-%dT%H:%M:%SZ')}",
              to: "{to_date.strftime('%Y-%m-%dT%H:%M:%SZ')}",
              interval: "1d"
            ) {{
              datetime
              value
            }}
          }}
        }}"""

        logger.debug(f"Querying Santiment API for {metric_name} data of {token}")
        response = requests.post(self.url, json={"query": query}, headers=self.headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {metric_name} for {token}: {response.text}")
            raise Exception(f"API request failed with status {response.status_code}")

        data = response.json()
        return data["data"]["getMetric"]["timeseriesData"]

    def get_token_metrics(self, token: str, days: int = 7) -> Dict[str, Any]:
        """Get all available metrics for a token.

        Args:
            token: Token symbol (e.g., 'ethereum', 'bitcoin').
            days: Number of days of historical data to fetch.

        Returns:
            Dict[str, Any]: Dictionary containing all metric data.
        """
        logger.info(f"Fetching Santiment metrics for {token}")
        result = {}

        for metric_key, metric_label in self.metrics.items():
            try:
                data = self.query_metric(token, metric_key, days)
                
                values = [entry["value"] for entry in data]
                dates = [entry["datetime"][:10] for entry in data]
                
                if values:
                    avg_val = sum(values) / len(values)
                    trend = "increasing" if values[-1] > values[0] else "decreasing"
                    
                    result[metric_key] = {
                        "label": metric_label,
                        "data_points": [{"date": d, "value": v} for d, v in zip(dates, values)],
                        "average": avg_val,
                        "trend": trend
                    }
                    logger.debug(f"Successfully fetched {metric_label} for {token}")
                
            except Exception as e:
                logger.error(f"Failed to fetch {metric_label} for {token}: {str(e)}")
                result[metric_key] = {"error": str(e)}

        return result
