import os, json, random, string, urllib.parse, requests
from threading import Thread
from flask import Flask, request
import telebot
from telebot import types

RAW_TOKEN = os.environ.get('BOT_TOKEN', '')
TOKEN = RAW_TOKEN.strip().replace('"', '').replace("'", '')
if not TOKEN:
    raise ValueError("BOT_TOKEN Environment Variable is missing in Render!")

ADMIN_IDS = [7172828025, 8705494010]
PRIMARY_ADMIN_ID = 7172828025

# ✅ CORRECT API URL & DETAILS FROM YOUR API PANEL
API_URL = "https://xyzcheats.com/api/reseller_v1.php"
API_KEY = os.environ.get('RESELLER_API_KEY', 'ef64b0bb9cac3d11ec8544c769381')
MASTER_KEY = "a7f3e8b2c9d1f4a6b8c"
DEFAULT_BALA_PID = "133"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)
DATA_FILE = "store_data.json"

DEFAULT_PRODUCTS = {
    "bala_mod_pro": {"name": "⚡ BALA MOD PRO (AUTO API)", "prices": {"1h": 10, "3h": 30, "6h": 60, "12h": 120, "1d": 240}},
    "main_id": {"name": "🛒 MAIN ID PANEL", "prices": {"1d": 100, "3d": 250, "7d": 450, "15d": 800, "30d": 1200}},
    "prime": {"name": "💧 PRIME HOOK", "prices": {"1d": 60, "3d": 140, "7d": 250, "15d": 400, "30d": 600}},
    "drip": {"name": "🔺 DRIP CLIENT", "prices": {"1d": 60, "3d": 140, "7d": 250, "15d": 400, "30d": 600}},
    "guild_glory": {"name": "🏆 GUILD GLORY BOT", "prices": {"4bot": 119, "8bot": 235}}
}

# ✅ EXACT DURATION MAP MATCHING YOUR PANEL SCREENSHOT
DAYS_MAP = {
    "1h": "1 Hours",
    "3h": "3 Hours",
    "6h": "6 Hours",
    "12h": "12 Hours",
    "1d": "1 DaYs",
    "2d": "2 DaYs",
    "3d": "3 DaYs",
    "5d": "5 DaYs",
    "7d": "7 DaYs",
    "15d": "15 DaYs",
    "30d": "30 DaYs",
    "4bot": "4 Bot",
    "8bot": "8 Bot"
}

DEFAULT_DELIVERY_CONFIG = {
    "link": "https://t.me/+T-QvHT2k8Pw4NTI9",
    "footer": "🙏 Thank you for your purchase!"
}

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"products": DEFAULT_PRODUCTS, "days_map": DAYS_MAP, "stock": {}, "users": [], "delivery": DEFAULT_DELIVERY_CONFIG}

def save_data(data):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception:
        pass

db = load_data()
PRODUCTS = db.get("products", DEFAULT_PRODUCTS)
stock_keys = db.get("stock", {})
bot_users = db.get("users", [])
delivery_cfg = db.get("delivery", DEFAULT_DELIVERY_CONFIG)
pending_orders, user_orders, user_states, last_bot_messages, pending_android_ids = {}, {}, {}, {}, {}

def is_admin(user_id):
    return user_id in ADMIN_IDS

def safe_delete(chat_id, message_id):
    try:
        bot.delete_message(chat_id, message_id)
    except Exception:
        pass

def sync_db():
    save_data({"products": PRODUCTS, "days_map": DAYS_MAP, "stock": stock_keys, "users": list(set(bot_users)), "delivery": delivery_cfg})

def generate_api_key(duration_label, android_id="0b9b969bc2e7997b"):
    try:
        payload = {
            'api_key': API_KEY, 
            'action': 'buy', 
            'product_id': DEFAULT_BALA_PID, 
            'duration': duration_label, 
            'android_id': android_id
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded', 
            'x-master-key': MASTER_KEY
        }
        res = requests.post(API_URL, data=payload, headers=headers, timeout=15)
        try:
            res_json = res.json()
            if res_json.get("status") == "success" or "key" in res_json:
                return res_json.get("key") or res_json.get("license_key") or str(res_json)
        except Exception:
            pass
        if res.text and len(res.text.strip()) > 0 and "error" not in res.text.lower():
            return res.text.strip()
        return None
    except Exception:
        return None

def get_welcome_text(first_name):
    return f"👋 Welcome, {first_name}\n\n★ — 👑 Hassan X Mod Store 👑 — ★\n\n🔑 Premium All Best Mod Keys\n⚡ Instant Delivery 24/7\n🔒 100% Secure Payment\n🏷 Best Prices Guaranteed\n🎁 High Discount Rewards\n🎧 Active Support For Set-Up\n\n🚀 Tap Shop Now To Start!"

def get_start_inline_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(types.InlineKeyboardButton("🛒 Shop Now", callback_data="nav:open_shop"))
    markup.add(types.InlineKeyboardButton("🔑 My Orders", callback_data="user:purchases"), types.InlineKeyboardButton("👤 Profile", callback_data="user:profile"))
    markup.add(types.InlineKeyboardButton("❓ How to Use", callback_data="info:how_to_buy"), types.InlineKeyboardButton("🎧 Support", callback_data="user:support"))
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
        if panel_key == "bala_mod_pro":
            btn_text = f"{label} - ₹{price} (Auto Key)"
            c_data = f"buy:{panel_key}:{day_code}"
        else:
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
    markup.add(types.InlineKeyboardButton("➕ Add New Panel", callback_data="admin:add_panel"), types.InlineKeyboardButton("✏️ Edit Panel Name", callback_data="admin:edit_panel_name"))
    markup.add(types.InlineKeyboardButton("🗑 Delete Panel", callback_data="admin:del_panel"), types.InlineKeyboardButton("⏳ Add Plan", callback_data="admin:add_plan"))
    markup.add(types.InlineKeyboardButton("❌ Delete Plan", callback_data="admin:del_plan"), types.InlineKeyboardButton("💰 Update Price", callback_data="admin:select_price_panel"))
    markup.add(types.InlineKeyboardButton("🔑 Add Key Stock", callback_data="admin:add_key"), types.InlineKeyboardButton("📊 View Stock", callback_data="admin:view_stock"))
    markup.add(types.InlineKeyboardButton("🔗 Edit Setup Link", callback_data="admin:edit_delivery_link"), types.InlineKeyboardButton("📝 Edit Delivery Msg", callback_data="admin:edit_delivery_msg"))
    markup.add(types.InlineKeyboardButton("📢 Broadcast Msg", callback_data="admin:broadcast"))
    return markup

@app.route('/', methods=['GET'])
def home():
    return "Bot Server Active!"

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

@bot.message_handler(content_types=['text', 'photo'])
def handle_all_user_inputs(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    
    # Check Admin Input States
    if is_admin(chat_id) and state:
        if state.startswith("UPDATING_PRICE:"):
            _, pk, dc = state.split(":")
            if message.text and message.text.isdigit():
                PRODUCTS[pk]["prices"][dc] = int(message.text)
                sync_db()
                bot.send_message(chat_id, f"✅ Price updated to ₹{message.text}!", reply_markup=get_admin_panel())
                user_states[chat_id] = None
                return
        elif state.startswith("ADDING_KEY:"):
            _, pk, dc = state.split(":")
            if message.text:
                k_key = f"{pk}:{dc}"
                if k_key not in stock_keys: stock_keys[k_key] = []
                keys = [k.strip() for k in message.text.split("\n") if k.strip()]
                stock_keys[k_key].extend(keys)
                sync_db()
                bot.send_message(chat_id, f"✅ Added {len(keys)} key(s) to stock!", reply_markup=get_admin_panel())
                user_states[chat_id] = None
                return
        elif state == "EDIT_DELIVERY_LINK":
            delivery_cfg["link"] = message.text.strip()
            sync_db()
            bot.send_message(chat_id, "✅ Setup Link Updated!", reply_markup=get_admin_panel())
            user_states[chat_id] = None
            return
        elif state == "EDIT_DELIVERY_MSG":
            delivery_cfg["footer"] = message.text.strip()
            sync_db()
            bot.send_message(chat_id, "✅ Delivery Message Updated!", reply_markup=get_admin_panel())
            user_states[chat_id] = None
            return
        elif state == "BROADCAST_MSG":
            count = 0
            for u in bot_users:
                try:
                    bot.copy_message(u, chat_id, message.message_id)
                    count += 1
                except Exception:
                    pass
            bot.send_message(chat_id, f"📢 Broadcast Sent to {count} users!", reply_markup=get_admin_panel())
            user_states[chat_id] = None
            return

    # Check User Payment Proof Submission
    if state and str(state).startswith("WAITING_PROOF:"):
        _, p_key, d_code = state.split(":")
        order_id = f"ORD_{random.randint(1000, 9999)}"
        pending_orders[order_id] = chat_id
        if p_key == "bala_mod_pro" and message.content_type == 'text':
            pending_android_ids[order_id] = message.text.strip()
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton("✅ Approve", callback_data=f"approve:{order_id}:{p_key}:{d_code}"), types.InlineKeyboardButton("❌ Reject", callback_data=f"reject:{order_id}"))
        p_name = PRODUCTS.get(p_key, {}).get("name", "Panel")
        d_label = DAYS_MAP.get(d_code, d_code)
        admin_txt = f"📥 **NEW ORDER RECEIVED**\n\n👤 User: {message.from_user.first_name} (`{chat_id}`)\n🛒 Panel: {p_name}\n⌛ Validity: {d_label}\n🆔 Order ID: `{order_id}`\n"
        if message.text:
            admin_txt += f"📝 Note/Android ID: `{message.text}`\n"
        for admin_id in ADMIN_IDS:
            try:
                if message.content_type == 'photo':
                    bot.send_photo(admin_id, message.photo[-1].file_id, caption=admin_txt, parse_mode="Markdown", reply_markup=markup)
                else:
                    bot.send_message(admin_id, admin_txt, parse_mode="Markdown", reply_markup=markup)
            except Exception:
                pass
        bot.send_message(chat_id, "✅ **Payment Proof Received!**\nYour payment is being verified by Admin. Key will be delivered shortly.")
        user_states[chat_id] = None

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
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("✅ I Have Paid", callback_data=f"paid:{p_key}:{d_code}"), types.InlineKeyboardButton("❌ Cancel Order", callback_data="cancel_qr"))
        sent_qr = bot.send_photo(chat_id, qr_url, caption=payment_text, parse_mode="Markdown", reply_markup=markup)
        last_bot_messages[chat_id] = sent_qr.message_id

    elif action == "cancel_qr":
        safe_delete(chat_id, message_id)
        user_states[chat_id] = None
        bot.send_message(chat_id, get_welcome_text(first_name), reply_markup=get_start_inline_menu())

    elif action == "paid":
        p_key, d_code = data[1], data[2]
        user_states[chat_id] = f"WAITING_PROOF:{p_key}:{d_code}"
        if chat_id in last_bot_messages: safe_delete(chat_id, last_bot_messages[chat_id])
        if p_key == "bala_mod_pro":
            msg = bot.send_message(chat_id, "📸 Send your **Screenshot/UTR** AND **Android ID** (e.g., `0b9b969bc2e7997b`):")
        else:
            msg = bot.send_message(chat_id, "📸 Send your **12-digit UTR / Screenshot** here:")
        last_bot_messages[chat_id] = msg.message_id

    elif action == "admin":
        if not is_admin(user_id): return
        sub = data[1]
        if sub == "add_panel":
            user_states[chat_id] = "ADDING_PANEL"
            bot.send_message(chat_id, "📝 Send: `panel_id : Panel Name`\nEx: `vip : ⚡ VIP PANEL`", parse_mode="Markdown")
        elif sub == "edit_panel_name":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for pk, pv in PRODUCTS.items():
                markup.add(types.InlineKeyboardButton(f"✏️ {pv['name']}", callback_data=f"admin:rename_panel:{pk}"))
            bot.send_message(chat_id, "Select Panel to Edit/Rename:", reply_markup=markup)
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
        elif sub == "add_key":
            markup = types.InlineKeyboardMarkup(row_width=1)
            for pk, pv in PRODUCTS.items():
                if pk == "bala_mod_pro": continue
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
                if pk == "bala_mod_pro":
                    msg += " • Unlimited (Auto API Connected)\n"
                else:
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
        elif sub == "edit_delivery_link":
            user_states[chat_id] = "EDIT_DELIVERY_LINK"
            curr_link = delivery_cfg.get("link", "None")
            bot.send_message(chat_id, f"🔗 Current Setup Link:\n`{curr_link}`\n\nSend NEW URL/LINK:", parse_mode="Markdown")
        elif sub == "edit_delivery_msg":
            user_states[chat_id] = "EDIT_DELIVERY_MSG"
            curr_footer = delivery_cfg.get("footer", "🙏 Thank you for your purchase!")
            bot.send_message(chat_id, f"📝 Current Thank You Message:\n`{curr_footer}`\n\nSend NEW Thank You message:", parse_mode="Markdown")
        elif sub == "broadcast":
            user_states[chat_id] = "BROADCAST_MSG"
            bot.send_message(chat_id, "📢 Send message to broadcast (Text, Photo, Voice, Video, etc.):", parse_mode="Markdown")

    elif action == "approve":
        if not is_admin(user_id): return
        order_id, pk, dc = data[1], data[2], data[3]
        if order_id in pending_orders:
            uid = pending_orders[order_id]
            gname = PRODUCTS.get(pk, {}).get("name", "Panel")
            dstr = DAYS_MAP.get(dc, dc.upper())
            cur_link = delivery_cfg.get("link", "https://t.me/+T-QvHT2k8Pw4NTI9")
            cur_footer = delivery_cfg.get("footer", "🙏 Thank you for your purchase!")
            
            final_key = None
            if pk == "bala_mod_pro":
                usr_android_id = pending_android_ids.get(order_id, "0b9b969bc2e7997b")
                final_key = generate_api_key(dstr, usr_android_id)
            else:
                k_key = f"{pk}:{dc}"
                if k_key in stock_keys and len(stock_keys[k_key]) > 0:
                    final_key = stock_keys[k_key].pop(0)
                    sync_db()

            if final_key:
                del_msg = f"🎉 **YOUR ORDER HAS BEEN APPROVED!**\n\n🛒 Panel: {gname}\n⌛ Validity: {dstr}\n🔑 **License Key**:\n`{final_key}`\n\n🔗 **Setup Guide / Download**: {cur_link}\n\n{cur_footer}"
                try:
                    bot.send_message(uid, del_msg, parse_mode="Markdown")
                    if uid not in user_orders: user_orders[uid] = []
                    user_orders[uid].append(f"🛒 {gname} ({dstr})\n🔑 `{final_key}`")
                    bot.send_message(chat_id, f"✅ Order `{order_id}` Approved & Key Delivered!")
                except Exception:
                    bot.send_message(chat_id, f"❌ Failed to deliver key to user {uid}.")
            else:
                bot.send_message(chat_id, f"❌ **Key generation failed!**\nAPI Error 402 (Insufficient Reseller Balance / Server Issue). Please contact support.")
            
            del pending_orders[order_id]

    elif action == "reject":
        if not is_admin(user_id): return
        order_id = data[1]
        if order_id in pending_orders:
            uid = pending_orders[order_id]
            try:
                bot.send_message(uid, "❌ **Your Order Was Rejected.**\nPayment proof invalid or mismatch.")
            except Exception:
                pass
            bot.send_message(chat_id, f"❌ Order `{order_id}` Rejected!")
            del pending_orders[order_id]

def run_flask():
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    Thread(target=run_flask).start()
    bot.infinity_polling()