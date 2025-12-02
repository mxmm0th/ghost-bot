import requests
import time

TOKEN = "8345246339:AAFVH-ozvcJqZIUWb6IuiqnAUxc5YeztDfc"
URL = f"https://api.telegram.org/bot{TOKEN}/getUpdates"

def get_chat_id():
    print(f"Checking for messages on Bot (Token: {TOKEN[:5]}...)...")
    try:
        response = requests.get(URL, timeout=10)
        data = response.json()
        
        if not data.get("ok"):
            print(f"Error: {data.get('description')}")
            return

        results = data.get("result", [])
        if not results:
            print("No messages found.")
            print("Please send a message (e.g., 'Hello') to your bot on Telegram, then run this script again.")
            return

        # Get the last message
        last_update = results[-1]
        chat_id = last_update["message"]["chat"]["id"]
        username = last_update["message"]["chat"].get("username", "Unknown")
        
        print(f"\nSUCCESS! Found Chat ID.")
        print(f"User: @{username}")
        print(f"Chat ID: {chat_id}")
        print("\nPlease set this Chat ID in your environment variables.")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_chat_id()
