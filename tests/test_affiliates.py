# tests/test_affiliates.py
import pytest
import json
import uuid
import time
from pathlib import Path
from mcp_solana_affiliate import affiliates

# The manage_test_data_file fixture from conftest.py is used automatically

def test_load_affiliate_data_non_existent(monkeypatch):
    """Test loading data when the file doesn't exist."""
    # Ensure the file is gone (though the fixture should handle this)
    test_file = affiliates.affiliate_data_file
    if test_file.exists():
        test_file.unlink()
    # Reload data explicitly for this test case after ensuring file is gone
    monkeypatch.setattr(affiliates, "affiliate_data", affiliates.load_affiliate_data())
    assert affiliates.load_affiliate_data() == {}

def test_load_affiliate_data_existent():
    """Test loading data from an existing file."""
    test_data = {"test_id": {"commissions": []}}
    with open(affiliates.affiliate_data_file, "w") as f:
        json.dump(test_data, f)
    # Reload data explicitly for this test case
    affiliates.affiliate_data = affiliates.load_affiliate_data()
    assert affiliates.load_affiliate_data() == test_data

def test_save_affiliate_data():
    """Test saving affiliate data."""
    test_data = {"save_test_id": {"commissions": [{"amount": 10}]}}
    affiliates.save_affiliate_data(test_data)
    with open(affiliates.affiliate_data_file, "r") as f:
        loaded_data = json.load(f)
    assert loaded_data == test_data

def test_generate_affiliate_id():
    """Test generating a unique affiliate ID."""
    affiliate_id = affiliates.generate_affiliate_id()
    # Check if it looks like a UUID
    try:
        uuid.UUID(affiliate_id, version=4)
    except ValueError:
        pytest.fail(f"Generated ID {affiliate_id} is not a valid UUID4.")

    # Verify it's saved in the (reloaded) data
    loaded_data = affiliates.load_affiliate_data()
    assert affiliate_id in loaded_data
    assert loaded_data[affiliate_id] == {"commissions": []}

def test_store_affiliate_data():
    """Test storing affiliate data."""
    affiliate_id = affiliates.generate_affiliate_id() # Ensures ID exists
    data_to_store = {"commissions": [{"ico_id": "test_ico", "amount": 50}]}
    affiliates.store_affiliate_data(affiliate_id, data_to_store)

    loaded_data = affiliates.load_affiliate_data()
    assert loaded_data.get(affiliate_id) == data_to_store

def test_get_affiliate_data():
    """Test retrieving affiliate data."""
    # 1. Existing ID
    affiliate_id = affiliates.generate_affiliate_id()
    data_to_store = {"commissions": [{"amount": 100}]}
    affiliates.store_affiliate_data(affiliate_id, data_to_store)
    retrieved_data = affiliates.get_affiliate_data(affiliate_id)
    assert retrieved_data == data_to_store

    # 2. Non-existent ID
    non_existent_id = str(uuid.uuid4())
    retrieved_data_none = affiliates.get_affiliate_data(non_existent_id)
    assert retrieved_data_none is None

def test_record_commission_success():
    """Test recording a commission successfully."""
    affiliate_id = affiliates.generate_affiliate_id()
    ico_id = "main_ico"
    amount = 1000
    commission = 100.0
    client_ip = "192.168.1.1"
    start_time = int(time.time())

    success = affiliates.record_commission(affiliate_id, ico_id, amount, commission, client_ip)
    end_time = int(time.time())

    assert success is True
    loaded_data = affiliates.load_affiliate_data()
    commissions = loaded_data[affiliate_id]["commissions"]
    assert len(commissions) == 1
    recorded = commissions[0]
    assert recorded["ico_id"] == ico_id
    assert recorded["amount"] == amount
    assert recorded["commission"] == commission
    assert recorded["client_ip"] == client_ip
    assert start_time <= recorded["timestamp"] <= end_time

def test_record_commission_invalid_id():
    """Test recording a commission with an invalid affiliate ID."""
    non_existent_id = str(uuid.uuid4())
    success = affiliates.record_commission(non_existent_id, "test_ico", 100, 10, "127.0.0.1")
    assert success is False
    # Ensure data file wasn't created or modified unexpectedly
    loaded_data = affiliates.load_affiliate_data()
    assert non_existent_id not in loaded_data