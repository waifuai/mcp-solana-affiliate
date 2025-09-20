# MCP Solana Affiliate Server

This project provides a separate MCP (Model Context Protocol) server for managing the affiliate program associated with the `mcp_solana_ico` project.  It is designed to be completely independent of the main ICO server, handling all aspects of affiliate registration and commission tracking.

## Key Features

*   **Affiliate Registration:**  Provides an `affiliate://register` resource that generates unique affiliate IDs and Solana Blink URLs.
*   **Blink URL Handling:**  The generated Blink URLs point to an endpoint (`/affiliate_buy_tokens`) *within this server*.
*   **Proxy Functionality:** The `/affiliate_buy_tokens` endpoint acts as a proxy. It receives requests from Blinks, forwards the purchase request to the main ICO server's Action API, and then records the commission.
*   **Persistent Storage:** Affiliate data and commissions are stored persistently in a JSON file (`affiliate_data.json`).
*   **Complete Separation:** This server has *no* dependencies on the main `mcp_solana_ico` server, other than using its Action API URL for constructing purchase transactions. The main ICO server has no knowledge of the affiliate program.
*   **Health Monitoring:** Built-in health check and metrics endpoints for monitoring service status.
*   **Type Safety:** Full type hints and Pydantic models for robust data validation.
*   **Comprehensive Logging:** Structured logging with configurable levels and file output.
*   **Security:** Input validation and security measures throughout the application.

## Requirements

*   Python 3.11+
*   Poetry
*   Flask

## Installation

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd mcp_solana_affiliate
    ```

2.  **Install dependencies:**

    ```bash
    poetry install
    ```

## Configuration

### `.env` file

Create a `.env` file in the root directory with the following content:

```
MAIN_SERVER_URL="http://localhost:5000"  # URL of the main mcp_solana_ico server's Action API
```

**Important:**  `MAIN_SERVER_URL` must point to the correct location of the main ICO server's Action API.

## Usage

1.  **Start the server:**

    ```bash
    poetry run python mcp_solana_affiliate/server.py
    ```
   This will start both the FastMCP server (for `affiliate://register`) on port 5001 and the Flask app (for handling Blink requests and commission recording) on port 5002.

2.  **Register Affiliates:** Use an MCP client to call the `affiliate://register` resource. This will return a Solana Blink URL.

3.  **Token Purchases via Blinks:** When a user clicks the Blink URL, it will send a request to the `/affiliate_buy_tokens` endpoint on this server.  This endpoint will:
    *   Extract the `amount` from the request.
    *   Forward the purchase request (without any affiliate information) to the main ICO server's Action API (`/buy_tokens_action`).
    *   Receive the serialized Solana transaction from the main server.
    *   Record the commission in `affiliate_data.json`.
    *   Return the serialized transaction to the Blink client.

## API Documentation

### MCP Resources

#### `affiliate://register`

Registers a new affiliate and returns a Solana Blink URL.

**Response:**
```json
"Affiliate registered successfully! Your Solana Blink URL is: solana-action:http://localhost:5000/affiliate_buy_tokens?affiliate_id=123e4567-e89b-12d3-a456-426614174000"
```

### REST Endpoints

#### POST `/affiliate_buy_tokens`

Processes token purchases through affiliate links.

**Request:**
```json
{
  "amount": 1000.0,
  "affiliate_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response (Success):**
```json
{
  "transaction": "base64-encoded-transaction"
}
```

**Response (Error):**
```json
{
  "error": "Error message"
}
```

**Status Codes:**
- `200` - Success
- `400` - Bad Request (validation error)
- `500` - Internal Server Error
- `502` - Bad Gateway (main server error)
- `503` - Service Unavailable (timeout)

#### POST `/record_commission`

Manually records a commission for an affiliate.

**Request:**
```json
{
  "affiliate_id": "123e4567-e89b-12d3-a456-426614174000",
  "ico_id": "main_ico",
  "amount": 1000.0,
  "commission": 50.0,
  "client_ip": "192.168.1.1"
}
```

**Response (Success):**
```json
{
  "message": "Commission recorded successfully"
}
```

**Response (Error):**
```json
{
  "error": "Error message"
}
```

#### GET `/health`

Health check endpoint for monitoring.

**Response:**
```json
{
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
```

#### GET `/metrics`

Metrics endpoint for monitoring service statistics.

**Response:**
```json
{
  "total_affiliates": 10,
  "total_commissions": 25,
  "total_commission_amount": 1250.0,
  "timestamp": 1234567890
}
```

#### GET `/cache/stats`

Cache statistics endpoint for monitoring cache performance.

**Response:**
```json
{
  "affiliate_cache": {
    "total_items": 5,
    "expired_items": 1,
    "active_items": 4,
    "hit_count": 150,
    "miss_count": 25
  },
  "metrics_cache": { ... },
  "health_cache": { ... }
}
```

#### POST `/cache/clear`

Clear all cache data.

**Response:**
```json
{
  "message": "All caches cleared successfully"
}
```

#### POST `/cache/cleanup`

Remove expired items from cache.

**Response:**
```json
{
  "message": "Cache cleanup completed",
  "items_removed": 3
}
```

### Configuration

The application uses Pydantic models for configuration management. Configuration can be set via environment variables:

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MAIN_SERVER_URL` | None | URL of the main ICO server (required) |
| `MCP_PORT` | `5001` | Port for MCP server |
| `FLASK_PORT` | `5002` | Port for Flask server |
| `DEBUG` | `false` | Enable debug mode |
| `COMMISSION_RATE` | `0.01` | Default commission rate (1%) |
| `DEFAULT_ICO_ID` | `main_ico` | Default ICO identifier |
| `AFFILIATE_DATA_FILE` | `affiliate_data.json` | Path to affiliate data file |
| `MAX_REQUESTS_PER_MINUTE` | `60` | Rate limiting: max requests per minute |
| `MAX_AFFILIATES_PER_IP` | `10` | Rate limiting: max affiliates per IP |
| `REQUEST_TIMEOUT` | `10.0` | HTTP request timeout in seconds |
| `MAX_RETRIES` | `3` | Maximum retry attempts |
| `RETRY_DELAY` | `1.0` | Delay between retries |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_FILE` | None | Optional log file path |

### Data Models

The application uses the following data models:

#### CommissionRecord
```python
{
  "ico_id": "main_ico",
  "amount": 1000.0,
  "commission": 50.0,
  "client_ip": "192.168.1.1",
  "timestamp": 1234567890
}
```

#### AffiliateData
```python
{
  "affiliate_id": "123e4567-e89b-12d3-a456-426614174000",
  "commissions": [CommissionRecord],
  "created_at": 1234567890,
  "last_updated": 1234567890
}
```

## Project Structure

```
mcp_solana_affiliate/
├── affiliates.py      # Core affiliate logic (generation, storage, commission recording)
├── server.py           # Main server code (FastMCP resource and Flask app)
├── config.py           # Configuration management with Pydantic models
├── models.py           # Data models using Pydantic
├── services.py         # Service layer for business logic
├── __init__.py
.env                    # Environment variables
.gitignore
pyproject.toml          # Poetry configuration
README.md               # This file
```

## Architecture

The application follows a layered architecture:

- **Presentation Layer:** Flask endpoints handling HTTP requests/responses
- **Service Layer:** Business logic in `services.py` (AffiliateService, TransactionService, etc.)
- **Data Layer:** Data access and persistence in `affiliates.py`
- **Configuration Layer:** Centralized configuration management in `config.py`
- **Model Layer:** Data validation and serialization in `models.py`

### Key Components

- **AffiliateService:** Handles affiliate registration and data retrieval
- **TransactionService:** Processes token purchases and commission recording
- **HealthService:** Provides health check and monitoring functionality
- **MetricsService:** Collects and exposes service metrics
- **Configuration Management:** Environment-based configuration with Pydantic validation
- **Error Handling:** Comprehensive error handling with appropriate HTTP status codes
- **Logging:** Structured logging with configurable levels and outputs

## Development

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd mcp_solana_affiliate
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=mcp_solana_affiliate

# Run specific test file
poetry run pytest tests/test_server.py
```

### Running the Application

```bash
# Development mode
poetry run python -m mcp_solana_affiliate.server

# Production mode (with gunicorn)
poetry run gunicorn -w 4 -b 0.0.0.0:5002 mcp_solana_affiliate.server:app
```

### Code Quality

```bash
# Format code
poetry run black mcp_solana_affiliate tests

# Lint code
poetry run ruff check mcp_solana_affiliate tests

# Type checking
poetry run mypy mcp_solana_affiliate
```

## Monitoring

### Health Checks

The service provides health check endpoints:

- `GET /health` - Overall health status
- `GET /metrics` - Service metrics and statistics

### Logging

Logs are output to:
- Console (INFO level by default)
- Optional log file (if LOG_FILE environment variable is set)

Log levels can be configured via the LOG_LEVEL environment variable.

## Security

- Input validation using Pydantic models
- CORS configuration for cross-origin requests
- Environment variable validation
- Rate limiting support (configurable)
- IP-based affiliate limits (configurable)

## Performance

### Caching Strategy

The application implements a multi-tier caching strategy:

- **Affiliate Cache**: 5-minute TTL for affiliate data to reduce database reads
- **Metrics Cache**: 1-minute TTL for metrics data
- **Health Cache**: 30-second TTL for health check data

### Performance Optimizations

- Efficient JSON file storage with in-memory caching
- Configurable HTTP timeouts and retry logic
- Connection pooling for external requests
- Thread-safe caching with automatic cleanup
- Metrics collection for monitoring bottlenecks
- Lazy loading of configuration

### Cache Management

Cache can be managed via API endpoints:
- Monitor cache performance: `GET /cache/stats`
- Clear all caches: `POST /cache/clear`
- Cleanup expired items: `POST /cache/cleanup`

### Monitoring

Performance metrics are exposed via:
- `GET /metrics` - Service usage statistics
- `GET /health` - Health status with dependency checks
- `GET /cache/stats` - Cache performance metrics

## Future Considerations

- **Database Storage:** Replace JSON file storage with a more robust database (PostgreSQL, MongoDB)
- **Caching:** Implement Redis caching for frequently accessed data
- **Authentication:** Add API key authentication for endpoints
- **Rate Limiting:** Implement more sophisticated rate limiting
- **Monitoring:** Integrate with Prometheus/Grafana for advanced monitoring
- **Scaling:** Add support for horizontal scaling with load balancing

## Key Files

*   **`affiliates.py`:**
    *   `generate_affiliate_id()`: Generates a unique affiliate ID using `uuid.uuid4()`.
    *   `load_affiliate_data()`: Loads affiliate data from `affiliate_data.json`.
    *   `save_affiliate_data()`: Saves affiliate data to `affiliate_data.json`.
    *   `store_affiliate_data()`: Stores affiliate data.
    *   `get_affiliate_data()`: Retrieves affiliate data.
    *   `record_commission()`: Records a commission for an affiliate.

*   **`server.py`:**
    *   `mcp = FastMCP(name="Solana Affiliate Server")`: Initializes the FastMCP server.
    *   `@mcp.resource("affiliate://register")`: The FastMCP resource for registering affiliates.
    *   `app = Flask(__name__)`: Initializes the Flask application.
    *   `@app.route('/affiliate_buy_tokens', methods=['POST', 'OPTIONS'])`: The Flask endpoint that handles Blink requests, forwards them to the main server, and records commissions.
    *    `@app.route('/record_commission', methods=['POST'])`: A Flask endpoint for manually recording commissions (not strictly required, but potentially useful).

## Future Considerations

*   **Database Storage:** Replace the JSON file storage with a more robust database (e.g., PostgreSQL, SQLite).
*   **Error Handling:** Implement more comprehensive error handling and logging.
*   **Security:**  Implement security measures, such as authentication and authorization, especially for the `/record_commission` endpoint.
*   **Scalability:** Consider using a message queue (e.g., RabbitMQ, Kafka) for handling commission recording asynchronously, improving scalability.
* **Testing:** Add unit and integration tests.