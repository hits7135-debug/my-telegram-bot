import os
import json
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

DATA_FILE = "store_data.json"

# Default Initial Products
DEFAULT_PRODUCTS = {
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

DEFAULT_DAYS_MAP = {
    "1d": "1 Day",
    "3d": "3 Days",
    "7d": "7 Days",
    "15d": "15 Days",
    "30d": "30 Days",
    "4bot": "4 Bot",
    "8bot": "8 Bot"
}

# --- LOCAL FILE STORAGE HELPERS ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "products": DEFAULT_PRODUCTS,
        "days_map": DEFAULT_DAYS_MAP,
        "stock": {}
    }

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

# Initialize Data
db = load_data()
PRODUCTS = db.get("products", DEFAULT_PRODUCTS)
DAYS_MAP = db.get("days_map", DEFAULT_DAYS_MAP)
stock_keys = db.get("stock", {})

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

def sync_db():
    save_data({
        "products": PRODUCTS,
        "days_map": DAYS_MAP,
        "stock": stock_keys
    })

# Dynamic Welcome Text
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
    for p_key, p_val in PRODUCTS.items():
        markup.add(types.InlineKeyboardButton(p_val["name"], callback_data=f"select:{p_key}"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Menu", callback_data="nav:go_start"))
    return markup

def get_category_inline(panel_key):
    markup = types.InlineKeyboardMarkup(row_width=1)
    panel_info = PRODUCTS.get(panel_key, {})
    prices = panel_info.get("prices", {})
    
    for day_code, price in prices.items():
        label = DAYS_MAP.get(day_code, day_code.upper())
        stock_list = stock_keys.get(f"{panel_key}:{day_code}", [])
        
        if len(stock_list) > 0:
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
        types.InlineKeyboardButton("➕ Add New Panel", callback_data="admin:add_panel"),
        types.InlineKeyboardButton("🗑 Delete Panel", callback_data="admin:del_panel")
    )
    markup.add(
        types.InlineKeyboardButton("⏳ Add Duration/Plan", callback_data="admin:add_plan"),
        types.InlineKeyboardButton("💰 Update Price", callback_data="admin:select_price_panel")
    )
    markup.add(
        types.InlineKeyboardButton("🔑 Add Key Stock", callback_data="admin:add_key"),
        types.InlineKeyboardButton("📊 View Stock", callback_data="admin:view_stock")
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
        bot.send_message(message.chat.id, "🛠️ **Full Dynamic Admin Panel**", parse_mode="Markdown", reply_markup=get_admin_panel())
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
            welcome_text = get_welcome_text(first_name)
            bot.edit_message_text(welcome_text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_start_inline_menu())

    elif action == "user":
        sub = data[1]
        if sub == "profile":
            text = f"👤 **Profile Info**\n\nName: {first_name}\nUsername: @{call.from_user.username or 'None'}\nID: `{user_id}`"
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())
        elif sub == "purchases":
            if chat_id in user_orders and user_orders[chat_id]:
                orders_txt = "\n\n➖➖➖➖➖➖➖➖➖\n\n".join(user_orders[chat_id])
                text = f"🔑 **Your Active Keys & Orders:**\n\n{orders_txt}"
            else:
                text = "🔑 **Your Orders:**\n\nYou haven't made any purchases yet."
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button(), disable_web_page_preview=True)
        elif sub == "support":
            text = "🎧 **Support Center**\n\n👤 Telegram: @HassanXMods1\nIf you need any help, contact us on Telegram."
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

    elif action == "info":
        if data[1] == "sold_out":
            bot.answer_callback_query(call.id, "This category is currently Sold Out!", show_alert=True)
        elif data[1] == "how_to_buy":
            text = "❓ **How to Use**\n\n1. Click Shop Now.\n2. Select product & validity.\n3. Pay exact amount.\n4. Get Instant Key Delivery."
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

    elif action == "select":
        panel_key = data[1]
        if panel_key in PRODUCTS:
            bot.edit_message_text(f"🛒 Select Category for **{PRODUCTS[panel_key]['name']}**:", chat_id, message_id, parse_mode="Markdown", reply_markup=get_category_inline(panel_key))

    elif action == "buy":
        p_key, d_code = data[1], data[2]
        p_val = PRODUCTS.get(p_key, {})
        price = p_val.get("prices", {}).get(d_code, 0)
        p_name = p_val.get("name", "Panel")
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

    # --- ADMIN ACTIONS ---
    elif action == "admin":
        if not is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ Access Denied!", show_alert=True)
            return

        sub_action = data[1]

        if sub_action == "add_panel":
            user_states[chat_id] = "ADDING_PANEL"
            bot.send_message(chat_id, "📝 Send new panel ID & Name in format:\n`panel_id : Panel Name`\n\nExample:\n`vip_mod : ⚡ VIP MOD PANEL`", parse_mode="Markdown")

        elif sub_action == "del_panel":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p_key, p_val in PRODUCTS.items():
                markup.add(types.InlineKeyboardButton(f"❌ Delete {p_val['name']}", callback_data=f"admin:confirm_del:{p_key}"))
            bot.send_message(chat_id, "Select Panel to Delete:", reply_markup=markup)

        elif sub_action == "confirm_del":
            p_key = data[2]
            if p_key in PRODUCTS:
                del PRODUCTS[p_key]
                sync_db()
                bot.send_message(chat_id, f"✅ **Panel `{p_key}` deleted!**", parse_mode="Markdown", reply_markup=get_admin_panel())

        elif sub_action == "add_plan":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p_key, p_val in PRODUCTS.items():
                markup.add(types.InlineKeyboardButton(p_val["name"], callback_data=f"admin:select_plan_panel:{p_key}"))
            bot.send_message(chat_id, "Select Panel to add new Plan/Duration:", reply_markup=markup)

        elif sub_action == "select_plan_panel":
            p_key = data[2]
            user_states[chat_id] = f"ADDING_PLAN:{p_key}"
            bot.send_message(chat_id, f"📝 Send Plan Details for **{PRODUCTS[p_key]['name']}** in format:\n`plan_code : Plan Name : Price`\n\nExample:\n`1m : 1 Month : 1500`", parse_mode="Markdown")

        elif sub_action == "add_key":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p_key, p_val in PRODUCTS.items():
                for d_code in p_val.get("prices", {}).keys():
                    lbl = DAYS_MAP.get(d_code, d_code.upper())
                    markup.add(types.InlineKeyboardButton(f"{p_val['name']} ({lbl})", callback_data=f"admin:addstock:{p_key}:{d_code}"))
            bot.send_message(chat_id, "Select Plan to Add Key:", reply_markup=markup)

        elif sub_action == "addstock":
            p_key, d_code = data[2], data[3]
            user_states[chat_id] = f"ADDING_KEY:{p_key}:{d_code}"
            lbl = DAYS_MAP.get(d_code, d_code.upper())
            bot.send_message(chat_id, f"📝 Send Key for **{PRODUCTS[p_key]['name']} ({lbl})**:", parse_mode="Markdown")

        elif sub_action == "view_stock":
            msg = "📊 **Current Stock & Prices:**\n\n"
            for p_key, p_val in PRODUCTS.items():
                msg += f"**{p_val['name']}**:\n"
                for d_code, prc in p_val.get("prices", {}).items():
                    cnt = len(stock_keys.get(f"{p_key}:{d_code}", []))
                    lbl = DAYS_MAP.get(d_code, d_code.upper())
                    msg += f" • {lbl}: `{cnt}` Keys | ₹{prc}\n"
                msg += "\n"
            bot.send_message(chat_id, msg, parse_mode="Markdown")

        elif sub_action == "select_price_panel":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for p_key, p_val in PRODUCTS.items():
                for d_code, curr_price in p_val.get("prices", {}).items():
                    lbl = DAYS_MAP.get(d_code, d_code.upper())
                    markup.add(types.InlineKeyboardButton(f"{p_val['name']} ({lbl}) - ₹{curr_price}", callback_data=f"admin:editprice:{p_key}:{d_code}"))
            bot.send_message(chat_id, "💰 Select Plan to Change Price:", reply_markup=markup)

        elif sub_action == "editprice":
            p_key, d_code = data[2], data[3]
            curr_p = PRODUCTS[p_key]["prices"][d_code]
            user_states[chat_id] = f"UPDATING_PRICE:{p_key}:{d_code}"
            lbl = DAYS_MAP.get(d_code, d_code.upper())
            bot.send_message(chat_id, f"🔢 Current price for **{PRODUCTS[p_key]['name']} ({lbl})** is **₹{curr_p}**.\n\nSend NEW PRICE (only numbers):", parse_mode="Markdown")

    elif action == "approve":
        if not is_admin(user_id):
            return

        order_id, p_key, d_code = data[1], data[2], data[3]
        target_stock = f"{p_key}:{d_code}"

        if order_id in pending_orders:
            u_id = pending_orders[order_id]
            stock_list = stock_keys.get(target_stock, [])
            if len(stock_list) > 0:
                key = stock_list.pop(0)
                sync_db()

                game_name = PRODUCTS.get(p_key, {}).get("name", "Panel")
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
                bot.send_message(chat_id, f"⚠️ Stock Empty for **{PRODUCTS.get(p_key, {}).get('name', p_key)} ({lbl})**! Add key using /admin first.")
            del pending_orders[order_id]

    elif action == "cancel":
        if not is_admin(user_id):
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

# --- TEXT / PHOTO INPUT HANDLERS ---
@bot.message_handler(content_types=['text', 'photo'])
def handle_inputs(message):
    chat_id = message.chat.id
    current_state = user_states.get(chat_id)

    if not current_state:
        return

    # 1. ADD NEW PANEL
    if current_state == "ADDING_PANEL" and is_admin(chat_id):
        try:
            p_key, p_name = message.text.split(":")
            p_key = p_key.strip().lower()
            p_name = p_name.strip()

            PRODUCTS[p_key] = {
                "name": p_name,
                "prices": {"1d": 100, "3d": 250, "7d": 450}
            }
            sync_db()
            user_states[chat_id] = None
            bot.send_message(chat_id, f"✅ **New Panel Added Successfully!**\n\nID: `{p_key}`\nName: {p_name}", parse_mode="Markdown", reply_markup=get_admin_panel())
        except Exception:
            bot.send_message(chat_id, "❌ Format Error! Use: `panel_id : Panel Name`\nExample: `vip_mod : ⚡ VIP MOD PANEL`")
        return

    # 2. ADD NEW DURATION / PLAN
    if current_state.startswith("ADDING_PLAN:") and is_admin(chat_id):
        p_key = current_state.split(":")[1]
        try:
            d_code, label, price = message.text.split(":")
            d_code = d_code.strip().lower()
            label = label.strip()
            price = int(price.strip())

            DAYS_MAP[d_code] = label
            if p_key in PRODUCTS:
                PRODUCTS[p_key]["prices"][d_code] = price
            sync_db()

            user_states[chat_id] = None
            bot.send_message(chat_id, f"✅ **New Plan Added to {PRODUCTS[p_key]['name']}!**\n\nPlan Code: `{d_code}`\nLabel: {label}\nPrice: ₹{price}", parse_mode="Markdown", reply_markup=get_admin_panel())
        except Exception:
            bot.send_message(chat_id, "❌ Format Error! Use: `plan_code : Plan Name : Price`\nExample: `1m : 1 Month : 1500`")
        return

    # 3. UPDATE PRICE
    if current_state.startswith("UPDATING_PRICE:") and is_admin(chat_id):
        _, p_key, d_code = current_state.split(":")
  
