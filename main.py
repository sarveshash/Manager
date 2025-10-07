import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import ChatParticipantAdmin, ChatParticipantCreator
from telethon.errors import ChatAdminRequiredError, UserAdminInvalidError
import json
import os

# ========== BOT CONFIG ==========
API_ID= 27715449
API_HASH= "dd3da7c5045f7679ff1f0ed0c82404e0"
BOT_TOKEN="8397651199:AAGPUiPNlr4AkgGoQK6BWAeyK4uCYL0knJ4"

# ========== FILE TO STORE ACTIVITY ==========
ACTIVITY_FILE = "activity.json"

# Load saved activity data
if os.path.exists(ACTIVITY_FILE):
    with open(ACTIVITY_FILE, "r") as f:
        user_activity = json.load(f)
else:
    user_activity = {}

# ========== INIT TELETHON CLIENT ==========
client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ========== SAVE ACTIVITY ==========
def save_activity():
    with open(ACTIVITY_FILE, "w") as f:
        json.dump(user_activity, f, default=str)

# ========== TRACK USER MESSAGES ==========
@client.on(events.NewMessage)
async def track_activity(event):
    if event.is_group and event.sender_id:
        chat_id = str(event.chat_id)
        user_id = str(event.sender_id)
        now = datetime.utcnow().isoformat()

        if chat_id not in user_activity:
            user_activity[chat_id] = {}

        user_activity[chat_id][user_id] = now
        save_activity()

# ========== /kickall COMMAND ==========
@client.on(events.NewMessage(pattern='/kickall'))
async def kick_all(event):
    chat = await event.get_chat()
    sender = await event.get_sender()

    # Check if sender is admin
    admins = [p.participant.user_id async for p in client.iter_participants(chat, filter=ChatParticipantAdmin)]
    if sender.id not in admins:
        await event.reply("❌ Only admins can use this command.")
        return

    kicked = 0
    async for user in client.iter_participants(chat):
        if isinstance(user.participant, (ChatParticipantAdmin, ChatParticipantCreator)):
            continue  # Skip admins
        try:
            await client.kick_participant(chat, user.id)
            kicked += 1
            await asyncio.sleep(1)
        except UserAdminInvalidError:
            continue
        except ChatAdminRequiredError:
            await event.reply("⚠️ I need 'Ban Members' permission to kick users.")
            return

    await event.reply(f"✅ Kicked {kicked} non-admin members.")

# ========== INACTIVITY CHECKER ==========
async def remove_inactive_users():
    while True:
        now = datetime.utcnow()
        cutoff = now - timedelta(days=4)

        for chat_id, users in list(user_activity.items()):
            for user_id, last_active_str in list(users.items()):
                try:
                    last_active = datetime.fromisoformat(last_active_str)
                except ValueError:
                    continue

                if last_active < cutoff:
                    try:
                        await client.kick_participant(int(chat_id), int(user_id))
                        await client.send_message(
                            int(chat_id),
                            f"👋 Removed inactive user: [User](tg://user?id={user_id}) (inactive >4 days)"
                        )
                        del user_activity[chat_id][user_id]
                        save_activity()
                        await asyncio.sleep(1)
                    except Exception as e:
                        print(f"Error removing {user_id}: {e}")

        await asyncio.sleep(10)  # Run every 24 hours

# ========== RUN BOT ==========
async def main():
    print("✅ Bot started and running...")
    asyncio.create_task(remove_inactive_users())
    await client.run_until_disconnected()

asyncio.run(main())
