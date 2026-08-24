import asyncio
import random
import time
import os
import re
from typing import Set, List, Optional

from telethon import TelegramClient, events
from telethon.tl.types import Message, User
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import InputPhoto
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from typing import List

API_ID = 22152659
API_HASH = "7300603715676773c05db7fd7aab55fc"
PHONE_NUMBER = "+989053716748"

SESSION_NAME = "user_sadra"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOT_DIR = BASE_DIR
FOSH_FILE = os.path.join(BASE_DIR, "fosh.txt")
TARGET_ID_FILE = os.path.join(BOT_DIR, "targetid.txt")
FWD_SOURCE_CHANNEL_FILE = os.path.join(BOT_DIR, "fwd_source_channel.txt")
FWD_SOURCE_MSG_ID_FILE = os.path.join(BOT_DIR, "fwd_source_msg_id.txt")
FWD_DELAY_MIN_FILE = os.path.join(BOT_DIR, "fwd_delay_min.txt")
FWD_DELAY_MAX_FILE = os.path.join(BOT_DIR, "fwd_delay_max.txt")
FWD_EXTRA_TEXT_FILE = os.path.join(BOT_DIR, "fwd_extra_text.txt")
FWD_EXTRA_POSITION_FILE = os.path.join(BOT_DIR, "fwd_extra_position.txt")
HELP_IMAGE_URL = "https://raw.githubusercontent.com/sadraonthehack/VDIEO/main/doc_2026-07-19_19-43-39.mp4"

ADMIN_IDS: Set[int] = {7202211827}  
FOSHLIST: List[str] = []
SPAM_TARGET: Optional[int] = None
SPAM_TEXT: str = "ONLINE"
SPAM_ACTIVE: bool = False
SPAM_TASK: Optional[asyncio.Task] = None
FORWARD_SPAM_ACTIVE: bool = False
FORWARD_SPAM_TASK: Optional[asyncio.Task] = None
SPAM_SPEED: float = 1.0  
ON_OFF_ACTIVE: bool = False
ON_OFF_TASK: Optional[asyncio.Task] = None
ON_OFF_SEQUENCE: List[str] = ["چس", "مس", "کص","لش", "مست", "1", "2", "3", "4", "5", "6", "7", "8", "9", "00", "مدرک"]
ON_OFF_DELAY: float = 0
ENEMY_TARGET: Optional[int] = None
ENEMY_ACTIVE: bool = False
REPLY_TO_ENEMY: bool = True
ORIGINAL_NAME: str = ""
ORIGINAL_PHOTO: Optional[InputPhoto] = None

# New variables for tag spam
TAG_TARGETS: List[int] = []
TAG_SPAM_ACTIVE: bool = False
TAG_SPAM_TASK: Optional[asyncio.Task] = None
TAG_SPAM_DELAY: float = 5.0
TAG_SPAM_CHAT_ID: Optional[int] = None
TAG_SYMBOL: str = "🪽"  # default symbol for tag mentions (editable via setsymbol)

client: Optional[TelegramClient] = None


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def spam_loop():
    """Background task that sends spam messages with custom speed."""
    global SPAM_ACTIVE, SPAM_TARGET, SPAM_TEXT, SPAM_SPEED, client
    while SPAM_ACTIVE and SPAM_TARGET and client:
        try:
            await client.send_message(SPAM_TARGET, SPAM_TEXT)
            print(f"[SPAM] 📨 Sent to {SPAM_TARGET} | Speed: {SPAM_SPEED}s")
        except Exception as e:
            print(f"[ERROR] Spam failed: {e}")
        await asyncio.sleep(SPAM_SPEED)

async def on_off_loop(chat_id: int):
    global ON_OFF_ACTIVE, ON_OFF_SEQUENCE, ON_OFF_DELAY, client
    while ON_OFF_ACTIVE and client:
        for item in ON_OFF_SEQUENCE:
            if not ON_OFF_ACTIVE:
                break
            try:
                await client.send_message(chat_id, item)
            except Exception as e:
                print(f"[ERROR] on/off send failed: {e}")
            await asyncio.sleep(ON_OFF_DELAY)
        await asyncio.sleep(0)

async def tag_spam_loop(chat_id: int):
    """Background task that sends fosh messages with all tag mentions."""
    global TAG_SPAM_ACTIVE, TAG_TARGETS, TAG_SPAM_DELAY, FOSHLIST, TAG_SYMBOL, client
    while TAG_SPAM_ACTIVE and client and chat_id:
        if not FOSHLIST:
            print("[TAG SPAM] No fosh messages available.")
            await asyncio.sleep(5)
            continue
        if not TAG_TARGETS:
            print("[TAG SPAM] No targets set.")
            await asyncio.sleep(5)
            continue

        # Pick a random fosh message
        fosh_text = random.choice(FOSHLIST)

        # Build mention string for all targets using the current symbol
        mentions = "\n".join(
            f"<a href='tg://user?id={uid}'>{TAG_SYMBOL}</a>"
            for uid in TAG_TARGETS
        )

        # Combine message: fosh text + newline + mentions
        full_message = f"{fosh_text}\n\n{mentions}"

        try:
            await client.send_message(chat_id, full_message, parse_mode='html')
            print(f"[TAG SPAM] Sent with {len(TAG_TARGETS)} tag(s), delay {TAG_SPAM_DELAY}s")
        except Exception as e:
            print(f"[ERROR] Tag spam send failed: {e}")

        await asyncio.sleep(TAG_SPAM_DELAY)

async def send_loading_animation(event):
    """Send a loading animation with progress bar effect."""
    loading_steps = [
        " [          ] 0%",
        " [█         ] 10%",
        " [██        ] 20%",
        " [███       ] 30%",
        " [████      ] 40%",
        " [█████     ] 50%",
        " [██████    ] 60%",
        " [███████   ] 70%",
        " [████████  ] 80%",
        " [█████████ ] 90%",
        " [██████████] 100%",
        " LOADING COMPLETE"
    ]
    loading_msg = await event.reply(" **Loading...**\n" + loading_steps[0])
    for i in range(1, len(loading_steps)):
        await asyncio.sleep(0.3)
        try:
            await loading_msg.edit(f" **Loading...**\n{loading_steps[i]}")
        except:
            break
    await asyncio.sleep(0.3)
    try:
        await loading_msg.delete()
    except:
        pass


def save_fosh_file():
    try:
        with open(FOSH_FILE, "w", encoding="utf-8") as f:
            for item in FOSHLIST:
                f.write(item.strip() + "\n")
    except Exception as e:
        print(f"[ERROR] Could not save {FOSH_FILE}: {e}")


def normalize_join_target(raw: str) -> Optional[str]:
    if not raw:
        return None

    target = raw.strip()
    if not target:
        return None

    if target.startswith("@"):
        return target[1:]

    target = target.replace("https://", "").replace("http://", "")
    target = target.replace("t.me/", "", 1).replace("telegram.me/", "", 1)
    target = target.split("?", 1)[0].split("#", 1)[0].strip("/")

    if not target:
        return None

    if target.lower().startswith("joinchat/"):
        return target[len("joinchat/"):]

    if target.startswith("+"):
        return target

    if target.lower().startswith("joinchat"):
        return target[len("joinchat"):]

    if "/" in target:
        first_part = target.split("/", 1)[0]
        if first_part.lower() in {"joinchat", "addlist", "s"}:
            return target.split("/", 1)[1]
        return first_part

    return target


def looks_like_invite_hash(target: str) -> bool:
    if not target:
        return False
    return target.lower().startswith("joinchat") or target.startswith("+")


def ensure_forward_files():
    os.makedirs(BOT_DIR, exist_ok=True)
    files_defaults = {
        TARGET_ID_FILE: "1",
        FWD_SOURCE_CHANNEL_FILE: "",
        FWD_SOURCE_MSG_ID_FILE: "0",
        FWD_DELAY_MIN_FILE: "3",
        FWD_DELAY_MAX_FILE: "10",
        FWD_EXTRA_TEXT_FILE: "",
        FWD_EXTRA_POSITION_FILE: "after",
    }
    for path, value in files_defaults.items():
        if not os.path.exists(path):
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(value)
            except Exception as e:
                print(f"[ERROR] Could not create {path}: {e}")


def read_forward_file(path: str, default: str = "") -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip() or default
    except Exception:
        return default


async def check_owner(event) -> bool:
    if event.sender_id not in ADMIN_IDS:
        try:
            await event.reply("Access denied.")
        except Exception:
            pass
        return False
    return True


async def forward_spam_function():
    global FORWARD_SPAM_ACTIVE, client
    print("Forward spam thread started")
    ensure_forward_files()
    while FORWARD_SPAM_ACTIVE and client:
        try:
            target_id = SPAM_TARGET
            if not target_id:
                target_id = int(read_forward_file(TARGET_ID_FILE, "1") or "1")

            source_channel = read_forward_file(FWD_SOURCE_CHANNEL_FILE)
            source_msg_id = int(read_forward_file(FWD_SOURCE_MSG_ID_FILE, "0"))
            delay_min = float(read_forward_file(FWD_DELAY_MIN_FILE, "3"))
            delay_max = float(read_forward_file(FWD_DELAY_MAX_FILE, "10"))
            extra_text = read_forward_file(FWD_EXTRA_TEXT_FILE)
            extra_pos = read_forward_file(FWD_EXTRA_POSITION_FILE, "after").lower()
        except Exception as e:
            print(f"Config read error: {e}")
            await asyncio.sleep(5)
            continue

        if not target_id or target_id == 1:
            print(" No target set. Use setid <chatid> first.")
            FORWARD_SPAM_ACTIVE = False
            break

        if not source_channel or source_msg_id == 0:
            print(" No source set. Use setfwd <message_link>")
            FORWARD_SPAM_ACTIVE = False
            break

        try:
            source_message = await client.get_messages(source_channel, ids=source_msg_id)
            if not source_message:
                print(f"❌ Message {source_msg_id} not found in {source_channel}")
                FORWARD_SPAM_ACTIVE = False
                break

            await client.forward_messages(target_id, source_message)

            if extra_text:
                if extra_pos == "before":
                    await client.send_message(target_id, f"{extra_text}\n\n")
                else:
                    await client.send_message(target_id, f"\n\n{extra_text}")

            print(f" Forwarded to {target_id}")
            delay = random.uniform(delay_min, delay_max)
            await asyncio.sleep(delay)

        except FloodWaitError as e:
            print(f" Flood wait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Forward error: {e}")
            await asyncio.sleep(5)


async def handle_all_messages(event):
    global ADMIN_IDS, FOSHLIST, SPAM_TARGET, SPAM_TEXT, SPAM_ACTIVE, SPAM_TASK, SPAM_SPEED
    global ON_OFF_ACTIVE, ON_OFF_TASK, ENEMY_TARGET, ENEMY_ACTIVE, REPLY_TO_ENEMY, ORIGINAL_NAME, ORIGINAL_PHOTO, FORWARD_SPAM_ACTIVE, FORWARD_SPAM_TASK, client
    global TAG_TARGETS, TAG_SPAM_ACTIVE, TAG_SPAM_TASK, TAG_SPAM_DELAY, TAG_SPAM_CHAT_ID, TAG_SYMBOL
    
    user_id = event.sender_id
    
    if ENEMY_ACTIVE and REPLY_TO_ENEMY and FOSHLIST:
        if user_id == ENEMY_TARGET:
            reply_text = random.choice(FOSHLIST)
            await asyncio.sleep(0.5)
            try:
                await event.reply(reply_text)
                print(f"[BOT]  Enemy reply sent to {user_id}")
            except Exception as e:
                print(f"[ERROR] Enemy reply failed: {e}")
            return
    
    if not event.message or not event.message.text:
        return
    
    raw_text = event.message.text.strip() if event.message.text else ""
    text = raw_text.lower()

    if event.is_reply and raw_text:
    # بررسی کن که کاربر ادمین هست یا نه
        if user_id in ADMIN_IDS:
            if not text.startswith((
            "help", "راهنما", "help2", "on", "off", "spam", "spamoff", "setfosh ",
            "speed ", "id", "setid ", "setfwd ", "setfwd_delay ", "setfwd_text ",
            "setfwd_pos ", "fspam_on", "fspam_off", "showfwd", "join ",
            "addfosh", "listfosh", "removefosh ", "setenemy", "enemyoff", "setreply ",
            "clone ", "cloneback", "ping", "status", "sudo su", "kiladmin",
            ".settag ", "time ", "start", "stop", "setsymbol "
        )):
             trailing_match = re.match(r"^(.*?)(?:\s+)?(\d+)\s*$", raw_text)
            if trailing_match:
                message_text = trailing_match.group(1).strip()
                count = int(trailing_match.group(2))
                if message_text and count > 0:
                    reply_to_id = event.message.reply_to_msg_id or event.message.id
                    try:
                        for _ in range(count):
                            await client.send_message(event.chat_id, message_text, reply_to=reply_to_id)
                            await asyncio.sleep(0.1)
                    except Exception as e:
                        print(f"[ERROR] Repeat reply failed: {e}")
                    return
    # اگر ادمین نباشه، هیچ کاری انجام نمیشه و بیصدا نادیده گرفته میشه
    
    me = await client.get_me()

    if user_id not in ADMIN_IDS:
        print(f"[BOT] Ignored non-admin message from {user_id}")
        return
    
    

    
    
    if event.is_private:
        location = "PRIVATE"
    elif event.is_group:
        location = "GROUP"
    elif event.is_channel:
        location = "CHANNEL"
    else:
        location = "UNKNOWN"
    
    print(f"[BOT]  Admin {user_id} in {location}: {text[:50]}")
    
    
    if text == "help" or text == "راهنما":
        await send_loading_animation(event)
        help_text = """
```> • `spam` – Start spam
> • `spamoff` – Stop spam
> • `setfosh <text>` – Change spam text
> • `speed <1-60>` – Set speed
> • `id` – Get chat ID
> • `setid <chat_id>` – Set target
> • `join <link>` – Join link
> • `ping` – Check bot ping
> • `status` – Show status
> • `help2`
> •Development by @DevilWillCryBitch ````
"""
        try:
            await client.send_file(
                event.chat_id,
                HELP_IMAGE_URL,
                caption=help_text,
                reply_to=event.message.id,
            )
        except Exception as e:
            print(f"[ERROR] Help media send failed: {e}")
            try:
                await client.send_message(event.chat_id, help_text, reply_to=event.message.id)
            except Exception as fallback_error:
                print(f"[ERROR] Help text fallback failed: {fallback_error}")
        return

    if text == "help2":
        await send_loading_animation(event)
        help_text = """
```• sudo su  – user id  add admin 
• kiladmin – user id remove admin
• clone @user – Clone profile
• cloneback – Restore original profile
• on/off – number fight 
• setenemy – mark use as enemy
• enemyoff – remove user form enemy list
• listfosh – show the fosh list
• addfosh – add fosh 
• yourword – you can use your word for ech time you want it spam like it im here 10 
• removefosh – remove fosh
• bitch – user id to set tag them 
• setuser – anything u want to put target username 
> •Development by @DevilWillCryBitch ````
"""
        try:
            await client.send_file(
                event.chat_id,
                HELP_IMAGE_URL,
                caption=help_text,
                reply_to=event.message.id,
            )
        except Exception as e:
            print(f"[ERROR] Help2 media send failed: {e}")
            try:
                await client.send_message(event.chat_id, help_text, reply_to=event.message.id)
            except Exception as fallback_error:
                print(f"[ERROR] Help2 text fallback failed: {fallback_error}")
        return

    # `help3` removed per user request
    
    
    if text == "on":
        if not ON_OFF_ACTIVE:
            ON_OFF_ACTIVE = True
            if ON_OFF_TASK and not ON_OFF_TASK.done():
                ON_OFF_TASK.cancel()
            ON_OFF_TASK = asyncio.create_task(on_off_loop(event.chat_id))
        return

    if text == "off":
        if ON_OFF_ACTIVE:
            ON_OFF_ACTIVE = False
            if ON_OFF_TASK and not ON_OFF_TASK.done():
                ON_OFF_TASK.cancel()
        return

    if text.startswith("speed "):
        try:
            new_speed = float(text[6:].strip())
            if 1 <= new_speed <= 60:
                SPAM_SPEED = new_speed
                print(f"[BOT]  Spam speed changed to {SPAM_SPEED}s (silent)")
        except ValueError:
            pass
        return  
    
    
    if text == "spam":

        if not SPAM_TARGET:
            await event.reply(" No target chat set. Use `setid` first.")
            return
        if SPAM_ACTIVE:
            await event.reply(" Spam is already running. Use `spamoff` to stop.")
            return
        
        SPAM_ACTIVE = True
        await event.reply(
            f"spam run!**\n"
            f"Target: `{SPAM_TARGET}`\n"
            f"Text: `{SPAM_TEXT}`\n"
            f"Speed: `{SPAM_SPEED} seconds`\n"
        )
        
        if SPAM_TASK and not SPAM_TASK.done():
            SPAM_TASK.cancel()
        SPAM_TASK = asyncio.create_task(spam_loop())
        return
    
    if text == "spamoff":
        if SPAM_ACTIVE:
            SPAM_ACTIVE = False
            if SPAM_TASK and not SPAM_TASK.done():
                SPAM_TASK.cancel()
            await event.reply("SPAM STOP ")
        else:
            await event.reply("NOT ACTIVE")
        return
    
    if text.startswith("setfosh "):
        SPAM_TEXT = text[8:].strip()
        await event.reply(f" new txt :\n`{SPAM_TEXT}`")
        return
    
    if text == "id":
        chat_id = event.chat_id
        chat_type = "Private" if event.is_private else "Group" if event.is_group else "Channel"
        await event.reply(f" ID `{chat_id}`\n **Type:** {chat_type}")
        return
    
    if text.startswith("setid "):
        try:
            SPAM_TARGET = int(text[6:].strip())
            await event.reply(f"TG SET `{SPAM_TARGET}`")
            try:
                with open(TARGET_ID_FILE, "w", encoding="utf-8") as f:
                    f.write(str(SPAM_TARGET))
            except Exception as e:
                print(f"[ERROR] Could not save target ID file: {e}")
        except ValueError:
            await event.reply(" WRONG CHATID ")
        return

    if text.startswith("setfwd "):
        link = text[7:].strip()
        if not link:
            await event.reply("Usage: `setfwd <message_link>`")
            return
        try:
            cleaned = link.replace("https://", "").replace("http://", "").replace("t.me/", "").replace("telegram.me/", "")
            parts = cleaned.split("/")
            if len(parts) >= 3 and parts[0].lower() == "c":
                channel = str(int("-100" + parts[1]))
                msg_id = int(parts[2])
            elif len(parts) >= 2:
                channel = parts[0]
                msg_id = int(parts[1])
            else:
                await event.reply(" Invalid setfwd link. Use a t.me link with message ID.")
                return
            with open(FWD_SOURCE_CHANNEL_FILE, "w", encoding="utf-8") as f:
                f.write(channel)
            with open(FWD_SOURCE_MSG_ID_FILE, "w", encoding="utf-8") as f:
                f.write(str(msg_id))
            await event.reply(f" Source set!\nChannel: `{channel}`\nMessage ID: `{msg_id}`")
        except Exception as e:
            await event.reply(f" Failed to parse link: {e}")
        return

    if text.startswith("setfwd_delay "):
        try:
            parts = text.split()
            min_d = float(parts[1])
            max_d = float(parts[2]) if len(parts) > 2 else min_d + 1
            if min_d < 0.5:
                min_d = 0.5
            if max_d < min_d:
                max_d = min_d + 1
            with open(FWD_DELAY_MIN_FILE, "w", encoding="utf-8") as f:
                f.write(str(min_d))
            with open(FWD_DELAY_MAX_FILE, "w", encoding="utf-8") as f:
                f.write(str(max_d))
            await event.reply(f" Delay: {min_d}-{max_d} seconds")
        except Exception:
            await event.reply(" Usage: `setfwd_delay <min> <max>`")
        return

    if text.startswith("setfwd_text "):
        extra_text = text[12:].strip()
        with open(FWD_EXTRA_TEXT_FILE, "w", encoding="utf-8") as f:
            f.write(extra_text)
        await event.reply(" Extra text set")
        return

    if text.startswith("setfwd_pos "):
        pos = text[11:].strip().lower()
        if pos not in ["before", "after"]:
            await event.reply(" Usage: `setfwd_pos before` or `setfwd_pos after`")
            return
        with open(FWD_EXTRA_POSITION_FILE, "w", encoding="utf-8") as f:
            f.write(pos)
        await event.reply(f" Position: {pos}")
        return

    if text == "fspam_on":
        if FORWARD_SPAM_ACTIVE:
            await event.reply(" Forward spam is already running.")
            return
        FORWARD_SPAM_ACTIVE = True
        if FORWARD_SPAM_TASK and not FORWARD_SPAM_TASK.done():
            FORWARD_SPAM_TASK.cancel()
        FORWARD_SPAM_TASK = asyncio.create_task(forward_spam_function())
        await event.reply(" **FWD SPAM RUNNING**")
        return

    if text == "fspam_off":
        if FORWARD_SPAM_ACTIVE:
            FORWARD_SPAM_ACTIVE = False
            if FORWARD_SPAM_TASK and not FORWARD_SPAM_TASK.done():
                FORWARD_SPAM_TASK.cancel()
            await event.reply(" **FWD SPAM STOPPED**")
        else:
            await event.reply(" Forward spam is not running.")
        return

    if text == "showfwd":
        source = read_forward_file(FWD_SOURCE_CHANNEL_FILE)
        msg_id = read_forward_file(FWD_SOURCE_MSG_ID_FILE, "0")
        min_delay = read_forward_file(FWD_DELAY_MIN_FILE, "3")
        max_delay = read_forward_file(FWD_DELAY_MAX_FILE, "10")
        target = SPAM_TARGET or int(read_forward_file(TARGET_ID_FILE, "1") or "1")
        status = "RUNNING" if FORWARD_SPAM_ACTIVE else "STOPPED"
        await event.reply(f"**Forward Config - {status}**\n• TARGET: `{target}`\n• SOURCE: `{source}/{msg_id}`\n• DELAY: `{min_delay}-{max_delay}` seconds")
        return

    if text.startswith("join "):
        invite_input = raw_text[5:].strip()
        if not invite_input:
            await event.reply(" Usage: `join <invite_link>` or `join @channelname`")
            return

        invite_input = invite_input.strip()
        target = normalize_join_target(invite_input)
        if not target:
            await event.reply(" Invalid invite link. Use a real Telegram invite link or public channel username.")
            return

        try:
            if not looks_like_invite_hash(target):
                try:
                    entity = await client.get_entity(target if not target.startswith("@") else target[1:])
                    try:
                        await client(JoinChannelRequest(entity))
                    except UserAlreadyParticipantError:
                        await event.reply(f" Already joined: `{invite_input}`")
                        return
                    except Exception as e:
                        error_text = str(e).lower()
                        if "already participant" in error_text or "already joined" in error_text:
                            await event.reply(f" Already joined: `{invite_input}`")
                            return
                        raise
                    await event.reply(f" Joined successfully: `{invite_input}`")
                    return
                except Exception:
                    pass

            invite_candidates = [target]
            if target.startswith("+"):
                invite_candidates.append(target[1:])
            if target.lower().startswith("joinchat"):
                invite_candidates.append(target[len("joinchat"):])
            if target.lower().startswith("joinchat/"):
                invite_candidates.append(target[len("joinchat/"):])
            invite_candidates = list(dict.fromkeys(invite_candidates))

            joined = False
            for candidate in invite_candidates:
                try:
                    await client(JoinChannelRequest(candidate))
                    await event.reply(f" Joined successfully: `{invite_input}`")
                    joined = True
                    break
                except UserAlreadyParticipantError:
                    await event.reply(f" Already joined: `{invite_input}`")
                    joined = True
                    break
                except Exception:
                    continue

            if not joined:
                await event.reply(f" Could not join: `{invite_input}`")
        except Exception as e:
            await event.reply(f" Failed to join: {e}")
        return

    if text == "addfosh":
        if not event.is_reply:
            await event.reply(" Reply fosh and after type addfosh")
            return

        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.text:
            await event.reply(" The replied message has no text.")
            return

        FOSHLIST.append(replied_msg.text)
        save_fosh_file()
        await event.reply(
            f"fosh added** (Index #{len(FOSHLIST)-1})\n"
            f"Preview: `{replied_msg.text[:50]}...`"
        )
        return

    await _commands_handler(event, text, client)

# خواندن از فایل
try:
    with open(FOSH_FILE, "r", encoding="utf-8") as f:
        FOSHLIST: List[str] = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    # اگر فایل وجود نداشت، لیست پیش‌فرض
    FOSHLIST: List[str] = [
        "بیا پایین 🗿",
        "کصخل 🐒",
        "برو گمشو 👋"
    ]
    print("fosh.txt not found. Using default fosh list.")


async def _commands_handler(event, text, client):
    global ADMIN_IDS, FOSHLIST, ENEMY_TARGET, ENEMY_ACTIVE, REPLY_TO_ENEMY, ORIGINAL_NAME, ORIGINAL_PHOTO
    global TAG_TARGETS, TAG_SPAM_ACTIVE, TAG_SPAM_TASK, TAG_SPAM_DELAY, TAG_SPAM_CHAT_ID, TAG_SYMBOL
    user_id = event.sender_id

    if text == "listfosh":
        if not FOSHLIST:
            await event.reply(" Foshlist is empty. Use `addfosh` to fill it.")
            return
        lines = []
        for i, item in enumerate(FOSHLIST):
            snippet = item.replace("\n", " ")[:60]
            lines.append(f"`{i}`: {snippet}...")
        msg = " **FOSHLIST** (index to use with `removefosh`):\n" + "\n".join(lines[:20])
        if len(lines) > 20:
            msg += f"\n... and {len(lines)-20} more."
        await event.reply(msg)
        return

    if text.startswith("removefosh "):
        try:
            idx = int(text[11:].strip())
            if idx < 0 or idx >= len(FOSHLIST):
                await event.reply(" Index out of range.")
                return
            removed = FOSHLIST.pop(idx)
            save_fosh_file()
            await event.reply(
                f" Removed fosh {idx}:\n`{removed[:50]}...`"
            )
        except ValueError:
            await event.reply(" Invalid index. Must be a number.")
        return


    if text == "setenemy":
        if not event.is_reply:
            await event.reply("reply dojman ")
            return

        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.sender_id:
            await event.reply(" Could not identify the user")
            return

        target_user = await client.get_entity(replied_msg.sender_id)
        ENEMY_TARGET = target_user.id
        ENEMY_ACTIVE = True
        await event.reply(
            f" **mother fuck:** @{target_user.username or target_user.first_name or 'Unknown'}\n"
            f"ID: `{ENEMY_TARGET}`\n"
        )
        return

    if text == "enemyoff":
        if ENEMY_ACTIVE:
            ENEMY_ACTIVE = False
            await event.reply(" enemey mod off")
        else:
            await event.reply("ℹ Enemy mode is already off.")
        return

    if text.startswith("setreply "):
        mode = text[9:].strip().lower()
        if mode not in ["on", "off"]:
            await event.reply(" Usage: `setreply on` or `setreply off`")
            return
        REPLY_TO_ENEMY = mode == "on"
        await event.reply(f" Auto-reply set to: {REPLY_TO_ENEMY}")
        return
    
    if text.startswith("copy "):
        target_identifier = text[6:].strip()
        if target_identifier.startswith("@"):
            target_identifier = target_identifier[1:]
        
        await event.reply(f"`{target_identifier}`...")
        
        try:
            try:
                target_user = await client.get_entity(target_identifier)
            except:
                if target_identifier.isdigit():
                    try:
                        target_user = await client.get_entity(int(target_identifier))
                    except:
                        target_user = None
                else:
                    target_user = None
            
            if not target_user and event.is_reply:
                replied_msg = await event.get_reply_message()
                if replied_msg and replied_msg.sender_id:
                    target_user = await client.get_entity(replied_msg.sender_id)
            
            if not target_user:
                await event.reply(" Could not find user")
                return
            
            me = await client.get_me()
            if not ORIGINAL_NAME:
                ORIGINAL_NAME = me.first_name or ""
            
            if not ORIGINAL_PHOTO:
                try:
                    photos = await client.get_profile_photos(me, limit=1)
                    if photos:
                        ORIGINAL_PHOTO = photos[0]
                except:
                    pass
            
            await event.reply(f" `{target_user.first_name or ''}`...")
            
            try:
                photos = await client.get_profile_photos(target_user, limit=1)
                
                if photos:
                    photo = photos[0]
                    photo_path = await client.download_media(photo, file="temp_profile.jpg")
                    
                    if photo_path:
                        await client(UploadProfilePhotoRequest(
                            file=await client.upload_file(photo_path)
                        ))
                        await event.reply(" **set pfp**")
                        try:
                            os.remove(photo_path)
                        except:
                            pass
                else:
                    await event.reply("")
            except Exception as e:
                await event.reply(f" `{str(e)[:100]}`")
            
            new_first_name = target_user.first_name or ""
            new_last_name = target_user.last_name or ""
            
            try:
                await client(UpdateProfileRequest(
                    first_name=new_first_name,
                    last_name=new_last_name
                ))
                
                await event.reply(
                    f" ****\n"
                    f" `{new_first_name} {new_last_name}`".strip()
                )
            except Exception as e:
                await event.reply(f" Failed to set name `{str(e)[:100]}`")
            
            await event.reply(
                f"\n"
                f"`{target_user.first_name or ''}`\n"
                f"ID: `{target_user.id}`"
            )
            
        except Exception as e:
            await event.reply(f" copy faild`{str(e)[:200]}`")
        return
    
    if text == "back":
        try:
            photos = await client.get_profile_photos(await client.get_me(), limit=1)
            if photos:
                await client(DeletePhotosRequest(id=[photos[0]]))
            
            if ORIGINAL_PHOTO:
                try:
                    photo_path = await client.download_media(ORIGINAL_PHOTO, file="orig_profile.jpg")
                    if photo_path:
                        await client(UploadProfilePhotoRequest(
                            file=await client.upload_file(photo_path)
                        ))
                        try:
                            os.remove(photo_path)
                        except:
                            pass
                except:
                    pass
            
            if ORIGINAL_NAME:
                await client(UpdateProfileRequest(
                    first_name=ORIGINAL_NAME,
                    last_name=""
                ))
            
            await event.reply(" ok")
        except Exception as e:
            await event.reply(f" Failed to restore: `{str(e)[:100]}`")
        return

    # ====================== NEW .settag COMMAND ======================
    if text.startswith("bitch"):
        try:
            # Extract IDs from the command
            parts = text.split()
            if len(parts) < 2:
                await event.reply(" provide at least one User ID.\nUsage: `bitch user id `")
                return
            
            # Parse IDs and handle errors
            user_ids = []
            invalid_ids = []
            
            for part in parts[1:]:
                try:
                    user_id = int(part.strip())
                    user_ids.append(user_id)
                except ValueError:
                    invalid_ids.append(part)
            
            if invalid_ids:
                await event.reply(f"Invalid user IDs: {', '.join(invalid_ids)}\n")
                return
            
            if not user_ids:
                await event.reply("No valid User IDs provided")
                return
            
            # Store the targets
            TAG_TARGETS = user_ids
            await event.reply(f"  {len(TAG_TARGETS)} \nIDs: `{'`, `'.join(map(str, TAG_TARGETS))}`")
            
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
        return
    # ====================== END .settag ======================

    # ====================== TIME COMMAND ======================
    if text.startswith("time "):
        try:
            delay = float(text[5:].strip())
            if 1 <= delay <= 60:
                TAG_SPAM_DELAY = delay
                await event.reply(f" `{TAG_SPAM_DELAY}` seconds")
            else:
                await event.reply("only 1-60 seconds")
        except ValueError:
            await event.reply("")
        return
    # ====================== END TIME ======================

    # ====================== START COMMAND ======================
    if text == "start":
        if TAG_SPAM_ACTIVE:
            await event.reply(" spam is already running.")
            return
        if not FOSHLIST:
            await event.reply(" `addfosh`")
            return
        if not TAG_TARGETS:
            await event.reply(" set bitchs fisrt")
            return
        
        # Store the current chat ID and start the task
        TAG_SPAM_CHAT_ID = event.chat_id
        TAG_SPAM_ACTIVE = True
        if TAG_SPAM_TASK and not TAG_SPAM_TASK.done():
            TAG_SPAM_TASK.cancel()
        TAG_SPAM_TASK = asyncio.create_task(tag_spam_loop(TAG_SPAM_CHAT_ID))
        await event.reply(
            f" **spam**\n"
            f"  {len(TAG_TARGETS)} user(s)\n"
            f" {TAG_SPAM_DELAY}s\n"
            f"{len(FOSHLIST)}\n"
            f"Symbol `{TAG_SYMBOL}`"
        )
        return
    # ====================== END START ======================

    # ====================== STOP COMMAND ======================
    if text == "stop":
        if not TAG_SPAM_ACTIVE:
            await event.reply("ℹspam not run")
            return
        TAG_SPAM_ACTIVE = False
        if TAG_SPAM_TASK and not TAG_SPAM_TASK.done():
            TAG_SPAM_TASK.cancel()
        await event.reply("spam off")
        return
    # ====================== END STOP ======================

    # ====================== SETSYMBOL COMMAND ======================
    if text.startswith("set"):
        symbol = text[10:].strip()  # everything after "setsymbol "
        if not symbol:
            await event.reply("\n")
            return
        TAG_SYMBOL = symbol
        await event.reply(f"target user `{TAG_SYMBOL}`")
        return
    # ====================== END SETSYMBOL ======================

    if text == "bot":
        start = time.perf_counter()
        await event.reply("O N L I N E")  
        
    
    if text == "status":
        status_msg = f"""
 **BOT STATUS**

 **Admins:** {len(ADMIN_IDS)} users
 **Spam target:** `{SPAM_TARGET or 'Not set'}`
 **Spam text:** `{SPAM_TEXT[:50]}...`
 **Spam speed:** `{SPAM_SPEED} seconds`
**Spam active:** {SPAM_ACTIVE}
 **Enemy target:** `{ENEMY_TARGET or 'None'}`
 **Enemy active:** {ENEMY_ACTIVE}

"""
        await event.reply(status_msg)
        return
    
    if text.startswith("sudo su"):
        try:
            parts = text.split()
            if len(parts) < 3:  # چون "sudo su" دو کلمه هست
                await event.reply(" user id only")
                return
            try:
                new_admin = int(parts[2].strip())  # قسمت سوم رو میگیره
            except ValueError:
                await event.reply(" Invalid user ID. Must be a number")
                return

            if new_admin == user_id:
                await event.reply(" you have already root permission")
                return
            if new_admin in ADMIN_IDS:
                await event.reply(" User is already an admin")
                return
            ADMIN_IDS.add(new_admin)
            await event.reply(f" User `{new_admin}` is now have root permission")
            print(f"[BOT]  New admin added: {new_admin}")
            print(f"[BOT]  Current admins: {ADMIN_IDS}")

           
        except Exception as e:
            await event.reply(f" Failed to add admin: `{str(e)[:100]}`")
            return

    if text.startswith("kiladmin"):
        try:
            parts = text.split(maxsplit=1)  
            if len(parts) < 2:
                await event.reply("  provide a user ID.")
                return
            rem_admin = int(parts[1].strip())
            
            if rem_admin not in ADMIN_IDS:
                await event.reply(" user dont have root permission")
                return
            if len(ADMIN_IDS) <= 1:
                await event.reply(" the last root user cant be deleted.")
                return
            ADMIN_IDS.remove(rem_admin)
            await event.reply(f" User `{rem_admin}` dont have root permission any more")
            print(f"[BOT]  Admin killed: {rem_admin}")
            print(f"[BOT]  Current admins: {ADMIN_IDS}")
        except (ValueError, IndexError):
            await event.reply(" Invalid user ID.")
        return


async def main():
    global client
    
    print("=" * 60)
    print("[BOT] 🚀 Starting Rebel Bot...")
    print(f"[BOT] 👑 Admins: {ADMIN_IDS}")
    print("[BOT] 🔇 Non-admins: COMPLETE SILENCE")
    print("[BOT] 🎯 Enemy auto-reply: ACTIVE (private only)")
    print("[BOT] 📝 NO SLASH MODE: Just type commands")
    print("[BOT] 📍 RESPONSE MODE: EVERYWHERE (Private, Groups, Channels)")
    print(f"[BOT] ⏱️ Default spam speed: {SPAM_SPEED}s")
    print("=" * 60)
    
    ensure_forward_files()
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)
    
    me = await client.get_me()
    ADMIN_IDS.add(me.id)
    print(f"[BOT] 👑 Admins: {ADMIN_IDS}")
    
    client.add_event_handler(handle_all_messages, events.NewMessage(incoming=True))
    client.add_event_handler(handle_all_messages, events.NewMessage(outgoing=True))

    
    print(f"[BOT] ✅ Logged in as: {me.first_name} (@{me.username})")
    print(f"[BOT] 🆔 User ID: {me.id}")
    print("[BOT] ✅ READY!")
    print("=" * 60)
    
    try:
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("[BOT] Shutting down...")
        await client.disconnect()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[ERROR] Bot crashed: {e}")
        input("Press Enter to exit...")
