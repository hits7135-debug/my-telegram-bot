import os, json, random, string, urllib.parse
from flask import Flask, request
import telebot
from telebot import types

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_IDS = [7172828025, 8705494010]
PRIMARY_ADMIN_ID = 7172828025

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
DATA_FILE = "store_data.json"

DEFAULT_PRODUCTS = {
    "main_id": {"name": "🛒 MAIN ID PANEL", "prices": {"1d": 100, "3d": 250, "7d": 450, "15d": 800, "30d": 1200}},
    "prime": {"name": "💧 PRIME HOOK", "prices": {"1d": 60, "3d": 140, "7d": 250, "15d": 400, "30d": 600}},
    "drip": {"name": "🔺 DRIP CLIENT", "prices": {"1d": 60, "3d": 140, "7d": 250, "15d": 400, "30d": 600}},
    "guild_glory": {"name": "🏆 GUILD GLORY BOT", "prices": {"4bot": 119, "8bot": 235}}
}

DEFAULT_DAYS_MAP = {
    "1h": "1 Hour", "3h": "3 Hours", "6h": "6 Hours",
    "1d": "1 Day", "3d": "3 Days", "7d": "7 Days", 
    "15d": "15 Days", "30d": "30 Days", "4bot": "4 Bot", "8bot": "8 Bot"
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"products": DEFAULT_PRODUCTS, "days_map": DEFAULT_DAYS_MAP, "stock": {}, "users": []}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

db = load_data()
PRODUCTS = db.get("products", DEFAULT_PRODUCTS)
DAYS_MAP = db.get("days_map", DEFAULT_DAYS_MAP)
stock_keys = db.get("stock", {})
bot_users = db.get("users", [])

pending_orders, user_orders, user_states, last_bot_messages = {}, {}, {}, {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def sync_db():
    save_data({"products": PRODUCTS, "days_map": DAYS_MAP, "stock": stock_keys, "users": list(set(bot_users))})

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
    prices = PRODUCTS.get(panel_key, {}).get("prices", {})
    for day_code, price in prices.items():
        label = DAYS_MAP.get(day_code, day_code.upper())
        stock_list = stock_keys.get(f"{panel_key}:{day_code}", [])
        btn_text = f"{label} - ₹{price}" if len(stock_list) > 0 else f"{label} - ❌ Sold Out"
        c_data = f"buy:{panel_key}:{day_code}" if len(stock_list) > 0 else "info:sold_out"
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
        types.InlineKeyboardButton("⏳ Add Plan", callback_data="admin:add_plan"),
        types.InlineKeyboardButton("❌ Delete Plan", callback_data="admin:del_plan")
    )
    markup.add(
        types.InlineKeyboardButton("💰 Update Price", callback_data="admin:select_price_panel"),
        types.InlineKeyboardButton("🔑 Add Key Stock", callback_data="admin:add_key")
    )
    markup.add(
        types.InlineKeyboardButton("📊 View Stock", callback_data="admin:view_stock"),
        types.InlineKeyboardButton("📢 Broadcast Msg", callback_data="admin:broadcast")
    )
    return markup

@app.route('/', methods=['GET'])
def home():
    return "Bot Server Active!"

@app.route(f'/{TOKEN}', methods=['POST', 'GET'])
def webhook():
    if request.method == 'POST' and request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return 'OK', 200
    return 'Active', 200

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_states[message.chat.id] = None
    if message.chat.id not in bot_users:
        bot_users.append(message.chat.id)
        sync_db()
    bot.send_message(message.chat.id, get_welcome_text(message.from_user.first_name or "User"), reply_markup=get_start_inline_menu())

@bot.message_handler(commands=['admin'])
def admin_command(message):
    if is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "🛠️ **Full Dynamic Admin Control Panel**", parse_mode="Markdown", reply_markup=get_admin_panel())

@bot.callback_query_handler(func=lambda call: True)
def callback_listener(call):
    chat_id, user_id, message_id = call.message.chat.id, call.from_user.id, call.message.message_id
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
            bot.edit_message_text(get_welcome_text(first_name), chat_id, message_id, parse_mode="Markdown", reply_markup=get_start_inline_menu())

    elif action == "user":
        sub = data[1]
        if sub == "profile":
            text = f"👤 **Profile Info**\n\nName: {first_name}\nUsername: @{call.from_user.username or 'None'}\nID: `{user_id}`"
            bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())
        elif sub == "purchases":
            orders_txt = "\n\n".join(user_orders.get(chat_id, [])) if user_orders.get(chat_id) else "You haven't made any purchases yet."
            bot.edit_message_text(f"🔑 **Your Active Keys & Orders:**\n\n{orders_txt}", chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button(), disable_web_page_preview=True)
        elif sub == "support":
            bot.edit_message_text("🎧 **Support Center**\n\n👤 Telegram: @HassanXMods1", chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

    elif action == "info":
        if data[1] == "sold_out":
            bot.answer_callback_query(call.id, "Sold Out!", show_alert=True)
        elif data[1] == "how_to_buy":
            bot.edit_message_text("❓ **How to Use**\n\n1. Click Shop Now.\n2. Select product & validity.\n3. Pay exact amount.\n4. Get Instant Key Delivery.", chat_id, message_id, parse_mode="Markdown", reply_markup=get_back_button())

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
        payment_text = f"👑 💳 — **Hassan X Mod Store** — 👑\n\nPanel: {p_name}\nCategory: {cat_label}\nPrice: ₹{price}\n\n💳 **UPI ID**: `8171733966@fam`\nName: Harsaan Ali Khan\n\nPlease pay exact amount and send Screenshot."
        upi_uri = f"upi://pay?pa=8171733966@fam&pn=Harsaan%20Ali%20Khan&am={price}&cu=INR"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote_plus(upi_uri)}"
        safe_delete(chat_id, message_id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid:{p_key}:{d_code}"))
        sent_qr = bot.send_photo(chat_id, qr_url, caption=payment_text, parse_mode="Markdown", reply_markup=markup)
        last_bot_messages[chat_id] = sent_qr.message_id

    elif action == "paid":
        p_key, d_code = data[1], data[2]
        user_states[chat_id] = f"WAITING_PROOF:{p_key}:{d_code}"
        if chat_id in last_bot_messages: safe_delete(chat_id, last_bot_messages[chat_id])
        msg = bot.send_message(chat_id, "📸 Send your **12-digit UTR / Screenshot** here:")
        last_bot_messages[chat_id] = msg.message_id

    elif action == "admin":
        if not is_admin(user_id): return
        sub = data[1]
        if sub == "add_panel":
            user_states[chat_id] = "ADDING_PANEL"
            bot.send_message(chat_id, "📝 Send: `panel_id : Panel Name`\nEx: `vip : ⚡ VIP PANEL`", parse_mode="Markdown")
        elif sub == "del_panel":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for pk, pv in PRODUCTS.items(): markup.add(types.InlineKeyboardButton(f"❌ Delete {pv['name']}", callback_data=f"admin:confirm_del:{pk}"))
            bot.send_message(chat_id, "Select Panel to Delete:", reply_markup=markup)
        elif sub == "confirm_del":
            pk = data[2]
            if pk in PRODUCTS:
                del PRODUCTS[pk]
                sync_db()
                bot.send_message(chat_id, f"✅ Panel `{pk}` deleted!", parse_mode="Markdown", reply_markup=get_admin_panel())
        elif sub == "add_plan":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for pk, pv in PRODUCTS.items(): markup.add(types.InlineKeyboardButton(pv["name"], callback_data=f"admin:select_plan_panel:{pk}"))
            bot.send_message(chat_id, "Select Panel to Add Plan:", reply_markup=markup)
        elif sub == "del_plan":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for pk, pv in PRODUCTS.items():
                for dc in pv.get("prices", {}).keys():
                    markup.add(types.InlineKeyboardButton(f"❌ {pv['name']} - {DAYS_MAP.get(dc, dc.upper())}", callback_data=f"admin:confirm_del_plan:{pk}:{dc}"))
            bot.send_message(chat_id, "Select Plan to Delete:", reply_markup=markup)
        elif sub == "confirm_del_plan":
            pk, dc = data[2], data[3]
            if pk in PRODUCTS and dc in PRODUCTS[pk]["prices"]:
                del PRODUCTS[pk]["prices"][dc]
                sync_db()
                bot.send_message(chat_id, f"✅ Plan deleted successfully!", parse_mode="Markdown", reply_markup=get_admin_panel())
        elif sub == "select_plan_panel":
            user_states[chat_id] = f"ADDING_PLAN:{data[2]}"
            bot.send_message(chat_id, "📝 Send: `code : Name : Price`\nEx: `1h : 1 Hour : 49`", parse_mode="Markdown")
        elif sub == "add_key":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for pk, pv in PRODUCTS.items():
                for dc in pv.get("prices", {}).keys():
                    markup.add(types.InlineKeyboardButton(f"{pv['name']} ({DAYS_MAP.get(dc, dc.upper())})", callback_data=f"admin:addstock:{pk}:{dc}"))
            bot.send_message(chat_id, "Select Plan:", reply_markup=markup)
        elif sub == "addstock":
            user_states[chat_id] = f"ADDING_KEY:{data[2]}:{data[3]}"
            bot.send_message(chat_id, f"📝 Send Key for **{PRODUCTS[data[2]]['name']}**:", parse_mode="Markdown")
        elif sub == "view_stock":
            msg = "📊 **Current Stock:**\n\n"
            for pk, pv in PRODUCTS.items():
                msg += f"**{pv['name']}**:\n"
                for dc, prc in pv.get("prices", {}).items():
                    cnt = len(stock_keys.get(f"{pk}:{dc}", []))
                    msg += f" • {DAYS_MAP.get(dc, dc.upper())}: `{cnt}` Keys | ₹{prc}\n"
                msg += "\n"
            bot.send_message(chat_id, msg, parse_mode="Markdown")
        elif sub == "select_price_panel":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for pk, pv in PRODUCTS.items():
                for dc, cp in pv.get("prices", {}).items():
                    markup.add(types.InlineKeyboardButton(f"{pv['name']} ({DAYS_MAP.get(dc, dc.upper())}) - ₹{cp}", callback_data=f"admin:editprice:{pk}:{dc}"))
            bot.send_message(chat_id, "Select Plan:", reply_markup=markup)
        elif sub == "editprice":
            user_states[chat_id] = f"UPDATING_PRICE:{data[2]}:{data[3]}"
            bot.send_message(chat_id, f"🔢 Send NEW PRICE (only numbers):", parse_mode="Markdown")
        elif sub == "broadcast":
            user_states[chat_id] = "BROADCAST_MSG"
            bot.send_message(chat_id, "📢 Send message to broadcast to ALL bot users:", parse_mode="Markdown")

    elif action == "approve":
        if not is_admin(user_id): return
        order_id, pk, dc = data[1], data[2], data[3]
        if order_id in pending_orders:
            uid = pending_orders[order_id]
            st_list = stock_keys.get(f"{pk}:{dc}", [])
            if len(st_list) > 0:
                key = st_list.pop(0)
                sync_db()
                gname = PRODUCTS.get(pk, {}).get("name", "Panel")
                dstr = DAYS_MAP.get(dc, dc.upper())
                bot.send_message(uid, f"✅ Payment Successful!\n🎮 Game: {gname}\n⌛ Duration: {dstr}\n🔑 Key: `{key}`\n\nLink: https://t.me/+T-QvHT2k8Pw4NTI9", parse_mode="Markdown", disable_web_page_preview=True)
                if uid not in user_orders: user_orders[uid] = []
                user_orders[uid].append(f"🎮 **{gname}** | {dstr}\n🔑 Key: `{key}`")
                try: bot.edit_message_caption(caption=call.message.caption + "\n\n✅ APPROVED", chat_id=chat_id, message_id=message_id, reply_markup=None)
                except Exception: pass
            else:
                bot.send_message(chat_id, "⚠️ Stock Empty!")
            del pending_orders[order_id]

    elif action == "cancel":
        if not is_admin(user_id): return
        order_id = data[1]
        if order_id in pending_orders:
            bot.send_message(pending_orders[order_id], "❌ **Payment Rejected**", parse_mode="Markdown")
            try: bot.edit_message_caption(caption=call.message.caption + "\n\n❌ CANCELLED", chat_id=chat_id, message_id=message_id, reply_markup=None)
            except Exception: pass
            del pending_orders[order_id]

@bot.message_handler(content_types=['text', 'photo'])
def handle_inputs(message):
    chat_id = message.chat.id
    current_state = user_states.get(chat_id)
    if not current_state: return

    if current_state == "ADDING_PANEL" and is_admin(chat_id):
        try:
            pk, pn = message.text.split(":")
            PRODUCTS[pk.strip().lower()] = {"name": pn.strip(), "prices": {}}
            sync_db()
            user_states[chat_id] = None
            bot.send_message(chat_id, "✅ **New Panel Added!** Now add plans using `Add Plan` button.", parse_mode="Markdown", reply_markup=get_admin_panel())
        except Exception:
            bot.send_message(chat_id, "❌ Format Error! Use: `id : Name`")

    elif current_state.startswith("ADDING_PLAN:") and is_admin(chat_id):
        pk = current_state.split(":")[1]
        try:
            dc, lbl, prc = message.text.split(":")
            DAYS_MAP[dc.strip().lower()] = lbl.strip()
            if pk in PRODUCTS: PRODUCTS[pk]["prices"][dc.strip().lower()] = int(prc.strip())
            sync_db()
            user_states[chat_id] = None
            bot.send_message(chat_id, "✅ **New Plan Added!**", parse_mode="Markdown", reply_markup=get_admin_panel())
        except Exception:
            bot.send_message(chat_id, "❌ Format Error! Use: `code : Name : Price`")

    elif current_state.startswith("UPDATING_PRICE:") and is_admin(chat_id):
        _, pk, dc = current_state.split(":")
        if message.text and message.text.strip().isdigit():
            PRODUCTS[pk]["prices"][dc] = int(message.text.strip())
            sync_db()
            user_states[chat_id] = None
            bot.send_message(chat_id, "✅ **Price Updated!**", parse_mode="Markdown", reply_markup=get_admin_panel())

    elif current_state.startswith("ADDING_KEY:") and is_admin(chat_id):
        _, pk, dc = current_state.split(":")
        key = message.text.strip() if message.text else ""
        if key:
            stock_keys.setdefault(f"{pk}:{dc}", []).append(key)
            sync_db()
            user_states[chat_id] = None
            bot.send_message(chat_id, f"✅ **Key added! Total: {len(stock_keys[f'{pk}:{dc}'])}**", parse_mode="Markdown", reply_markup=get_admin_panel())

    elif current_state == "BROADCAST_MSG" and is_admin(chat_id):
        user_states[chat_id] = None
        count = 0
        for uid in bot_users:
            try:
                bot.send_message(uid, f"📢 **Announcement:**\n\n{message.text}", parse_mode="Markdown")
                count += 1
            except Exception:
                pass
        bot.send_message(chat_id, f"✅ **Broadcast Sent to {count} users!**", parse_mode="Markdown", reply_markup=get_admin_panel())

    elif current_state.startswith("WAITING_PROOF:"):
        _, pk, dc = current_state.split(":")
        order_id = f"ORD-{''.join(random.choices(string.digits, k=10))}"
        pending_orders[order_id] = chat_id
        user_states[chat_id] = None
        if chat_id in last_bot_messages: safe_delete(chat_id, last_bot_messages[chat_id])
        safe_delete(chat_id, message.message_id)
        bot.send_message(chat_id, f"✅ **Payment proof received!** Order ID: `{order_id}`", parse_mode="Markdown")
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve:{order_id}:{pk}:{dc}"), types.InlineKeyboardButton("❌ Cancel", callback_data=f"cancel:{order_id}"))
        price = PRODUCTS.get(pk, {}).get("prices", {}).get(dc, 0)
        admin_msg = f"📩 **New Payment Proof!**\nOrder: `{order_id}`\nPanel: {PRODUCTS.get(pk, {}).get('name')}\nCategory: {DAYS_MAP.get(dc, dc.upper())}\nAmount: ₹{price}\nUser: @{message.from_user.username or 'NoUser'} (`{chat_id}`)"
        if message.photo:
            bot.send_photo(PRIMARY_ADMIN_ID, message.photo[-1].file_id, caption=admin_msg, parse_mode="Markdown", reply_markup=markup)
        else:
            bot.send_message(PRIMARY_ADMIN_ID, f"{admin_msg}\nProof: {message.text}", parse_mode="Markdown", reply_markup=markup)

if __name__ == "__main__":
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"https://my-telegram-bot-kamx.onrender.com/{TOKEN}")
    except Exception:
        pass
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
    
