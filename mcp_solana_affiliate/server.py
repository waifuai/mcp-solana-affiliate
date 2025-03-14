import asyncio
import os
from urllib.parse import quote
from fastmcp import FastMCP, Context, Field
from mcp_solana_affiliate.affiliates import generate_affiliate_id, store_affiliate_data, record_commission
from flask import Flask, request, jsonify
import httpx

mcp = FastMCP(name="Solana Affiliate Server")

app = Flask(__name__)

@mcp.resource("affiliate://register")
async def register_affiliate(context: Context) -> str:
    """Register a new affiliate and return a Solana Blink URL."""
    affiliate_id = generate_affiliate_id()
    main_server_url = os.getenv("MAIN_SERVER_URL", "http://localhost:5000")
    # Point the Blink URL to the *affiliate* server's endpoint
    action_api_url = f"{main_server_url}/affiliate_buy_tokens?affiliate_id={affiliate_id}"
    blink_url = "solana-action:" + quote(action_api_url)
    return f"Affiliate registered successfully! Your Solana Blink URL is: {blink_url}"

@app.route('/affiliate_buy_tokens', methods=['POST', 'OPTIONS'])
async def affiliate_buy_tokens():
    """Handles token purchases through affiliate links."""
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return '', 204, headers
    
    headers = {'Access-Control-Allow-Origin': '*'}
    try:
        data = request.get_json()
        amount = data.get('amount')
        affiliate_id = data.get('affiliate_id')  # Get affiliate_id from the request

        if not amount:
            return jsonify({"error": "Missing amount"}), 400, headers

        # 1. Construct a request to the *main* server's Action API
        main_server_url = os.getenv("MAIN_SERVER_URL", "http://localhost:5000")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{main_server_url}/buy_tokens_action",
                json={"amount": amount},  # No affiliate_id here
                timeout=10.0
            )
            response.raise_for_status()  # Raise HTTP errors
            main_server_response = response.json()

            # 2. Get the serialized transaction from the main server's response
            serialized_transaction = main_server_response.get("transaction")
            if not serialized_transaction:
                return jsonify({"error": "Failed to get transaction from main server"}), 500, headers

            # 3.  Record the commission (affiliate_id, ico_id, amount, commission)
            ico_id = 'main_ico'  #  get this from the main server's response if you have multiple ICOs
            required_sol = server.calculate_token_price(amount, server.ico_data[ico_id]) #need to calculate it
            commission = required_sol * 0.1
            record_commission(affiliate_id, ico_id, amount, commission, request.remote_addr)

            # 4. Return the serialized transaction to the Blink client
            return jsonify({"transaction": serialized_transaction}), 200, headers

    except Exception as e:
        return jsonify({"error": str(e)}), 500, headers

@app.route('/record_commission', methods=['POST'])
def record_commission_endpoint():
    """Record a commission for an affiliate."""
    try:
        data = request.get_json()
        affiliate_id = data.get('affiliate_id')
        ico_id = data.get('ico_id')
        amount = data.get('amount')
        commission = data.get('commission')
        client_ip = data.get('client_ip')

        if not all([affiliate_id, ico_id, amount, commission, client_ip]):
            return jsonify({"error": "Missing required data"}), 400

        success = record_commission(affiliate_id, ico_id, amount, commission, client_ip)
        if success:
            return jsonify({"message": "Commission recorded successfully"}), 200
        else:
            return jsonify({"error": "Invalid affiliate ID or other error"}), 400  # Or 500, depending on the error
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    asyncio.run(mcp.run(transport="http", port=5001))
    app.run(debug=True, port=5002)