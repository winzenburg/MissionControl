#!/usr/bin/env python3
"""
TradingView Webhook Listener
Listens for alerts from TradingView Pine Script → routes to Telegram
"""

import json
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 5001))
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


class TradingViewWebhookHandler(BaseHTTPRequestHandler):
    """Handle incoming TradingView webhook alerts"""

    def do_POST(self):
        """Process POST request from TradingView"""
        if self.path != '/tradingview':
            self.send_response(404)
            self.end_headers()
            return

        try:
            # Read request body
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            
            logger.info(f"Received webhook: {body}")
            
            # Parse JSON
            alert_data = json.loads(body)
            
            # Format message for Telegram
            message = format_alert(alert_data)
            
            # Send to Telegram
            send_telegram(message)
            
            # Return success
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'received',
                'timestamp': datetime.now().isoformat()
            }).encode())
            
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def log_message(self, format, *args):
        """Suppress default HTTP logging"""
        logger.info(f"HTTP: {format % args}")


def format_alert(alert_data):
    """Format TradingView alert for Telegram"""
    try:
        symbol = alert_data.get('symbol', 'UNKNOWN')
        action = alert_data.get('action', 'ALERT')
        price = alert_data.get('price', 'N/A')
        message_text = alert_data.get('message', '')
        
        # Build Telegram message
        telegram_msg = f"""
📊 *TradingView Alert*

*Symbol:* `{symbol}`
*Action:* {action}
*Price:* {price}

{message_text}

_Time: {datetime.now().strftime('%H:%M:%S')}_
"""
        return telegram_msg.strip()
    except Exception as e:
        logger.error(f"Error formatting alert: {e}")
        return f"Alert received: {json.dumps(alert_data)}"


def send_telegram(message):
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram credentials not set (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)")
        return
    
    try:
        import requests
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': message,
            'parse_mode': 'Markdown'
        }
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            logger.info("Message sent to Telegram")
        else:
            logger.error(f"Telegram error: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending to Telegram: {e}")


def start_server():
    """Start webhook listener"""
    server_address = ('127.0.0.1', WEBHOOK_PORT)
    httpd = HTTPServer(server_address, TradingViewWebhookHandler)
    logger.info(f"🦞 TradingView Webhook Listener started on http://127.0.0.1:{WEBHOOK_PORT}/tradingview")
    logger.info("Waiting for alerts...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        httpd.shutdown()


if __name__ == '__main__':
    start_server()
