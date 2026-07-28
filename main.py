import os
import requests
from flask import Flask
from threading import Thread
import telebot
from telebot import types

# ----------------- CONFIGURATION -----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "0"))
FIREBASE_URL = os.environ.get("FIREBASE_URL", "").rstrip("/")

bot = telebot.TeleBot(BOT_TOKEN)

# ----------------- FLASK KEEP-ALIVE -----------------
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is active 24/7!"

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

# ----------------- FIREBASE HELPERS -----------------
def fb_get(path):
    try:
        res = requests.get(f"{FIREBASE_URL}/{path}.json")
        return res.json() if res.status_code == 200 else None
    except Exception as e:
        print(f"Firebase GET Error: {e}")
        return None

def fb_put(path, data):
    try:
        requests.put(f"{FIREBASE_URL}/{path}.json", json=data)
    except Exception as e:
        print(f"Firebase PUT Error: {e}")

def fb_patch(path, data):
    try:
        requests.patch(f"{FIREBASE_URL}/{path}.json", json=data)
    except Exception as e:
        print(f"Firebase PATCH Error: {e}")

# Save User Info & Handle Referral
def register_user(user_id, first_name, username, referrer_id=None):
    users = fb_get("users") or {}
    str_id = str(user_id)
    
    if str_id not in users:
        user_data = {
            "first_name": first_name or "User",
            "username": username or "NoUsername",
            "points": 0,
            "referred_by": referrer_id if referrer_id else None
        }
        fb_put(f"users/{str_id}", user_data)
        
        # Credit Referrer
        if referrer_id and str(referrer_id) in users:
            ref_str = str(referrer_id)
            current_pts = users[ref_str].get("points", 0)
            fb_patch(f"users/{ref_str}", {"points": current_pts + 10})
            try:
                bot.send_message(
                    referrer_id,
                    f"🎉 **New Referral!**\n\nUser {first_name} joined using your link!\n➕ You earned **10 Reward Points**!"
                )
            except Exception:
                pass

def get_products():
    products = fb_get("products")
    if not products:
        # Default fallback products
        default_p = {
            "main_id": {
                "name": "🛒 MAIN ID PANEL",
                "prices": {"1d": 100, "3d": 250, "7d": 450, "15d": 800, "30d": 1200}
            },
            "prime": {
                "name": "💧 PRIME HOOK",
                "prices": {"1d": 60, "3d": 140, "7d": 250, "15d": 400, "30d": 600}
            },
            "drip": {
                "name": "🔺 DRIP CLIENT",
                "prices": {"1d": 60, "3d": 140, "7d": 250, "15d": 400, "30d": 600}
            }
        }
        fb_put("products", default_p)
        return default_p
    return products

# ----------------- STATE MANAGEMENT -----------------
user_states = {}

# ----------------- KEYBOARDS -----------------
def get_main_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛒 Shop Now", callback_data="nav:shop"),
        types.InlineKeyboardButton("🎁 Invite & Earn", callback_data="nav:ref"),
        types.InlineKeyboardButton("👤 My Account", callback_data="nav:account"),
        types.InlineKeyboardButton("💬 Support", url="https://t.me/Hassanalikhan07")
    )
    return markup

def get_shop_menu():
    products = get_products()
    markup = types.InlineKeyboardMarkup(row_width=1)
    for p_id, details in products.items():
        markup.add(types.InlineKeyboardButton(details["name"], callback_data=f"select:{p_id}"))
    markup.add(types.InlineKeyboardButton("🔙 Main Menu", callback_data="nav:start"))
    return markup

def get_admin_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add New Panel", callback_data="admin:add_panel"),
        types.InlineKeyboardButton("📢 Broadcast", callback_data="admin:broadcast")
    )
    return markup

# ----------------- HANDLERS -----------------
@bot.message_handler(commands=['start'])
def start_cmd(message):
    chat_id = message.chat.id
    text_args = message.text.split()
    referrer_id = None
    
    if len(text_args) > 1 and text_args[1].startswith("ref_"):
        try:
            referrer_id = int(text_args[1].replace("ref_", ""))
            if referrer_id == chat_id:
                referrer_id = None
        except ValueError:
            referrer_id = None
            
    register_user(chat_id, message.from_user.first_name, message.from_user.username, referrer_id)
    
    bot.send_message(
        chat_id,
        f"👋 **Welcome {message.from_user.first_name}!**\n\nSelect an option below to get started:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['admin'])
def admin_cmd(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.send_message(message.chat.id, "⚙️ **Admin Control Panel**", reply_markup=get_admin_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    data = call.data

    if data == "nav:start":
        bot.edit_message_text("👋 Select an option below:", chat_id, call.message.message_id, reply_markup=get_main_menu())
        
    elif data == "nav:shop":
        bot.edit_message_text("🛍️ **Select Panel:**", chat_id, call.message.message_id, reply_markup=get_shop_menu(), parse_mode="Markdown")
        
    elif data == "nav:ref":
        bot_info = bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start=ref_{chat_id}"
        u_data = fb_get(f"users/{chat_id}") or {}
        pts = u_data.get("points", 0)
        
        msg = (
            f"🎁 **Referral System**\n\n"
            f"Share your link and earn 10 reward points per referral!\n\n"
            f"🔗 **Your Link:** `{ref_link}`\n"
            f"💰 **Your Reward Balance:** `{pts} Points`"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="nav:start"))
        bot.edit_message_text(msg, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data == "nav:account":
        u_data = fb_get(f"users/{chat_id}") or {}
        pts = u_data.get("points", 0)
        msg = f"👤 **Account Profile**\n\nName: {call.from_user.first_name}\nID: `{chat_id}`\nReward Points: `{pts}`"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="nav:start"))
        bot.edit_message_text(msg, chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("select:"):
        p_id = data.split(":")[1]
        products = get_products()
        if p_id in products:
            p = products[p_id]
            markup = types.InlineKeyboardMarkup(row_width=2)
            for cat, price in p.get("prices", {}).items():
                markup.add(types.InlineKeyboardButton(f"{cat.upper()} - ₹{price}", callback_data=f"buy:{p_id}:{cat}"))
            markup.add(types.InlineKeyboardButton("🔙 Back to Shop", callback_data="nav:shop"))
            bot.edit_message_text(f"⚡ **{p['name']}**\nSelect Duration:", chat_id, call.message.message_id, reply_markup=markup, parse_mode="Markdown")

    elif data.startswith("buy:"):
        _, p_id, cat = data.split(":")
        products = get_products()
        p = products.get(p_id, {})
        price = p.get("prices", {}).get(cat, 0)
        
        bot.send_message(
            chat_id,
            f"💳 **Payment Request**\n\nPanel: {p.get('name')}\nDuration: {cat.upper()}\nAmount: ₹{price}\n\nSend Payment Screenshot here!"
        )

    # ADMIN ACTIONS
    elif data == "admin:add_panel":
        if chat_id != ADMIN_ID: return
        user_states[chat_id] = {"step": "ADD_PANEL_NAME"}
        bot.send_message(chat_id, "📝 **Enter New Panel ID & Name** (e.g. `vip_panel:⚡ VIP MOD PANEL`):", parse_mode="Markdown")

    elif data == "admin:broadcast":
        if chat_id != ADMIN_ID: return
        user_states[chat_id] = {"step": "BROADCAST_MSG"}
        bot.send_message(chat_id, "📢 **Send the message or photo you want to broadcast to all users:**", parse_mode="Markdown")

@bot.message_handler(content_types=['text', 'photo'])
def handle_inputs(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id, {})

    # ADMIN BROADCAST PROCESS
    if chat_id == ADMIN_ID and state.get("step") == "BROADCAST_MSG":
        user_states.pop(chat_id, None)
        users = fb_get("users") or {}
        success = 0
        
        bot.send_message(chat_id, f"🚀 Broadcast started for {len(users)} users...")
        for u_id in users:
            try:
                bot.copy_message(int(u_id), chat_id, message.message_id)
                success += 1
            except Exception:
                pass
        bot.send_message(chat_id, f"✅ **Broadcast Completed!**\nSuccessfully sent to `{success}` users.", parse_mode="Markdown")
        return

    # ADMIN ADD PANEL PROCESS
    if chat_id == ADMIN_ID and state.get("step") == "ADD_PANEL_NAME":
        try:
            p_id, name = message.text.split(":")
            p_id = p_id.strip()
            name = name.strip()
            
            # Default prices template added automatically
            new_panel = {
                "name": name,
                "prices": {"1d": 100, "3d": 250, "7d": 450, "15d": 800, "30d": 1200}
            }
            fb_put(f"products/{p_id}", new_panel)
            user_states.pop(chat_id, None)
            bot.send_message(chat_id, f"✅ **Panel Added Successfully!**\nName: {name}\nID: `{p_id}`", parse_mode="Markdown")
        except Exception:
            bot.send_message(chat_id, "❌ Invalid format! Use: `panel_id: Panel Name`\nExample: `vip: ⚡ VIP MOD PANEL`", parse_mode="Markdown")
        return

if __name__ == "__main__":
    Thread(target=run_flask).start()
    print("Bot Started...")
    bot.infinity_polling(skip_pending=True)
