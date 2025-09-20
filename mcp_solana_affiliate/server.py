import asyncio
import os
import logging
import time
from typing import Dict, Any, Optional, Union
from urllib.parse import quote
from mcp.server.fastmcp import FastMCP, Context
from mcp_solana_affiliate.config import app_config
from mcp_solana_affiliate.models import (
    BuyTokensRequest, CommissionRequest, ErrorResponse,
    HealthCheckResponse, MetricsResponse
)
from mcp_solana_affiliate.services import (
    AffiliateService, TransactionService, HealthService, MetricsService
)
from mcp_solana_affiliate.cache import affiliate_cache, metrics_cache, health_cache
from flask import Flask, request, jsonify, Response
import httpx

# Configure logging from config
logging.basicConfig(
    level=getattr(logging, app_config.logging.level),
    format=app_config.logging.format,
    filename=str(app_config.logging.file_path) if app_config.logging.file_path else None
)
logger = logging.getLogger(__name__)

mcp = FastMCP(name="Solana Affiliate Server")

app = Flask(__name__)

# Configure CORS headers from config
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to all responses."""
    response.headers['Access-Control-Allow-Origin'] = ', '.join(app_config.server.cors_origins)
    response.headers['Access-Control-Allow-Methods'] = ', '.join(app_config.server.cors_methods)
    response.headers['Access-Control-Allow-Headers'] = ', '.join(app_config.server.cors_headers)
    return response

@mcp.tool("affiliate://register")
async def register_affiliate(context: Context) -> str:
    """Register a new affiliate and return a Solana Blink URL."""
    try:
        return AffiliateService.register_affiliate()
    except Exception as e:
        logger.error(f"Error registering affiliate: {e}")
        return f"Error registering affiliate: {str(e)}"

@app.route('/affiliate_buy_tokens', methods=['POST', 'OPTIONS'])
def affiliate_buy_tokens() -> Union[Response, tuple[str, int, Dict[str, str]]]:
    """Handles token purchases through affiliate links."""
    if request.method == 'OPTIONS':
        return '', 204

    try:
        # Parse and validate request data using Pydantic models
        request_data = BuyTokensRequest(**request.get_json())
        client_ip = request.remote_addr or "unknown"

        # Process the transaction through the service layer
        transaction_response = TransactionService.process_buy_tokens(request_data, client_ip)

        return jsonify(transaction_response.dict()), 200

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        error_response = ErrorResponse(error=str(e))
        return jsonify(error_response.dict()), 400
    except httpx.TimeoutException:
        logger.error("Timeout connecting to main server")
        error_response = ErrorResponse(error="Service temporarily unavailable")
        return jsonify(error_response.dict()), 503
    except httpx.RequestError as e:
        logger.error(f"Request error to main server: {e}")
        error_response = ErrorResponse(error="Unable to connect to main server")
        return jsonify(error_response.dict()), 502
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from main server: {e.response.status_code}")
        error_response = ErrorResponse(error="Main server error")
        return jsonify(error_response.dict()), 502
    except Exception as e:
        logger.error(f"Unexpected error in affiliate_buy_tokens: {e}")
        error_response = ErrorResponse(error="Internal server error")
        return jsonify(error_response.dict()), 500

@app.route('/record_commission', methods=['POST'])
def record_commission_endpoint() -> Response:
    """Record a commission for an affiliate."""
    try:
        # Parse and validate request data using Pydantic models
        commission_request = CommissionRequest(**request.get_json())

        # Process through service layer
        success = AffiliateService.record_commission(commission_request)

        if success:
            return jsonify({"message": "Commission recorded successfully"}), 200
        else:
            error_response = ErrorResponse(error="Invalid affiliate ID or recording failed")
            return jsonify(error_response.dict()), 400

    except ValueError as e:
        logger.warning(f"Validation error: {e}")
        error_response = ErrorResponse(error=str(e))
        return jsonify(error_response.dict()), 400
    except Exception as e:
        logger.error(f"Unexpected error in record_commission_endpoint: {e}")
        error_response = ErrorResponse(error="Internal server error")
        return jsonify(error_response.dict()), 500

@app.route('/health', methods=['GET'])
def health_check() -> Response:
    """Health check endpoint for monitoring and load balancers."""
    try:
        health_data = HealthService.check_health()
        status_code = 200 if health_data["status"] == "healthy" else 503
        return jsonify(health_data), status_code
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        error_response = {
            "status": "unhealthy",
            "timestamp": int(time.time()),
            "error": str(e)
        }
        return jsonify(error_response), 503

@app.route('/metrics', methods=['GET'])
def metrics() -> Response:
    """Metrics endpoint for monitoring."""
    try:
        metrics_data = MetricsService.get_metrics()
        return jsonify(metrics_data), 200
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        error_response = ErrorResponse(error="Failed to collect metrics")
        return jsonify(error_response.dict()), 500

@app.route('/cache/stats', methods=['GET'])
def cache_stats() -> Response:
    """Cache statistics endpoint for monitoring."""
    try:
        stats = {
            "affiliate_cache": affiliate_cache.stats(),
            "metrics_cache": metrics_cache.stats(),
            "health_cache": health_cache.stats()
        }
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Cache stats collection failed: {e}")
        return jsonify({"error": "Failed to collect cache stats"}), 500

@app.route('/cache/clear', methods=['POST'])
def clear_cache() -> Response:
    """Clear all caches."""
    try:
        affiliate_cache.clear()
        metrics_cache.clear()
        health_cache.clear()

        logger.info("All caches cleared via API")
        return jsonify({"message": "All caches cleared successfully"}), 200
    except Exception as e:
        logger.error(f"Cache clearing failed: {e}")
        return jsonify({"error": "Failed to clear caches"}), 500

@app.route('/cache/cleanup', methods=['POST'])
def cleanup_cache() -> Response:
    """Remove expired items from cache."""
    try:
        total_cleaned = (
            affiliate_cache.cleanup() +
            metrics_cache.cleanup() +
            health_cache.cleanup()
        )

        logger.info(f"Cache cleanup completed, {total_cleaned} items removed")
        return jsonify({
            "message": f"Cache cleanup completed",
            "items_removed": total_cleaned
        }), 200
    except Exception as e:
        logger.error(f"Cache cleanup failed: {e}")
        return jsonify({"error": "Failed to cleanup cache"}), 500

if __name__ == "__main__":
    asyncio.run(mcp.run(transport="http", port=app_config.server.mcp_port))
    app.run(debug=app_config.server.debug, port=app_config.server.flask_port)