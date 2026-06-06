import re
from firebase_functions import https_fn
from firebase_admin import initialize_app, firestore
import telebot

# Initialize Firebase Admin App
initialize_app()
db = firestore.client()

# --- CONFIGURATION ---
BOT_TOKEN = "YOUR_BOT_TOKEN_FROM_BOTFATHER"
# ---------------------

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

@https_fn.on_request()
def telegram_webhook(req: https_fn.Request) -> https_fn.Response:
    """This function wakes up every time Telegram sends a message"""
    if req.method == "POST":
        update = telebot.types.Update.de_json(req.get_text())
        bot.process_new_updates([update])
    return https_fn.Response("OK", status=200)

@bot.message_handler(commands=['start'])
def start_session(message):
    chat_id = str(message.chat.id)
    # Clear any previous session in Firestore database
    db.collection("sessions").document(chat_id).delete()
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

@bot.message_handler(content_types=['document', 'video', 'photo'])
def gather_files(message):
    chat_id = str(message.chat.id)
    if not message.caption:
        try:
            bot.delete_message(message.chat.id, message.message_id)
        except:
            pass
        return

    # Extract File ID based on type
    if message.content_type == 'document':
        file_id = message.document.file_id
    elif message.content_type == 'video':
        file_id = message.video.file_id
    else:
        file_id = message.photo[-1].file_id

    file_data = {
        "type": message.content_type,
        "caption": message.caption,
        "file_id": file_id,
        "timestamp": message.date
    }

    # Determine sorting category
    caption_upper = message.caption.upper()
    if "GRADE 12" in caption_upper or "GR 12" in caption_upper:
        category = "grade_12"
    elif "GRADE 13" in caption_upper or "GR 13" in caption_upper:
        category = "grade_13"
    else:
        category = "unknown"

    # Save directly to free Firebase Cloud Firestore database
    db.collection("sessions").document(chat_id).collection(category).add(file_data)

    # Delete original message from chat instantly
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

@bot.message_handler(commands=['done'])
def process_in_order(message):
    chat_id = str(message.chat.id)
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

    def clean_caption(raw_caption):
        lines = raw_caption.split('\n')
        cleaned_lines = [line for line in lines if '#' not in line and '@' not in line]
        return "\n".join(cleaned_lines).strip() + "\n@Combine27"

    def send_category_files(category_name, label):
        docs = db.collection("sessions").document(chat_id).collection(category_name).order_by("timestamp").stream()
        file_list = [d.to_dict() for d in docs]
        
        if file_list:
            bot.send_message(message.chat.id, f"✨ **{label}** ✨", parse_mode="Markdown")
            for item in file_list:
                new_cap = clean_caption(item["caption"])
                if item["type"] == 'document':
                    bot.send_document(message.chat.id, item["file_id"], caption=new_cap)
                elif item["type"] == 'video':
                    bot.send_video(message.chat.id, item["file_id"], caption=new_cap)
                elif item["type"] == 'photo':
                    bot.send_photo(message.chat.id, item["file_id"], caption=new_cap)
        return len(file_list)

    # Process sequentially: Grade 12 -> Grade 13 -> Unknown
    g12 = send_category_files("grade_12", "GRADE 12 FILES")
    g13 = send_category_files("grade_13", "GRADE 13 FILES")
    unk = send_category_files("unknown", "UNCLASSIFIED FILES")

    # Send summary message
    total = g12 + g13 + unk
    if total > 0:
        summary = (
            "📊 **Execution Summary**\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"✅ Total Files Processed: {total}\n"
            f"📂 Grade 12 Files: {g12}\n"
            f"📂 Grade 13 Files: {g13}\n"
            f"❓ Unclassified Files: {unk}\n\n"
            "All tags successfully updated to @Combine27!"
        )
        bot.send_message(message.chat.id, summary, parse_mode="Markdown")

    # Clear cloud database memory storage for this session
    db.collection("sessions").document(chat_id).delete()
