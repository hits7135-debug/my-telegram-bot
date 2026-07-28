import os
import random
import string
import urllib.parse
from flask import Flask, request
import telebot
from telebot import types

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS = [7172828025, 8705494010]
PRIMARY_ADMIN_ID = 7172828025

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- PRODUCTS CONFIG ---
PRODUCTS = {
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

DAYS_MAP = {
    "1d": "1 Day",
    "3d": "3 Days",
    "7d": "7 Days",
    "15d": "15 Days",
    "30d": "30 Days"
}

stock_keys = {
    f"{p}:{d}": [] 
    for p in PRODUCTS.keys() 
    for d in ["1d", "3d", "7d", "15d", "30d"]
}

pending_orders = {}
user_orders = {}
user_states = {}
last_bot_messages = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# Dynamic Welcome Message Generator
def get_welcome_text(first_name):
    return (
        f"👋 Welcome, {first_name}\n\n"
        "★ — 👑 Hassan X Mod Store 👑 — ★\n\n"
        "🔑 Premium All Best Mod Keys\n"
        "⚡ Instant Delivery 24/7\n"
        "🔒 100% Secure Payment\n"
        "🏷 Best Prices Guaranteed\n"
        "🎁 High Discount Rewards\n"
        "🎧 Active Support For Set-Up\n\n"
        "🚀 Tap Shop Now To Start!"
    )

# --- INLINE MENUS ---
def get_start_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🛒 Shop Now", callback_data="nav:open_shop"))
    markup.add(
        types.InlineKeyboardButton("🔑 My Orders", callback_data="user:purchases"),
        types.InlineKeyboardButton("👤 Profile", callback_data="user:profile")
    )
    markup.add(
        types.InlineKeyboardButton("❓ How to Use", callback_data="info:how_to_buy"),
        types.InlineKeyboardButton("🎧 Support", callback_data="user:support")
    )
    return markup

def get_main_panel_inline():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🎁 MAIN ID PANEL", callback_data="select:main_id"),
        types.InlineKeyboardButton("💧 PRIME HOOK", callback_data="select:prime"),
        types.InlineKeyboardButton("🔺 DRIP CLIENT", callback_data="select:drip"),
        types.InlineKeyboardButton("🔙 Back to Menu", callback_data="nav:go_start")
    )
    return markup

def get_category_inline(panel_key):
    markup = types.InlineKeyboardMarkup(row_width=1)
    panel_info = PRODUCTS[panel_key]
    
    for day_code, label in DAYS_MAP.items():
        price = panel_info["prices"][day_code]
        stock_count = len(stock_keys.get(f"{panel_key}:{day_code}", []))
        
        if stock_count > 0:
            btn_text = f"{label} - ₹{price}"
            c_data = f"buy:{panel_key}:{day_code}"
        else:
            btn_text = f"{label} - ❌ Sold Out"
            c_data = "info:sold_out"
            
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=c_data))
        
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="nav:open_shop"))
    return markup

def get_back_button():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="nav:go_start"))
    return markup

def get_admin_panel():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Add Key", callback_data="admin:add_key"),
        types.InlineKeyboardButton("📊 View Stock", callback_data="admin:view_stock"),
        types.InlineKeyboardButton("💰 Update Price", callback_data="admin:select_price_panel")
    )
    return markup

# --- WEBHOOK ROUTES ---
@app.route('/', methods=['GET'])
def home():
    return "Bot Webhook Server Active!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Forbidden', 403

# --- COMMANDS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = None
    first_name = message.from_user.first_name or "User"
    welcome_text = get_welcome_text(first_name)
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_start_inline_menu())

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🛠️ **Admin Control Panel**", parse_mode="Markdown", reply_markup=get_admin_panel())
    else:
        bot.send_message(message.chat.id, "❌ **Access Denied!**")

# --- CALLBACK HANDLER (EDIT MESSAGE SYSTEM) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    message_id = call.message.message_id
    first_name = call.from_user.first_name or "User"
    data = call.data.split(":")
    action = data[0]

    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    # Dynamic Editing System
    if action == "nav":
        sub = data[1]
        if sub == "open_shop":
            bot.edit_message_text("🛒 **Select Your Mod Panel:**", chat_id, message_id, parse_mode="Markdown", reply_markup=get_main_panel_inline())
        elif sub == "go_start":
            welcome_text = get_welcome_text(first_name)
            bot.edit_message_text(welcome_text, chat_id, message_id, reply_markup=get_start_inline_menu())

    elif action == "user":
        sub = data[1]
        if sub == "profile":
            text = f"👤 **Profile Info**\n\nName: {call.from_user.first_name}\nUsername: @{call.from_user.username or 'None'}\nID: `{user_id}`"
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())
        elif sub == "purchases":
            if chat_id in user_orders and user_orders[chat_id]:
                orders_txt = "\n\n➖➖➖➖➖➖➖➖➖\n\n".join(user_orders[chat_id])
                text = f"🔑 **Your Active Keys & Orders:**\n\n{orders_txt}"
            else:
                text = "🔑 **Your Orders:**\n\nYou haven't made any purchases yet."
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button(), disable_web_page_preview=True)
        elif sub == "support":
            text = (
                "🎧 **Support Center**\n\n"
                "👤 Telegram: @HassanXMods1\n"
                "If you need any help, contact us on Telegram, explain your issue, and please wait for our reply."
            )
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

    elif action == "info":
        if data[1] == "sold_out":
            bot.answer_callback_query(call.id, "This category is currently Sold Out!", show_alert=True)
        elif data[1] == "how_to_buy":
            text = (
                "❓ **How to Use — Tutorial Video**\n\n"
                "1. Click Shop Now.\n"
                "2. Select product & validity.\n"
                "3. Pay exact amount via QR / UPI.\n"
                "4. Get Instant Key Delivery.\n\n"
                "Tap button below if you need more help!"
            )
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

    elif action == "select":
        panel_key = data[1]
        bot.edit_message_text(f"🛒 Select Category for **{PRODUCTS[panel_key]['name']}**:", chat_id, message_id, parse_mode="Markdown", reply_markup=get_category_inline(panel_key))

    elif action == "buy":
        p_key, d_code = data[1], data[2]
        price = PRODUCTS[p_key]["prices"][d_code]
        p_name = PRODUCTS[p_key]["name"]

        payment_text = (
            f"👑 💳 — **Hassan X Mod Store** — 👑\n\n"
            f"Panel: {p_name}\nCategory: {d_code.upper()}\nPrice: ₹{price}\n\n"
            f"💳 **UPI ID**: `8171733966@fam`\nName: Harsaan Ali Khan\n\n"
            f"Please pay exact amount and send UTR / Screenshot here."
        )
        
        # Fixed UPI Payment URI with Exact Price
        upi_uri = f"upi://pay?pa=8171733966@fam&pn=Harsaan%20Ali%20Khan&am={price}&cu=INR"
        encoded_upi_uri = urllib.parse.quote_plus(upi_uri)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_upi_uri}"
        
        # Safe edit/delete flow for QR
        safe_delete(chat_id, message_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid:{p_key}:{d_code}"))
        sent_qr = bot.send_photo(chat_id, qr_url, caption=payment_text, parse_mode="Markdown", reply_markup=markup)
        last_bot_messages[chat_id] = sent_qr.message_id

    elif action == "paid":
        p_key, d_code = data[1], data[2]
        user_states[chat_id] = f"WAITING_PROOF:{p_key}:{d_code}"
        
        if chat_id in last_bot_messages:
            safe_delete(chat_id, last_bot_messages[chat_id])

        msg = bot.send_message(chat_id, "📸 Send your **12-digit UTR / Transaction ID** or **Screenshot** here:")
        last_bot_messages[chat_id] = msg.message_id

    elif action == "admin":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ Access Denied!", show_alert=True)
            return

        sub_action = data[1]
        if sub_action == "add_key":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p_key, p_val in PRODUCTS.items():
                for d_code in ["1d", "3d", "7d", "15d", "30d"]:
                    markup.add(types.InlineKeyboardButton(f"{p_val['name']} ({d_code})", callback_data=f"admin:addstock:{p_key}:{d_code}"))
            bot.send_message(chat_id, "Select Panel & Plan to Add Key:", reply_markup=markup)

        elif sub_action == "addstock":
            p_key, d_code = data[2], data[3]
            user_states[chat_id] = f"ADDING_KEY:{p_key}:{d_code}"
            bot.send_message(chat_id, f"📝 Send the key now for **{PRODUCTS[p_key]['name']} ({d_code})**:", parse_mode="Markdown")

        elif sub_action == "view_stock":
            msg = "📊 **Current Stock & Prices:**\n\n"
            for p_key, p_val in PRODUCTS.items():
                msg += f"**{p_val['name']}**:\n"
                for d_code in ["1d", "3d", "7d", "15d", "30d"]:
                    cnt = len(stock_keys.get(f"{p_key}:{d_code}", []))
                    prc = p_val["prices"][d_code]
                    msg += f" • {d_code}: `{cnt}` Keys | ₹{prc}\n"
                msg += "\n"
            bot.send_message(chat_id, msg, parse_mode="Markdown")

        elif sub_action == "select_price_panel":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p_key, p_val in PRODUCTS.items():
                for d_code in ["1d", "3d", "7d", "15d", "30d"]:
                    curr_price = p_val["prices"][d_code]
                    markup.add(types.InlineKeyboardButton(f"{p_val['name']} ({d_code}) - ₹{curr_price}", callback_data=f"admin:editprice:{p_key}:{d_code}"))
            bot.send_message(chat_id, "💰 Select Plan to Change Price:", reply_markup=markup)

        elif sub_action == "editprice":
            p_key, d_code = data[2], data[3]
            curr_p = PRODUCTS[p_key]["prices"][d_code]
            user_states[chat_id] = f"UPDATING_PRICE:{p_key}:{d_code}"
            bot.send_message(chat_id, f"🔢 Current price for **{PRODUCTS[p_key]['name']} ({d_code})** is **₹{curr_p}**.\n\nPlease type and send the **NEW PRICE** (only numbers):", parse_mode="Markdown")

    elif action == "approve":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ Not Authorized!", show_alert=True)
            return

        order_id, p_key, d_code = data[1], data[2], data[3]
        target_stock = f"{p_key}:{d_code}"

        if order_id in pending_orders:
            u_id = pending_orders[order_id]
            if len(stock_keys[target_stock]) > 0:
                key = stock_keys[target_stock].pop(0)
                game_name = PRODUCTS[p_key]['name']
                duration_str = DAYS_MAP.get(d_code, d_code.upper())

                delivery_msg = (
                    f"✅ Payment Successful!\n"
                    f"🎮 Game: {game_name}\n"
                    f"⌛ Duration: {duration_str}\n"
                    f"🔑 Key: `{key}`\n\n"
                    f"🙏 Thank you for your purchase!\n\n"
                    f"PANEL SETUP AND APK LINK  https://t.me/+T-QvHT2k8Pw4NTI9"
                )
                
                bot.send_message(u_id, delivery_msg, parse_mode="Markdown", disable_web_page_preview=True)
                
                # Update User's "My Orders" History
                if u_id not in user_orders:
                    user_orders[u_id] = []
                
                order_history_item = (
                    f"🎮 **Game:** {game_name}\n"
                    f"⌛ **Duration:** {duration_str}\n"
                    f"🔑 **Key:** `{key}`\n"
                    f"📦 **Order ID:** `{order_id}`\n"
                    f"🔗 **Setup/APK:** https://t.me/+T-QvHT2k8Pw4NTI9"
                )
                user_orders[u_id].append(order_history_item)

                try:
                    bot.edit_message_caption(caption=call.message.caption + "\n\n✅ **STATUS: APPROVED**", chat_id=chat_id, message_id=message_id, reply_markup=None)
                except Exception:
                    try:
                        bot.edit_message_text(text=call.message.text + "\n\n✅ **STATUS: APPROVED**", chat_id=chat_id, message_id=message_id, reply_markup=None)
                    except Exception:
                        pass
            else:
                bot.send_message(chat_id, f"⚠️ Stock Empty for **{PRODUCTS[p_key]['name']} ({d_code})**! Add key using /admin first.")
            del pending_orders[order_id]

    elif action == "cancel":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ Not Authorized!", show_alert=True)
            return

        order_id = data[1]
        if order_id in pending_orders:
            u_id = pending_orders[order_id]
            bot.send_message(u_id, f"❌ **Payment Rejected**\n\nYour payment for Order `{order_id}` was rejected.\nContact support @HassanXMods1 if this is a mistake.", parse_mode="Markdown")
            
            try:
                bot.edit_message_caption(caption=call.message.caption + "\n\n❌ **STATUS: CANCELLED**", chat_id=chat_id, message_id=message_id, reply_markup=None)
            except Exception:
                try:
                    bot.edit_message_text(text=call.message.text + "\n\n❌ **STATUS: CANCELLED**", chat_id=chat_id, message_id=message_id, reply_markup=None)
                except Exception:
                    pass
            del pending_orders[order_id]

# --- TEXT / PHOTO HANDLER ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_inputs(message):
    chat_id = message.chat.id
    current_state = user_states.get(chat_id)

    if not current_state:
        return

    if current_state.startswith("UPDATING_PRICE:"):
        if not is_admin(chat_id):
            return

        _, p_key, d_code = current_state.split(":")
        new_price_text = message.text.strip() if message.text else ""

        if new_price_text.isdigit():
            new_price = int(new_price_text)
            PRODUCTS[p_key]["prices"][d_code] = new_price
            user_states[chat_id] = None
            bot.send_message(chat_id, f"✅ **Price Updated Successfully!**\n\n{PRODUCTS[p_key]['name']} ({d_code}) is now **₹{new_price}**", parse_mode="Markdown", reply_markup=get_admin_panel())
        else:
            bot.send_message(chat_id, "❌ Invalid input! Please enter numbers only (e.g. 120):")
        return

    if current_state.startswith("ADDING_KEY:"):
        if not is_admin(chat_id):
            return

        _, p_key, d_code = current_state.split(":")
        target_stock = f"{p_key}:{d_code}"
        key = message.text.strip() if message.text else ""

        if key:
            stock_keys[target_stock].append(key)
            user_states[chat_id] = None
            bot.send_message(chat_id, f"✅ **Key added to {PRODUCTS[p_key]['name']} ({d_code})!**\n\nTotal Stock Now: {len(stock_keys[target_stock])}", parse_mode="Markdown", reply_markup=get_admin_panel())
        return

    if current_state.startswith("WAITING_PROOF:"):
        _, p_key, d_code = current_state.split(":")

        random_id = "".join(random.choices(string.digits, k=12))
        random_suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
        order_id = f"ORD-{random_id}-{random_suffix}"

        pending_orders[order_id] = chat_id
        user_states[chat_id] = None

        if chat_id in last_bot_messages:
            safe_delete(chat_id, last_bot_messages[chat_id])
        safe_delete(chat_id, message.message_id)

        bot.send_message(chat_id, f"✅ **Payment proof received!**\n\nOrder ID:\n`{order_id}`\n\nOur team will verify and deliver your key shortly.\nUpdates: @HassanXMods1", parse_mode="Markdown")

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Approve", callback_data=f"approve:{order_id}:{p_key}:{d_code}"),
            types.InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{order_id}")
        )

        price = PRODUCTS[p_key]["prices"][d_code]
        admin_msg = (
            f"📩 **New Payment Proof!**\n\n"
            f"Order: `{order_id}`\n"
            f"Panel: {PRODUCTS[p_key]['name']}\n"
            f"Category: {d_code.upper()}\n"
            f"Amount: ₹{price}\n"
            f"User: @{message.from_user.username or 'NoUser'} (`{chat_id}`)"
        )

        if message.photo:
            bot.send_photo(PRIMARY_ADMIN_ID, message.photo[-1].file_id, caption=admin_msg, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(PRIMARY_ADMIN_ID, f"{admin_msg}\nProof/UTR: {message.text}", parse_mode="Markdown", reply_markup=markup)

# --- WEBHOOK SETTER ---
if __name__ == "__main__":
    WEBHOOK_URL = f"https://my-telegram-bot-kamx.onrender.com/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)

    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
