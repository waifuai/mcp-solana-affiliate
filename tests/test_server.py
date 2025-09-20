# tests/test_server.py
import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock, ANY
from urllib.parse import quote, unquote
import uuid
import os
import httpx
from flask import Flask

# Import server components and fixtures
from mcp_solana_affiliate import server, affiliates
from mcp_solana_affiliate.models import BuyTokensRequest, CommissionRequest, ErrorResponse
from mcp_solana_affiliate.services import AffiliateService, TransactionService, HealthService, MetricsService
# Fixtures client (now Flask's TestClient), test_app, mcp_context_mock, mcp_server_instance are available from conftest.py

# --- Test FastMCP Resource ---

@pytest.mark.asyncio
async def test_register_affiliate(mcp_server_instance, mcp_context_mock):
    """Test the affiliate registration resource."""
    mock_affiliate_id = str(uuid.uuid4())
    mock_main_server_url = "http://mock-main-server.test"
    expected_action_api = f"{mock_main_server_url}/affiliate_buy_tokens?affiliate_id={mock_affiliate_id}"
    expected_blink_url = "solana-action:" + quote(expected_action_api)
    expected_response = f"Affiliate registered successfully! Your Solana Blink URL is: {expected_blink_url}"

    with patch("mcp_solana_affiliate.affiliates.generate_affiliate_id", return_value=mock_affiliate_id) as mock_gen_id, \
         patch.dict(os.environ, {"MAIN_SERVER_URL": mock_main_server_url}, clear=True):

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

@patch("mcp_solana_affiliate.services.TransactionService.process_buy_tokens")
def test_affiliate_buy_tokens_post_success(mock_process_buy_tokens, client):
    """Test successful POST request to affiliate_buy_tokens."""
    mock_affiliate_id = str(uuid.uuid4())
    mock_amount = 1000
    mock_transaction = "mock_serialized_transaction_base64"

    # Configure the mock service response
    from mcp_solana_affiliate.models import TransactionResponse
    mock_response = TransactionResponse(transaction=mock_transaction)
    mock_process_buy_tokens.return_value = mock_response

    # Make the request using the Flask test client
    response = client.post('/affiliate_buy_tokens', json={
        "amount": mock_amount,
        "affiliate_id": mock_affiliate_id
    })

    assert response.status_code == 200
    assert response.get_json() == {"transaction": mock_transaction}

    # Verify service was called with correct parameters
    expected_request = BuyTokensRequest(amount=mock_amount, affiliate_id=mock_affiliate_id)
    mock_process_buy_tokens.assert_called_once_with(expected_request, ANY)  # ANY for client_ip


def test_affiliate_buy_tokens_post_missing_amount(client):
    """Test POST request with missing amount."""
    response = client.post('/affiliate_buy_tokens', json={"affiliate_id": "some_id"})
    assert response.status_code == 400
    assert "Missing amount" in response.get_json()["error"]

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
def test_record_commission_endpoint_exception(mock_record_commission, test_app):
    """Test commission recording endpoint when an exception occurs."""
    mock_record_commission.side_effect = Exception("Database error")
    data = {
        "affiliate_id": "aff_123",
        "ico_id": "ico_abc",
        "amount": 500,
        "commission": 50.0,
        "client_ip": "1.2.3.4"
    }
    std_client = test_app.test_client()
    response = std_client.post('/record_commission', json=data)
    assert response.status_code == 500
    assert "Database error" in response.get_json()["error"]

# --- Test Health Check Endpoint ---

@patch("mcp_solana_affiliate.services.HealthService.check_health")
def test_health_check_success(mock_check_health, client):
    """Test successful health check."""
    mock_health_data = {
        "status": "healthy",
        "timestamp": 1234567890,
        "service": "mcp-solana-affiliate",
        "version": "1.0.0",
        "checks": {
            "affiliate_data": "healthy",
            "main_server": "healthy",
            "database": "healthy"
        }
    }
    mock_check_health.return_value = mock_health_data

    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == mock_health_data

@patch("mcp_solana_affiliate.services.HealthService.check_health")
def test_health_check_unhealthy(mock_check_health, client):
    """Test unhealthy health check."""
    mock_health_data = {
        "status": "unhealthy",
        "timestamp": 1234567890,
        "service": "mcp-solana-affiliate",
        "version": "1.0.0",
        "checks": {
            "affiliate_data": "unhealthy",
            "main_server": "unreachable",
            "database": "healthy"
        }
    }
    mock_check_health.return_value = mock_health_data

    response = client.get('/health')
    assert response.status_code == 503
    assert response.get_json() == mock_health_data

# --- Test Metrics Endpoint ---

@patch("mcp_solana_affiliate.services.MetricsService.get_metrics")
def test_metrics_endpoint_success(mock_get_metrics, client):
    """Test successful metrics endpoint."""
    mock_metrics_data = {
        "total_affiliates": 10,
        "total_commissions": 25,
        "total_commission_amount": 1250.0,
        "timestamp": 1234567890
    }
    mock_get_metrics.return_value = mock_metrics_data

    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.get_json() == mock_metrics_data

@patch("mcp_solana_affiliate.services.MetricsService.get_metrics")
def test_metrics_endpoint_exception(mock_get_metrics, client):
    """Test metrics endpoint with exception."""
    mock_get_metrics.side_effect = Exception("Metrics error")

    response = client.get('/metrics')
    assert response.status_code == 500
    assert "Failed to collect metrics" in response.get_json()["error"]

# --- Test Input Validation ---

def test_buy_tokens_request_validation():
    """Test BuyTokensRequest model validation."""
    # Valid request
    request = BuyTokensRequest(amount=1000.0, affiliate_id="test-id")
    assert request.amount == 1000.0
    assert request.affiliate_id == "test-id"

    # Invalid amount (negative)
    with pytest.raises(ValueError):
        BuyTokensRequest(amount=-100, affiliate_id="test-id")

    # Missing amount
    with pytest.raises(ValueError):
        BuyTokensRequest(affiliate_id="test-id")

    # Missing affiliate_id
    with pytest.raises(ValueError):
        BuyTokensRequest(amount=1000)

def test_commission_request_validation():
    """Test CommissionRequest model validation."""
    # Valid request
    request = CommissionRequest(
        affiliate_id="test-id",
        ico_id="test-ico",
        amount=1000.0,
        commission=50.0,
        client_ip="1.2.3.4"
    )
    assert request.commission == 50.0

    # Invalid commission (negative)
    with pytest.raises(ValueError):
        CommissionRequest(
            affiliate_id="test-id",
            ico_id="test-ico",
            amount=1000.0,
            commission=-10.0,
            client_ip="1.2.3.4"
        )

# --- Test Service Layer ---

@patch("mcp_solana_affiliate.affiliates.generate_affiliate_id")
@patch.dict(os.environ, {"MAIN_SERVER_URL": "http://mock-server.test"}, clear=True)
def test_affiliate_service_register_affiliate(mock_generate_id, client):
    """Test AffiliateService.register_affiliate."""
    mock_affiliate_id = str(uuid.uuid4())
    mock_generate_id.return_value = mock_affiliate_id

    result = AffiliateService.register_affiliate()
    expected_url = f"http://mock-server.test/affiliate_buy_tokens?affiliate_id={mock_affiliate_id}"
    expected_blink = f"solana-action:{quote(expected_url)}"
    assert expected_blink in result

@patch("mcp_solana_affiliate.affiliates.get_affiliate_data")
def test_affiliate_service_get_affiliate_data(mock_get_data):
    """Test AffiliateService.get_affiliate_data."""
    mock_data = {"commissions": [{"amount": 100, "commission": 10}]}
    mock_get_data.return_value = mock_data

    result = AffiliateService.get_affiliate_data("test-id")
    assert result is not None
    assert result.commissions[0]["amount"] == 100

@patch("mcp_solana_affiliate.affiliates.record_commission")
def test_affiliate_service_record_commission(mock_record_commission):
    """Test AffiliateService.record_commission."""
    mock_record_commission.return_value = True
    request = CommissionRequest(
        affiliate_id="test-id",
        ico_id="test-ico",
        amount=1000.0,
        commission=50.0,
        client_ip="1.2.3.4"
    )

    result = AffiliateService.record_commission(request)
    assert result is True
    mock_record_commission.assert_called_once()

# --- Integration Tests ---

def test_end_to_end_affiliate_flow(client):
    """Test complete affiliate flow integration."""
    # Register affiliate
    with patch("mcp_solana_affiliate.affiliates.generate_affiliate_id") as mock_gen_id:
        mock_affiliate_id = str(uuid.uuid4())
        mock_gen_id.return_value = mock_affiliate_id

        # This would normally call the MCP tool, but for integration test
        # we'll test the service layer directly
        result = AffiliateService.register_affiliate()
        assert mock_affiliate_id in result

        # Test buy tokens with the registered affiliate
        with patch("mcp_solana_affiliate.services.TransactionService.process_buy_tokens") as mock_process:
            from mcp_solana_affiliate.models import TransactionResponse
            mock_process.return_value = TransactionResponse(transaction="test-transaction")

            response = client.post('/affiliate_buy_tokens', json={
                "amount": 1000,
                "affiliate_id": mock_affiliate_id
            })

            assert response.status_code == 200
            assert "transaction" in response.get_json()