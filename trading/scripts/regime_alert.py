#!/usr/bin/env python3
"""
Send Telegram alert for regime changes.
Called by cron or manually when regime shift detected.
"""

import os
import sys
import json
import urllib.parse
import urllib.request
from pathlib import Path

# Load environment
ENV_FILE = Path(__file__).parent.parent / '.env'
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ[key] = value

TG_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TG_CHAT = os.getenv('TELEGRAM_CHAT_ID')

def send_telegram(text):
    """Send message to Telegram."""
    if not (TG_TOKEN and TG_CHAT):
        print("Telegram not configured (missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID)")
        return False
    
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    data = urllib.parse.urlencode({
        'chat_id': TG_CHAT,
        'text': text,
        'parse_mode': 'HTML'
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            return result.get('ok', False)
    except Exception as e:
        print(f"Error sending Telegram message: {e}")
        return False


def format_regime_alert(regime_data):
    """Format regime data as Telegram message."""
    
    emoji = regime_data.get('emoji', '')
    regime = regime_data.get('regime', 'UNKNOWN')
    score = regime_data.get('score', 0)
    prev_regime = regime_data.get('previousRegime', 'UNKNOWN')
    
    msg = f"🚨 <b>REGIME ALERT</b>\n"
    msg += f"{prev_regime} → {emoji} <b>{regime}</b>\n"
    msg += f"Score: {score}/10\n\n"
    
    # Active alerts
    active = regime_data.get('activeAlerts', [])
    if active:
        msg += "<b>Active Alerts:</b>\n"
        for alert in active[:3]:  # Top 3
            priority = alert.get('priority', '?')
            name = alert.get('name', 'Unknown')
            value = alert.get('value', '')
            weight = alert.get('weight', 0)
            msg += f"#{priority} {name}: {value} (+{weight})\n"
        msg += "\n"
    
    # AMS parameters
    params = regime_data.get('parameters', {})
    msg += "<b>AMS Adjustments:</b>\n"
    msg += f"• Z-score threshold: {params.get('zEnter', 'N/A')}\n"
    msg += f"• Position size: {params.get('sizeMultiplier', 0)*100:.0f}%\n"
    msg += f"• ATR multiplier: {params.get('atrMultiplier', 1.0):.1f}x\n"
    msg += f"• Cooldown: {params.get('cooldown', 'N/A')} bars\n"
    
    return msg


def main():
    """Send regime alert based on current state."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Send Telegram regime alert")
    parser.add_argument('--force', action='store_true', help="Send alert even if no change")
    args = parser.parse_args()
    
    # Load regime state
    state_file = Path(__file__).parent.parent / 'logs' / 'regime_state.json'
    if not state_file.exists():
        print("No regime state found")
        sys.exit(1)
    
    with open(state_file) as f:
        regime_data = json.load(f)
    
    # Check if regime changed
    current = regime_data.get('regime')
    previous = regime_data.get('previousRegime')
    
    if not args.force and current == previous:
        print(f"No regime change (current: {current})")
        sys.exit(0)
    
    # Format and send alert
    message = format_regime_alert(regime_data)
    
    if send_telegram(message):
        print("✅ Regime alert sent to Telegram")
    else:
        print("❌ Failed to send Telegram alert")
        sys.exit(1)


if __name__ == "__main__":
    main()
