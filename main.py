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
    },
    "guild_glory": {
        "name": "🏆 GUILD GLORY BOT",
        "prices": {"4bot": 119, "8bot": 235}
    }
}

DAYS_MAP = {
    "1d": "1 Day",
    "3d": "3 Days",
    "7d": "7 Days",
    "15d": "15 Days",
    "30d": "30 Days",
    "4bot": "4 Bot",
    "8bot": "8 Bot"
}

# Local Data Storage
stock_keys = {
    f"{p}:{d}": [] 
    for p, details in PRODUCTS.items() 
    for d in details["prices"].keys()
}

user_balances = {}
user_orders = {}
pending_orders = {}
user_states = {}
last_bot_messages = {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

# Dynamic Welcome Text with Your Bot Name
def get_welcome_text(user_id, first_name):
    balance = user_balances.get(user_id, 0.0)
    return (
        f"🏪 — **HASSAN X MOD STORE** — 🏪\n\n"
        f"🎉 ***Hello, {first_name}!***\n\n"
        f"🗝 **Powered by Hassan X Mod Store**\n\n"
        f"─ 🏪 **Direct deals with every supplier**\n"
        f"─ 💧 **Instant delivery after payment**\n"
        f"─ 🪙 **Guaranteed discounted prices**\n"
        f"─ 📞 **24/7 admin support**\n\n"
        f"***Tap any button below to begin.***\n\n"
        f"🪙 **Your Balance: ₹{balance:.2f}**\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬"
    )

# Exact Buttons Grid
def get_start_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # Row 1
    markup.add(types.InlineKeyboardButton("🛒 Buy Now", callback_data="nav:open_shop"))
    
    # Row 2
    markup.add(
        types.InlineKeyboardButton("📣 Payment Proof", url="https://t.me/+T-QvHT2k8Pw4NTI9"),
        types.InlineKeyboardButton("🪙 Add Balance", callback_data="user:add_balance")
    )
    
    # Row 3
    markup.add(types.InlineKeyboardButton("👑 My Profile + All History", callback_data="user:profile"))
    
    # Row 4
    markup.add(
        types.InlineKeyboardButton("➡️ Refer And Earn", callback_data="user:refer"),
        types.InlineKeyboardButton("📖 How To Use Bot", callback_data="info:how_to_buy")
    )
    
    # Row 5
    markup.add(
        types.InlineKeyboardButton("📞 Support", callback_data="user:support"),
        types.InlineKeyboardButton("🎁 Daily Gift", callback_data="user:daily_gift")
    )
    
    return markup

def get_main_panel_inline():
    markup = types.InlineKeyboardMarkup(row_width=1)
    for p_key, p_val in PRODUCTS.items():
        markup.add(types.InlineKeyboardButton(p_val["name"], callback_data=f"select:{p_key}"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="nav:go_start"))
    return markup

def get_category_inline(panel_key):
    markup = types.InlineKeyboardMarkup(row_width=1)
    panel_info = PRODUCTS[panel_key]
    
    for day_code, price in panel_info["prices"].items():
        label = DAYS_MAP.get(day_code, day_code.upper())
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
    if message.chat.id not in user_balances:
        user_balances[message.chat.id] = 0.0
        
    welcome_text = get_welcome_text(message.chat.id, first_name)
    bot.send_message(message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=get_start_inline_menu())

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🛠️ **Admin Control Panel**", parse_mode="Markdown", reply_markup=get_admin_panel())
    else:
        bot.send_message(message.chat.id, "❌ **Access Denied!**")

# --- CALLBACK HANDLER ---
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
    except Exception:
        pass

    if action == "nav":
        sub = data[1]
        if sub == "open_shop":
            bot.edit_message_text("🛒 **Select Your Mod Panel:**", chat_id, message_id, parse_mode="Markdown", reply_markup=get_main_panel_inline())
        elif sub == "go_start":
            welcome_text = get_welcome_text(chat_id, first_name)
            bot.edit_message_text(welcome_text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_start_inline_menu())

    elif action == "user":
        sub = data[1]
        if sub == "profile":
            bal = user_balances.get(chat_id, 0.0)
            history_str = "No active keys purchased yet."
            if chat_id in user_orders and user_orders[chat_id]:
                history_str = "\n\n➖➖➖➖➖➖➖➖➖\n\n".join(user_orders[chat_id])
                
            text = (
                f"👑 **MY PROFILE & HISTORY**\n\n"
                f"👤 Name: {first_name}\n"
                f"🆔 User ID: `{user_id}`\n"
                f"💰 Balance: ₹{bal:.2f}\n\n"
                f"🔑 **Purchased Orders:**\n{history_str}"
            )
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button(), disable_web_page_preview=True)
            
        elif sub == "add_balance":
            text = (
                "🪙 **Add Wallet Balance**\n\n"
                "Send payment to UPI: `8171733966@fam`\n"
                "After payment, contact admin @HassanXMods1 with payment screenshot to credit balance into your account!"
            )
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())
            
        elif sub == "refer":
            bot_username = bot.get_me().username
            ref_link = f"https://t.me/{bot_username}?start={chat_id}"
            text = (
                f"➡️ **REFER AND EARN**\n\n"
                f"Share your referral link with friends:\n`{ref_link}`\n\n"
                f"Earn bonus rewards for every friend who joins!"
            )
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

        elif sub == "daily_gift":
            bot.answer_callback_query(call.id, "🎁 Daily gift claimed! Check back tomorrow.", show_alert=True)
            
        elif sub == "support":
            text = (
                "📞 **Support Center**\n\n"
                "👤 Telegram: @HassanXMods1\n"
                "If you need any help, contact us on Telegram, explain your issue, and wait for our reply."
            )
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

    elif action == "info":
        if data[1] == "sold_out":
            bot.answer_callback_query(call.id, "This category is currently Sold Out!", show_alert=True)
        elif data[1] == "how_to_buy":
            text = (
                "📖 **How to Use — Tutorial Video**\n\n"
                "1. Click Buy Now.\n"
                "2. Select product & validity.\n"
                "3. Pay exact amount via QR / UPI.\n"
                "4. Get Instant Key Delivery."
            )
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

    elif action == "select":
        panel_key = data[1]
        bot.edit_message_text(f"🛒 Select Category for **{PRODUCTS[panel_key]['name']}**:", chat_id, message_id, parse_mode="Markdown", reply_markup=get_category_inline(panel_key))

    elif action == "buy":
        p_key, d_code = data[1], data[2]
        price = PRODUCTS[p_key]["prices"][d_code]
        p_name = PRODUCTS[p_key]["name"]
        cat_label = DAYS_MAP.get(d_code, d_code.upper())

        payment_text = (
            f"👑 💳 — **Hassan X Mod Store** — 👑\n\n"
            f"Panel: {p_name}\nCategory: {cat_label}\nPrice: ₹{price}\n\n"
            f"💳 **UPI ID**: `8171733966@fam`\nName: Harsaan Ali Khan\n\n"
            f"Please pay exact amount and send UTR / Screenshot here."
        )
        
        upi_uri = f"upi://pay?pa=8171733966@fam&pn=Harsaan%20Ali%20Khan&am={price}&cu=INR"
        encoded_upi_uri = urllib.parse.quote_plus(upi_uri)
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={encoded_upi_uri}"
        
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
                for d_code in p_val["prices"].keys():
                    lbl = DAYS_MAP.get(d_code, d_code.upper())
                    markup.add(types.InlineKeyboardButton(f"{p_val['name']} ({lbl})", callback_data=f"admin:addstock:{p_key}:{d_code}"))
            bot.send_message(chat_id, "Select Panel & Plan to Add Key:", reply_markup=markup)

        elif sub_action == "addstock":
            p_key, d_code = data[2], data[3]
            user_states[chat_id] = f"ADDING_KEY:{p_key}:{d_code}"
            lbl = DAYS_MAP.get(d_code, d_code.upper())
            bot.send_message(chat_id, f"📝 Send the key now for **{PRODUCTS[p_key]['name']} ({lbl})**:", parse_mode="Markdown")

        elif sub_action == "view_stock":
            msg = "📊 **Current Stock & Prices:**\n\n"
            for p_key, p_val in PRODUCTS.items():
                msg += f"**{p_val['name']}**:\n"
                for d_code, prc in p_val["prices"].items():
                    cnt = len(stock_keys.get(f"{p_key}:{d_code}", []))
                    lbl = DAYS_MAP.get(d_code, d_code.upper())
                    msg += f" • {lbl}: `{cnt}` Keys | ₹{prc}\n"
                msg += "\n"
            bot.send_message(chat_id, msg, parse_mode="Markdown")

        elif sub_action == "select_price_panel":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p_key, p_val in PRODUCTS.items():
                for d_code, curr_price in p_val["prices"].items():
                    lbl = DAYS_MAP.get(d_code, d_code.upper())
                    markup.add(types.InlineKeyboardButton(f"{p_val['name']} ({lbl}) - ₹{curr_price}", callback_data=f"admin:editprice:{p_key}:{d_code}"))
            bot.send_message(chat_id, "💰 Select Plan to Change Price:", reply_markup=markup)

        elif sub_action == "editprice":
            p_key, d_code = data[2], data[3]
            curr_p = PRODUCTS[p_key]["prices"][d_code]
            user_states[chat_id] = f"UPDATING_PRICE:{p_key}:{d_code}"
            lbl = DAYS_MAP.get(d_code, d_code.upper())
            bot.send_message(chat_id, f"🔢 Current price for **{PRODUCTS[p_key]['name']} ({lbl})** is **₹{curr_p}**.\n\nPlease type and send the **NEW PRICE** (only numbers):", parse_mode="Markdown")

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
                    f"PANEL SETUP AND APK LINK https://t.me/+T-QvHT2k8Pw4NTI9"
                )
                
                bot.send_message(u_id, delivery_msg, parse_mode="Markdown", disable_web_page_preview=True)
                
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
                lbl = DAYS_MAP.get(d_code, d_code.upper())
                bot.send_message(chat_id, f"⚠️ Stock Empty for **{PRODUCTS[p_key]['name']} ({lbl})**! Add key using /admin first.")
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
            lbl = DAYS_MAP.get(d_code, d_code.upper())
            bot.send_message(chat_id, f"✅ **Price Updated Successfully!**\n\n{PRODUCTS[p_key]['name']} ({lbl}) is now **₹{new_price}**", parse_mode="Markdown", reply_markup=get_admin_panel())
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
            lbl = DAYS_MAP.get(d_code, d_code.upper())
            bot.send_message(chat_id, f"✅ **Key added to {PRODUCTS[p_key]['name']} ({lbl})!**\n\nTotal Stock Now: {len(stock_keys[target_stock])}", parse_mode="Markdown", reply_markup=get_admin_panel())
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

        price = PRODUCTS[p_key]["p
