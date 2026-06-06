import asyncio
import re
from pyrogram import Client
from pyrogram.errors import FloodWait

# --- CONFIGURATION AREA ---
API_ID = 1234567          # Replace with your 7-digit API ID
API_HASH = "your_api_hash"  # Replace with your API Hash string

# Target Chat/Channel ID (Can be an integer like -100123456789 or a username like "@my_channel")
CHAT_ID = -100123456789   

# If you want to run this as a regular bot, put your token here. 
# If left as None, it will run as a Userbot (logging into your personal account).
BOT_TOKEN = None  
# --------------------------

if BOT_TOKEN:
    app = Client("caption_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
else:
    app = Client("caption_user", api_id=API_ID, api_hash=API_HASH)

async def main():
    async with app:
        print("🤖 Script started! Fetching messages...")
        updated_count = 0
        
        # Regex pattern to find the specific block text regardless of extra spaces or newlines
        # This looks for "2020", followed by "#COMBINED_MATHS", followed by "@SL_EDUCATION_A_L"
        target_pattern = r"2020\s*#COMBINED_MATHS\s*@SL_EDUCATION_A_L"
        replacement_text = "@Combine27"

        # Iterate through all messages in the chat history
        async for message in app.get_chat_history(CHAT_ID):
            # Check if the message contains a media file with a caption
            if message.caption:
                old_caption = message.caption
                
                # Check if our target pattern exists in the caption
                if re.search(target_pattern, old_caption, re.IGNORECASE):
                    # Perform the replacement
                    new_caption = re.sub(target_pattern, replacement_text, old_caption, flags=re.IGNORECASE)
                    
                    try:
                        # Update the caption on Telegram
                        await app.edit_message_caption(
                            chat_id=CHAT_ID,
                            message_id=message.id,
                            caption=new_caption
                        )
                        updated_count += 1
                        print(f"✅ [{updated_count}] Updated caption for Message ID: {message.id}")
                        
                        # Short pause to prevent hitting Telegram's rate limits too fast
                        await asyncio.sleep(1)
                        
                    except FloodWait as e:
                        print(f"⚠️ Hit Telegram rate limit. Sleeping for {e.value} seconds...")
                        await asyncio.sleep(e.value)
                    except Exception as e:
                        print(f"❌ Failed to update message {message.id}: {e}")
        
        print(f"\n🎉 Task complete! Successfully updated {updated_count} captions.")

if __name__ == "__main__":
    app.run(main())
