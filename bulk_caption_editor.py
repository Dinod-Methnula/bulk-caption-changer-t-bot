import os
import threading
from flask import Flask
import telebot

# --- CONFIGURATION ---
# We fetch the token securely from Render's Environment Variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
# ---------------------

bot = telebot.TeleBot(BOT_TOKEN)
user_sessions = {}

# Mini web server to satisfy Render's port check
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return "Bot is running perfectly!", 200

@bot.message_handler(commands=['start'])
def start_session(message):
    user_sessions[message.chat.id] = {"grade_12": [], "grade_13": [], "unknown": []}
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except Exception:
        pass

@bot.message_handler(content_types=['document', 'video', 'photo'])
def gather_files(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions:
        user_sessions[chat_id] = {"grade_12": [], "grade_13": [], "unknown": []}
        
    if not message.caption:
        try:
            bot.delete_message(chat_id, message.message_id)
        except Exception:
            pass
        return

    file_data = {
        "type": message.content_type,
        "caption": message.caption,
        "file_id": message.document.file_id if message.content_type == 'document' else 
                   (message.video.file_id if message.content_type == 'video' else message.photo[-1].file_id)
    }

    caption_upper = message.caption.upper()
    if "GRADE 12" in caption_upper or "GR 12" in caption_upper:
        user_sessions[chat_id]["grade_12"].append(file_data)
    elif "GRADE 13" in caption_upper or "GR 13" in caption_upper:
        user_sessions[chat_id]["grade_13"].append(file_data)
    else:
        user_sessions[chat_id]["unknown"].append(file_data)

    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

@bot.message_handler(commands=['done'])
def process_in_order(message):
    chat_id = message.chat.id
    try:
        bot.delete_message(chat_id, message.message_id)
    except Exception:
        pass

    if chat_id not in user_sessions:
        return

    session = user_sessions[chat_id]
    g12_count = len(session["grade_12"])
    g13_count = len(session["grade_13"])
    unk_count = len(session["unknown"])

    def process_and_send(item):
        lines = item["caption"].split('\n')
        cleaned_lines = [line for line in lines if '#' not in line and '@' not in line]
        new_caption = "\n".join(cleaned_lines).strip() + "\n@Combine27"

        if item["type"] == 'document':
            bot.send_document(chat_id, item["file_id"], caption=new_caption)
        elif item["type"] == 'video':
            bot.send_video(chat_id, item["file_id"], caption=new_caption)
        elif item["type"] == 'photo':
            bot.send_photo(chat_id, item["file_id"], caption=new_caption)

    if g12_count > 0:
        bot.send_message(chat_id, "✨ **GRADE 12 FILES** ✨", parse_mode="Markdown")
        for item in session["grade_12"]:
            process_and_send(item)

    if g13_count > 0:
        bot.send_message(chat_id, "✨ **GRADE 13 FILES** ✨", parse_mode="Markdown")
        for item in session["grade_13"]:
            process_and_send(item)

    if unk_count > 0:
        bot.send_message(chat_id, "✨ **UNCLASSIFIED FILES** ✨", parse_mode="Markdown")
        for item in session["unknown"]:
            process_and_send(item)

    total_processed = g12_count + g13_count + unk_count
    summary_text = (
        "📊 **Execution Summary**\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Total Files Processed: {total_processed}\n"
        f"📂 Grade 12 Files: {g12_count}\n"
        f"📂 Grade 13 Files: {g13_count}\n"
        f"❓ Unclassified Files: {unk_count}\n\n"
        "All tags successfully updated to @Combine27!"
    )
    bot.send_message(chat_id, summary_text, parse_mode="Markdown")
    del user_sessions[chat_id]

# Function to run the Telegram Bot polling loop
def run_telegram_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # Start Telegram Bot loop in a separate thread
    threading.Thread(target=run_telegram_bot, daemon=True).start()
    # Run Flask App to keep Render alive
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
