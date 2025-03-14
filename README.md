# MCP Solana Affiliate Server

This project provides a separate MCP (Model Context Protocol) server for managing the affiliate program associated with the `mcp_solana_ico` project.  It is designed to be completely independent of the main ICO server, handling all aspects of affiliate registration and commission tracking.

## Key Features

*   **Affiliate Registration:**  Provides an `affiliate://register` resource that generates unique affiliate IDs and Solana Blink URLs.
*   **Blink URL Handling:**  The generated Blink URLs point to an endpoint (`/affiliate_buy_tokens`) *within this server*.
*   **Proxy Functionality:** The `/affiliate_buy_tokens` endpoint acts as a proxy. It receives requests from Blinks, forwards the purchase request to the main ICO server's Action API, and then records the commission.
*   **Persistent Storage:** Affiliate data and commissions are stored persistently in a JSON file (`affiliate_data.json`).
* **Complete Separation:** This server has *no* dependencies on the main `mcp_solana_ico` server, other than using its Action API URL for constructing purchase transactions. The main ICO server has no knowledge of the affiliate program.

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

## Project Structure

```
mcp_solana_affiliate/
├── affiliates.py      # Affiliate logic (generation, storage, commission recording)
├── server.py           # Main server code (FastMCP resource and Flask app)
├── __init__.py
.env                    # Environment variables
.gitignore
pyproject.toml          # Poetry configuration
README.md               # This file
```

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