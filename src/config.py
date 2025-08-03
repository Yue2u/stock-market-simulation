# config.py
import logging
from pathlib import Path

import orjson

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
FRONTEND_DIR = BASE_DIR / "frontend"
CHART_DATA_FILE = BASE_DIR / "chart_data.json"

# Timeouts and limits
SUBSCRIBER_TIMEOUT = 300  # 5 minutes
EVENT_QUEUE_TIMEOUT = 2.0
CLEANUP_INTERVAL = 60  # 1 minute

# Logging configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def get_required_currencies():
    """Dynamically load required currencies from chart_data.json round 0"""
    try:
        if not CHART_DATA_FILE.exists():
            logger.warning(f"Chart data file not found: {CHART_DATA_FILE}")
            return ["Apple", "Google", "РосАтом", "BitCoin"]  # fallback

        with open(CHART_DATA_FILE, "r", encoding="utf-8") as f:
            data = orjson.loads(f.read())

        # Get currencies from round 0
        round_0_data = data.get("0", {}).get("chart", {})
        if not round_0_data:
            logger.warning("No chart data found for round 0")
            return ["Apple", "Google", "РосАтом", "BitCoin"]  # fallback

        currencies = list(round_0_data.keys())
        logger.info(f"Loaded currencies from chart data: {currencies}")
        return currencies

    except Exception as e:
        logger.error(f"Error loading currencies from chart data: {e}")
        return ["Apple", "Google", "РосАтом", "BitCoin"]  # fallback


# Load required currencies dynamically
REQUIRED_CURRENCIES = get_required_currencies()
