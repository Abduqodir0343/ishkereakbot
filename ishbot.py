import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request
import json
import os
import time

# -------------------
# CONFIG
# -------------------
TOKEN = "8441933465:AAFmeIGdHphCEJOrkTSjixl-nC-bdrRxKZ0"
ADMIN_ID = 6688570192  # Sizning Telegram ID
ANNOUNCE_FILE = "announcements.json"
WEBHOOK_URL = "https://sizning-server.com/" + TOKEN  # HTTPS manzilingiz

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# -------------------
# HELPERS
# -------------------
def load_announcements():
    if os.path.exists(ANNOUNCE_FILE):
        with open(ANNOUNCE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_announcements(data):
    with open(ANNOUNCE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def remove_expired():
    global announcements
    now = int(time.time())
    announcements = [e for e in announcements if e['expires_at'] > now]
    save_announcements(announcements)

def msg_from_admin(user_id):
    return user_id == ADMIN_ID

def start_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("🔹 E’lonlarni ko‘rish", callback_data="view_announcements")
    )
    kb.add(
        InlineKeyboardButton("📝 E’lon qo‘shish", callback_data="add")
    )
    return kb

def view_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("⬅️ Oldingi 3 e'lon", callback_data="prev"),
        InlineKeyboardButton("➡️ Keyingi 3 e'lon", callback_data="next")
    )
    kb.add(
        InlineKeyboardButton("📝 E’lon qo‘shish", callback_data="add")
    )
    return kb

def expire_keyboard():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("⏱ 15 soat", callback_data="expire_15h"))
    kb.add(InlineKeyboardButton("⏱ 1 kun", callback_data="expire_1d"))
    kb.add(InlineKeyboardButton("⏱ 2 kun", callback_data="expire_2d"))
    return kb

def generate_id():
    return int(time.time()*1000)

# -------------------
# GLOBAL
# -------------------
announcements = load_announcements()
remove_expired()
user_pos = {}
temp_user_data = {}

# -------------------
# HANDLERS
# -------------------
@bot.message_handler(commands=['start'])
def start(msg):
    chat_id = msg.chat.id
    bot.send_message(chat_id, "📢 E’lonlar taxtasiga xush kelibsiz!", reply_markup=start_keyboard())

@bot.message_handler(func=lambda m: True, content_types=['text'])
def greet(msg):
    chat_id = msg.chat.id
    if msg.text.lower() in ['salom', 'hi', 'hello']:
        bot.send_message(chat_id, "👋 Salom! E’lonlar taxtasiga xush kelibsiz!", reply_markup=start_keyboard())
    elif chat_id in temp_user_data:
        step = temp_user_data[chat_id].get("step")
        if step == "text":
            text = msg.text
            new_id = generate_id()
            temp_user_data[chat_id].update({"text": text, "id": new_id, "step":"time"})
            bot.send_message(chat_id, "📅 E'lon qancha muddat saqlansin?", reply_markup=expire_keyboard())

# -------------------
# E'lonlarni yuborish
# -------------------
def send_announcements(chat_id):
    remove_expired()
    pos = user_pos.get(chat_id, 0)
    chunk = announcements[pos:pos+3]

    if not chunk:
        bot.send_message(chat_id, "📭 Boshqa e'lonlar yo‘q.", reply_markup=view_keyboard())
        return

    text_all = ""
    for i, e in enumerate(chunk):
        text_all += f"{i+1}. {e['text']}\n"
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("⬅️ Oldingi 3 e'lon", callback_data="prev"),
        InlineKeyboardButton("➡️ Keyingi 3 e'lon", callback_data="next")
    )
    kb.add(
        InlineKeyboardButton("📝 E’lon qo‘shish", callback_data="add")
    )
    bot.send_message(chat_id, text_all, reply_markup=kb)

# -------------------
# Callback query
# -------------------
@bot.callback_query_handler(func=lambda c: True)
def callback(c):
    chat_id = c.message.chat.id
    data = c.data
    remove_expired()

    if data == "view_announcements":
        user_pos[chat_id] = 0
        send_announcements(chat_id)

    elif data == "next":
        user_pos[chat_id] = user_pos.get(chat_id,0)+3
        send_announcements(chat_id)

    elif data == "prev":
        user_pos[chat_id] = max(user_pos.get(chat_id,0)-3,0)
        send_announcements(chat_id)

    elif data == "add":
        bot.send_message(chat_id, "📝 E'lon matnini yuboring:")
        temp_user_data[chat_id] = {"step":"text"}

    elif data.startswith("del_"):
        e_id = int(data.split("_")[1])
        delete_announcement(chat_id, e_id)

    elif data.startswith("edit_"):
        e_id = int(data.split("_")[1])
        edit_announcement(chat_id, e_id)

    elif data.startswith("time_") or data.startswith("expire_"):
        if data.startswith("time_"):
            e_id = int(data.split("_")[1])
            bot.send_message(chat_id, "⏱ Yangi muddatni tanlang:", reply_markup=expire_keyboard())
        else:
            if chat_id in temp_user_data:
                e_id = temp_user_data[chat_id]["id"]
                handle_expire_selection(chat_id, data, e_id)

    bot.answer_callback_query(c.id)

# -------------------
# E'lon o'chirish / tahrirlash / muddat
# -------------------
def delete_announcement(user_id, e_id):
    global announcements
    for e in announcements:
        if e['id']==e_id and (msg_from_admin(user_id) or e['user_id']==user_id):
            announcements = [x for x in announcements if x['id'] != e_id]
            save_announcements(announcements)
            bot.send_message(user_id, "❌ E'lon o‘chirildi!")
            return
    bot.send_message(user_id, "❌ Siz bu e’lonni o‘chirishingiz mumkin emas!")

def edit_announcement(user_id, e_id):
    bot.send_message(user_id, "✏️ Yangi matn yuboring (keyinchalik qo‘shish mumkin)")

def handle_expire_selection(user_id, data, e_id):
    if data.endswith("15h"):
        delta = 15*3600
    elif data.endswith("1d"):
        delta = 24*3600
    elif data.endswith("2d"):
        delta = 48*3600
    else:
        delta = 24*3600

    if user_id in temp_user_data and "text" in temp_user_data[user_id]:
        new_announcement = {
            "id": temp_user_data[user_id]["id"],
            "text": temp_user_data[user_id]["text"],
            "user_id": user_id,
            "expires_at": int(time.time()) + delta
        }
        announcements.append(new_announcement)
        save_announcements(announcements)
        del temp_user_data[user_id]
        bot.send_message(user_id, "✅ E'lon qo‘shildi!", reply_markup=start_keyboard())

# -------------------
# FLASK WEBHOOK
# -------------------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

# -------------------
# SET WEBHOOK
# -------------------
if __name__ == "__main__":
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    print("Webhook o‘rnatildi va bot ishlayapti...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
