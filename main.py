import asyncio
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.tl.types import ChannelParticipantsAdmins
from telethon.errors import ChatAdminRequiredError, UserAdminInvalidError
import json
import os

API_ID = 27715449
API_HASH = "dd3da7c5045f7679ff1f0ed0c82404e0"
BOT_TOKEN = "8397651199:AAGPUiPNlr4AkgGoQK6BWAeyK4uCYL0knJ4"

ACTIVITY_FILE = "activity.json"

if os.path.exists(ACTIVITY_FILE):
    with open(ACTIVITY_FILE, "r") as f:
        user_activity = json.load(f)
else:
    user_activity = {}

client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

def save_activity():
    with open(ACTIVITY_FILE, "w") as f:
        json.dump(user_activity, f, default=str)

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

@client.on(events.NewMessage(pattern='/kickall'))
async def kick_all(event):
    chat = await event.get_chat()
    sender = await event.get_sender()

    admin_ids = []
    async for admin in client.iter_participants(chat, filter=ChannelParticipantsAdmins()):
        admin_ids.append(admin.id)
    
    if sender.id not in admin_ids:
        await event.reply("❌ Only admins can use this command.")
        return

    kicked = 0
    async for user in client.iter_participants(chat):
        if user.id in admin_ids:
            continue
        try:
            await client.kick_participant(chat, user.id)
            kicked += 1
            await asyncio.sleep(1)
        except UserAdminInvalidError:
            continue
        except ChatAdminRequiredError:
            await event.reply("⚠️ I need 'Ban Members' permission to kick users.")
            return
        except Exception as e:
            print(f"Error kicking {user.id}: {e}")
            continue

    await event.reply(f"✅ Kicked {kicked} non-admin members.")

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

        await asyncio.sleep(86400)

if __name__ == "__main__":
    print("✅ Bot started and running...")
    client.loop.create_task(remove_inactive_users())
    client.run_until_disconnected()
    
