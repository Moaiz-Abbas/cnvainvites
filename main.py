# main.py
# Telegram bot that accepts user email, waits for Canva verification code,
# logs in using Playwright, joins a Canva team using valid invite links, and manages expiry.

import telebot
import re
import json
import datetime
import subprocess
from pathlib import Path

BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
bot = telebot.TeleBot(BOT_TOKEN)

# Paths for saving user data and invite links
USERS_FILE = Path("users.json")
INVITES_FILE = Path("invites.txt")

# Load users data or create fresh
if USERS_FILE.exists():
    with open(USERS_FILE, "r") as f:
        joined_users = json.load(f)
else:
    joined_users = {}

# Helper to save users data
def save_users():
    with open(USERS_FILE, "w") as f:
        json.dump(joined_users, f, indent=2)

# Load valid team invites
def load_invite_links():
    if not INVITES_FILE.exists():
        return []
    with open(INVITES_FILE, "r") as f:
        lines = f.read().strip().split("---")
    invites = []
    for block in lines:
        if not block.strip():
            continue
        link_match = re.search(r"Link:\s*(https?://[\S]+)", block)
        date_match = re.search(r"Expiry:\s*(\d{2}-\d{2}-\d{2})", block)
        if link_match and date_match:
            invites.append({
                "link": link_match.group(1).strip(),
                "expiry": date_match.group(1).strip()
            })
    return invites

# Dictionary to track user state
user_state = {}

@bot.message_handler(commands=["joincanva"])
def ask_email(message):
    user_id = str(message.from_user.id)
    if user_id in joined_users:
        expiry = joined_users[user_id]['expiry']
        bot.send_message(message.chat.id, f"🛑 You already joined a team. Access valid till {expiry}.")
        return
    bot.send_message(message.chat.id, "📧 Please send your email address (Gmail preferred).")
    user_state[user_id] = {"stage": "awaiting_email"}

@bot.message_handler(func=lambda msg: user_state.get(str(msg.from_user.id), {}).get("stage") == "awaiting_email")
def get_email(message):
    user_id = str(message.from_user.id)
    email = message.text.strip()
    if not re.match(r"[^@\s]+@[^@\s]+\.[a-zA-Z0-9]+$", email):
        bot.send_message(message.chat.id, "❌ Invalid email. Please try again.")
        return
    user_state[user_id] = {"stage": "awaiting_code", "email": email}
    bot.send_message(message.chat.id, f"📨 Invite sent to {email}. Please send the 6-digit Canva code you received.")

@bot.message_handler(func=lambda msg: user_state.get(str(msg.from_user.id), {}).get("stage") == "awaiting_code")
def get_code(message):
    user_id = str(message.from_user.id)
    code = message.text.strip()
    if not code.isdigit() or len(code) != 6:
        bot.send_message(message.chat.id, "❌ Invalid code. Please send a 6-digit number.")
        return

    email = user_state[user_id]['email']
    invites = load_invite_links()
    today = datetime.datetime.now().date()

    for invite in invites:
        expiry_date = datetime.datetime.strptime(invite['expiry'], "%d-%m-%y").date()
        if today > expiry_date:
            continue

        # Call external Playwright script to handle login and team join
        try:
            result = subprocess.run(
                ["python", "canva_login.py", email, code, invite['link']],
                capture_output=True, text=True, timeout=90
            )
            if "success" in result.stdout.lower():
                joined_users[user_id] = {
                    "email": email,
                    "joined": str(today),
                    "expiry": invite['expiry']
                }
                save_users()
                bot.send_message(message.chat.id, f"✅ Joined Canva team! Access valid till {invite['expiry']}.")
                user_state.pop(user_id)
                return
        except Exception as e:
            continue

    bot.send_message(message.chat.id, "❌ All invite links are either expired or full. Please try again later.")
    user_state.pop(user_id, None)

bot.polling()
