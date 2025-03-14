import json
import uuid
from pathlib import Path
import time

affiliate_data_file = Path("affiliate_data.json")

def load_affiliate_data():
    """Load affiliate data from JSON file."""
    if affiliate_data_file.exists():
        with open(affiliate_data_file, "r") as f:
            return json.load(f)
    return {}

def save_affiliate_data(data):
    """Save affiliate data to JSON file."""
    with open(affiliate_data_file, "w") as f:
        json.dump(data, f, indent=4)

affiliate_data = load_affiliate_data()

def generate_affiliate_id():
    """Generate a unique affiliate ID."""
    affiliate_id = str(uuid.uuid4())
    affiliate_data[affiliate_id] = {"commissions": []}
    save_affiliate_data(affiliate_data)
    return affiliate_id

def store_affiliate_data(affiliate_id, data):
    """Store affiliate data."""
    affiliate_data[affiliate_id] = data
    save_affiliate_data(affiliate_data)

def get_affiliate_data(affiliate_id):
    """Retrieve affiliate data."""
    return affiliate_data.get(affiliate_id)

def record_commission(affiliate_id, ico_id, amount, commission, client_ip):
    """Record a commission for an affiliate."""
    if affiliate_id in affiliate_data:
        affiliate_data[affiliate_id]["commissions"].append({
            "ico_id": ico_id,
            "amount": amount,
            "commission": commission,
            "client_ip": client_ip,
            "timestamp": int(time.time())
        })
        save_affiliate_data(affiliate_data)
        return True
    return False