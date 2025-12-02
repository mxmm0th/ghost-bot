import requests
import os
import datetime

def send_deployment_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("Error: Telegram credentials not found.")
        print("Please set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.")
        return
        
    message = f"""
*🚀 MIDNIGHT EXPRESS: DEPLOYMENT SUCCESSFUL*
--------------------
*Timestamp:* {datetime.datetime.now()}
*Status:* ONLINE
*Configuration:* T+1 Efficient Frontier

The Midnight Express bot has been successfully deployed.
The "Midnight Hunter" is now active and will run daily at 09:50 TRT.
The "Ghost Bot" is also active and will run daily at 18:15 TRT.

*Current Strategy:*
- Midnight Hunter: T+1 Scalp (Entry 09:55, Exit 18:05 Next Day)
- Ghost Bot: Momentum (Halka Arz)

_This is a one-time confirmation message._
    """
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print("Deployment Telegram alert sent successfully.")
        else:
            print(f"Error sending Telegram alert: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")

if __name__ == "__main__":
    send_deployment_telegram()
