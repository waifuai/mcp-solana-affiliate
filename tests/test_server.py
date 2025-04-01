# tests/test_server.py
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, ANY
from urllib.parse import quote, unquote
import uuid
import os
import httpx # Import httpx

# Import server components and fixtures
from mcp_solana_affiliate import server, affiliates
# Fixtures client (now Flask's TestClient), test_app, mcp_context_mock, mcp_server_instance are available from conftest.py

# --- Test FastMCP Resource ---

@pytest.mark.asyncio # This test still needs to be async because it calls an async function directly
async def test_register_affiliate(mcp_server_instance, mcp_context_mock):
    """Test the affiliate registration resource."""
    mock_affiliate_id = str(uuid.uuid4())
    mock_main_server_url = "http://mock-main-server.test"
    expected_action_api = f"{mock_main_server_url}/affiliate_buy_tokens?affiliate_id={mock_affiliate_id}"
    expected_blink_url = "solana-action:" + quote(expected_action_api)
    expected_response = f"Affiliate registered successfully! Your Solana Blink URL is: {expected_blink_url}"

    with patch("mcp_solana_affiliate.server.generate_affiliate_id", return_value=mock_affiliate_id) as mock_gen_id, \
         patch.dict(os.environ, {"MAIN_SERVER_URL": mock_main_server_url}, clear=True): # Ensure env var is set for test

        # Directly call the resource function implementation
        response = await server.register_affiliate(mcp_context_mock)

        mock_gen_id.assert_called_once()
        assert response == expected_response

# --- Test Flask Endpoints ---

# Removed @pytest.mark.asyncio and async/await
def test_affiliate_buy_tokens_options(client): # client is Flask client
    """Test the OPTIONS request for CORS preflight."""
    response = client.options('/affiliate_buy_tokens') # Removed await
    assert response.status_code == 204
    assert response.headers.get('Access-Control-Allow-Origin') == '*'
    assert 'POST' in response.headers.get('Access-Control-Allow-Methods')
    assert 'Content-Type' in response.headers.get('Access-Control-Allow-Headers')

# Removed @pytest.mark.asyncio and async
@patch("mcp_solana_affiliate.server.httpx.Client") # Patch sync Client
@patch("mcp_solana_affiliate.server.record_commission") # Patch record_commission directly
def test_affiliate_buy_tokens_post_success(mock_record_commission, mock_sync_client, client): # client is Flask client
    """Test successful POST request to affiliate_buy_tokens."""
    mock_affiliate_id = str(uuid.uuid4())
    mock_amount = 1000
    mock_transaction = "mock_serialized_transaction_base64"
    mock_main_server_url = "http://mock-main-server.test:5000" # Use port from default env
    mock_ico_id = 'main_ico' # As assumed in server code
    # Expected commission based on 1% of amount
    mock_commission = 50.0 # Example value - this isn't used in assertion anymore

    # Configure the mock sync httpx client response
    mock_internal_response = MagicMock()
 # Use MagicMock
    mock_internal_response.status_code = 200
    mock_internal_response.json.return_value = {"transaction": mock_transaction}
    # Configure the mock client instance returned by the context manager
    mock_sync_client_instance = MagicMock()
 # Use MagicMock
    mock_sync_client_instance.post.return_value = mock_internal_response # Sync post call
    mock_sync_client.return_value.__enter__.return_value = mock_sync_client_instance
 # Patch __enter__


    # Expected commission: 1% of mock_amount (1000) = 10.0
    expected_commission = float(mock_amount) * 0.01

    with patch.dict(os.environ, {"MAIN_SERVER_URL": mock_main_server_url}, clear=True):

        # Make the request using the Flask test client
        response = client.post('/affiliate_buy_tokens', json={ # Removed await
            "amount": mock_amount,
            "affiliate_id": mock_affiliate_id
        })

    assert response.status_code == 200
    assert response.json == {"transaction": mock_transaction} # Use response.json (property)
    assert response.headers.get('Access-Control-Allow-Origin') == '*'

    # Verify internal httpx call (mock is now sync)
    mock_sync_client_instance.post.assert_called_once_with(
 # Corrected variable name
        f"{mock_main_server_url}/buy_tokens_action",
        json={"amount": mock_amount},
        timeout=10.0
    )
    mock_internal_response.raise_for_status.assert_called_once()

    # Verify commission recording
    # Check if record_commission was called with the correctly calculated commission
    mock_record_commission.assert_called_once_with(
        mock_affiliate_id,
        mock_ico_id,
        mock_amount,
        expected_commission, # Check for the calculated 1% commission
        ANY  # Client IP is harder to mock reliably here, accept any
    )


# Removed @pytest.mark.asyncio and async/await
def test_affiliate_buy_tokens_post_missing_amount(client): # client is Flask client
    """Test POST request with missing amount."""
    response = client.post('/affiliate_buy_tokens', json={"affiliate_id": "some_id"}) # Removed await
    assert response.status_code == 400
    assert response.json == {"error": "Missing amount"} # Use response.json
    assert response.headers.get('Access-Control-Allow-Origin') == '*'

# Removed @pytest.mark.asyncio and async
@patch("mcp_solana_affiliate.server.httpx.Client") # Patch sync Client
def test_affiliate_buy_tokens_post_httpx_error(mock_sync_client, client): # client is Flask client
    """Test POST request when httpx call fails."""
    # Configure the mock sync client to raise an exception
    mock_sync_client_instance = MagicMock()
 # Use MagicMock
    mock_sync_client_instance.post.side_effect = httpx.RequestError("Network Error") # Sync post call
    mock_sync_client.return_value.__enter__.return_value = mock_sync_client_instance
 # Patch __enter__
 
    # Ensure the correct URL with port is used for consistency
    with patch.dict(os.environ, {"MAIN_SERVER_URL": "http://mock-main-server.test:5000"}, clear=True):
        response = client.post('/affiliate_buy_tokens', json={"amount": 100, "affiliate_id": "some_id"}) # Removed await

    assert response.status_code == 500
    assert "Network Error" in response.json["error"] # Use response.json
    assert response.headers.get('Access-Control-Allow-Origin') == '*'

# Removed @pytest.mark.asyncio and async
@patch("mcp_solana_affiliate.server.httpx.Client") # Patch sync Client
def test_affiliate_buy_tokens_post_no_transaction(mock_sync_client, client): # client is Flask client
    """Test POST request when main server response lacks transaction."""
    # Configure the mock sync httpx client response
    mock_internal_response = MagicMock()
 # Use MagicMock
    mock_internal_response.status_code = 200
    mock_internal_response.json.return_value = {"message": "something went wrong"} # No transaction key
    # Configure the mock client instance returned by the context manager
    mock_sync_client_instance = MagicMock()
 # Use MagicMock
    mock_sync_client_instance.post.return_value = mock_internal_response # Sync post call
    mock_sync_client.return_value.__enter__.return_value = mock_sync_client_instance
 # Patch __enter__
 
    # Ensure the correct URL with port is used for consistency
    with patch.dict(os.environ, {"MAIN_SERVER_URL": "http://mock-main-server.test:5000"}, clear=True):
        response = client.post('/affiliate_buy_tokens', json={"amount": 100, "affiliate_id": "some_id"}) # Removed await

    assert response.status_code == 500
    assert response.json == {"error": "Failed to get transaction from main server"} # Use response.json
    assert response.headers.get('Access-Control-Allow-Origin') == '*'


# --- Test /record_commission Endpoint ---

# These tests were already using the standard Flask client and are synchronous
@patch("mcp_solana_affiliate.server.record_commission")
def test_record_commission_endpoint_success(mock_record_commission, test_app): # Use test_app fixture to get standard client
    """Test successful commission recording via endpoint."""
    mock_record_commission.return_value = True
    data = {
        "affiliate_id": "aff_123",
        "ico_id": "ico_abc",
        "amount": 500,
        "commission": 50.0,
        "client_ip": "1.2.3.4"
    }
    std_client = test_app.test_client() # Get standard client
    response = std_client.post('/record_commission', json=data)
    assert response.status_code == 200
    assert response.json == {"message": "Commission recorded successfully"} # Standard client uses .json
    mock_record_commission.assert_called_once_with(
        data["affiliate_id"], data["ico_id"], data["amount"], data["commission"], data["client_ip"]
    )

@patch("mcp_solana_affiliate.server.record_commission")
def test_record_commission_endpoint_failure(mock_record_commission, test_app): # Use test_app fixture
    """Test failed commission recording via endpoint (e.g., invalid ID)."""
    mock_record_commission.return_value = False
    data = {
        "affiliate_id": "invalid_id",
        "ico_id": "ico_abc",
        "amount": 500,
        "commission": 50.0,
        "client_ip": "1.2.3.4"
    }
    std_client = test_app.test_client() # Get standard client
    response = std_client.post('/record_commission', json=data)
    assert response.status_code == 400 # Or 500 depending on expected error
    assert "Invalid affiliate ID" in response.json["error"]
    mock_record_commission.assert_called_once_with(
        data["affiliate_id"], data["ico_id"], data["amount"], data["commission"], data["client_ip"]
    )

def test_record_commission_endpoint_missing_data(test_app): # Use test_app fixture
    """Test commission recording endpoint with missing data."""
    data = {
        "affiliate_id": "aff_123",
        # "ico_id": "ico_abc", # Missing
        "amount": 500,
        "commission": 50.0,
        "client_ip": "1.2.3.4"
    }
    std_client = test_app.test_client() # Get standard client
    response = std_client.post('/record_commission', json=data)
    assert response.status_code == 400
    assert response.json == {"error": "Missing required data"}

@patch("mcp_solana_affiliate.server.record_commission")
def test_record_commission_endpoint_exception(mock_record_commission, test_app): # Use test_app fixture
    """Test commission recording endpoint when an exception occurs."""
    mock_record_commission.side_effect = Exception("Database error")
    data = {
        "affiliate_id": "aff_123",
        "ico_id": "ico_abc",
        "amount": 500,
        "commission": 50.0,
        "client_ip": "1.2.3.4"
    }
    std_client = test_app.test_client() # Get standard client
    response = std_client.post('/record_commission', json=data)
    assert response.status_code == 500
    assert "Database error" in response.json["error"]