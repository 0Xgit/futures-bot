# Simple webhook server for OAuth callbacks

from flask import Flask, request, redirect, jsonify
import asyncio
from telegram_bot_enhanced import oauth_callback_handler

app = Flask(__name__)

@app.route('/oauth/callback')
async def oauth_callback():
    """Handle OAuth callbacks from exchanges"""
    
    result = await oauth_callback_handler(request)
    
    if 'error' in result:
        return f"""
        <html>
            <body>
                <h2>❌ Connection Failed</h2>
                <p>{result['error']}</p>
                <p>Please try again or contact support.</p>
            </body>
        </html>
        """, 400
    else:
        return """
        <html>
            <body>
                <h2>✅ Connection Successful!</h2>
                <p>Your exchange account has been connected successfully.</p>
                <p>You can now close this window and return to Telegram.</p>
                <script>
                    setTimeout(() => window.close(), 3000);
                </script>
            </body>
        </html>
        """

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
