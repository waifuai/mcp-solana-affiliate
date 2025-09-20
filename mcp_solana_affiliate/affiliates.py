import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Type definitions
AffiliateData = Dict[str, Any]
Commission = Dict[str, Union[str, int, float]]
AffiliateRecord = Dict[str, List[Commission]]

# Import config to get data file path
try:
    from mcp_solana_affiliate.config import app_config
    affiliate_data_file = app_config.affiliate.data_file_path
except ImportError:
    # Fallback to default if config is not available
    affiliate_data_file = Path("affiliate_data.json")
    logger.warning("Could not import config, using default affiliate_data.json")

def load_affiliate_data() -> AffiliateRecord:
    """Load affiliate data from JSON file."""
    try:
        if affiliate_data_file.exists():
            with open(affiliate_data_file, "r", encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                else:
                    logger.warning("Invalid data format in affiliate_data.json, returning empty dict")
                    return {}
        return {}
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading affiliate data: {e}")
        return {}

def save_affiliate_data(data: AffiliateRecord) -> None:
    """Save affiliate data to JSON file."""
    try:
        affiliate_data_file.parent.mkdir(parents=True, exist_ok=True)
        with open(affiliate_data_file, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        logger.info("Affiliate data saved successfully")
    except IOError as e:
        logger.error(f"Error saving affiliate data: {e}")
        raise

# Global affiliate data cache - will be loaded on module import
affiliate_data: AffiliateRecord = load_affiliate_data()

def generate_affiliate_id() -> str:
    """Generate a unique affiliate ID."""
    affiliate_id = str(uuid.uuid4())
    affiliate_data[affiliate_id] = {"commissions": []}
    save_affiliate_data(affiliate_data)
    logger.info(f"Generated new affiliate ID: {affiliate_id}")
    return affiliate_id

def store_affiliate_data(affiliate_id: str, data: AffiliateData) -> None:
    """Store affiliate data."""
    if not isinstance(affiliate_id, str) or not affiliate_id:
        raise ValueError("Invalid affiliate_id")
    if not isinstance(data, dict):
        raise ValueError("Data must be a dictionary")

    affiliate_data[affiliate_id] = data
    save_affiliate_data(affiliate_data)
    logger.info(f"Stored data for affiliate: {affiliate_id}")

def get_affiliate_data(affiliate_id: str) -> Optional[AffiliateData]:
    """Retrieve affiliate data."""
    if not isinstance(affiliate_id, str) or not affiliate_id:
        logger.warning("Invalid affiliate_id provided to get_affiliate_data")
        return None
    return affiliate_data.get(affiliate_id)

def record_commission(affiliate_id: str, ico_id: str, amount: Union[int, float],
                     commission: float, client_ip: str) -> bool:
    """Record a commission for an affiliate."""
    try:
        if not all([affiliate_id, ico_id, client_ip]):
            logger.warning("Missing required parameters for commission recording")
            return False

        if not isinstance(amount, (int, float)) or amount <= 0:
            logger.warning("Invalid amount provided for commission")
            return False

        if not isinstance(commission, (int, float)) or commission < 0:
            logger.warning("Invalid commission provided")
            return False

        if affiliate_id not in affiliate_data:
            logger.warning(f"Affiliate ID not found: {affiliate_id}")
            return False

        commission_record = {
            "ico_id": ico_id,
            "amount": float(amount),
            "commission": float(commission),
            "client_ip": client_ip,
            "timestamp": int(time.time())
        }

        affiliate_data[affiliate_id]["commissions"].append(commission_record)
        save_affiliate_data(affiliate_data)

        logger.info(f"Commission recorded for affiliate {affiliate_id}: "
                   f"amount={amount}, commission={commission}")
        return True

    except Exception as e:
        logger.error(f"Error recording commission for affiliate {affiliate_id}: {e}")
        return False