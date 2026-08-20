import asyncio
import random
import time
import os
import aiohttp
import json
import re
from typing import Set, List, Optional, Dict
from datetime import datetime, timedelta

from telethon import TelegramClient, events
from telethon.tl.types import Message, User
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import InputPhoto
from telethon.errors import FloodWaitError
from typing import List

# API Credentials
API_ID = 27029926
API_HASH = "6963d3bf5f8a776f5139d71cfc707abc"

# User Account Session (instead of bot tokens)
SESSION_NAME = "user_sadra"

MASTER_BOT_INDEX = 0

# AI Configuration
AI_API_KEY = "sk-nry-imZYqEQPGtSBwSHdkO_ihY2pU0LrD5brPmIrM6isWs4"
AI_API_URL = "https://router.bynara.id/v1/chat/completions"
AI_MODEL = "agnes-2.0-flash"
AI_MODE_ACTIVE = False

# AI Context Memory
AI_CONTEXT: Dict[int, List[Dict[str, str]]] = {}
MAX_CONTEXT_MESSAGES = 30

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

# AI Spam variables
AI_SPAM_ACTIVE: bool = False
AI_SPAM_TASK: Optional[asyncio.Task] = None
AI_SPAM_TARGET: Optional[int] = None
AI_SPAM_TEXT: str = ""
AI_SPAM_DELAY: float = 60
AI_SPAM_END_TIME: Optional[datetime] = None
AI_SPAM_MESSAGES_SENT: int = 0
AI_SPAM_TOTAL_DAYS: int = 1
AI_SPAM_BOT_COUNT: int = None

# SPAMTAG VARIABLES
SPAMTAG_ACTIVE: bool = False
SPAMTAG_TASK: Optional[asyncio.Task] = None
SPAMTAG_TARGET: Optional[int] = None
SPAMTAG_TAG: str = ""
SPAMTAG_DELAY: float = 1.0
SPAMTAG_BOT_COUNT: int = None
SPAMTAG_MESSAGES_SENT: int = 0

clients: List[TelegramClient] = []
MASTER_CLIENT: Optional[TelegramClient] = None
ALL_BOTS_RUNNING: bool = False
FORWARD_SPAM_ACTIVE = False
FORWARD_SPAM_TASK = None

# Per-bot spam states (now for user account)
bot_spam_states: Dict[int, Dict] = {}

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def parse_duration(text: str) -> int:
    text = text.lower().strip()
    
    if 'day' in text:
        parts = text.split()
        for part in parts:
            if part.isdigit():
                return int(part)
        return 1
    
    if 'hour' in text:
        parts = text.split()
        for part in parts:
            if part.isdigit():
                return int(part) / 24
        return 1/24
    
    if 'min' in text:
        parts = text.split()
        for part in parts:
            if part.isdigit():
                return int(part) / 1440
        return 1/1440
    
    return 1

def parse_delay(text: str) -> float:
    """Parse delay - supports sec, min, hour - from 1 second to 60 minutes"""
    text = text.lower().strip()
    
    numbers = re.findall(r'\d+', text)
    if not numbers:
        return 60
    
    value = int(numbers[0])
    
    if 'sec' in text:
        if value < 1:
            value = 1
        return float(value)
    elif 'min' in text:
        if value < 1:
            value = 1
        if value > 60:
            value = 60
        return float(value * 60)
    elif 'hour' in text or 'hr' in text:
        if value < 1:
            value = 1
        return float(value * 3600)
    else:
        if value < 1:
            value = 1
        if value > 3600:
            value = 3600
        return float(value)

def extract_text_in_parentheses(text: str) -> str:
    start = text.find('(')
    end = text.rfind(')')
    if start != -1 and end != -1 and start < end:
        return text[start+1:end]
    return None

def extract_number(text: str) -> int:
    parts = text.split()
    for part in parts:
        if part.isdigit():
            return int(part)
    return None

def format_delay(seconds: float) -> str:
    """Convert seconds to human readable format"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{int(minutes)} minutes"
    else:
        hours = seconds / 3600
        return f"{int(hours)} hours"

async def get_ai_response(user_id: int, prompt: str, replied_text: str = None) -> str:
    global AI_CONTEXT
    
    try:
        if user_id not in AI_CONTEXT:
            AI_CONTEXT[user_id] = []
        
        full_prompt = prompt
        if replied_text:
            full_prompt = f"[Reply to: {replied_text}]\n{prompt}"
        
        AI_CONTEXT[user_id].append({"role": "user", "content": full_prompt})
        
        if len(AI_CONTEXT[user_id]) > MAX_CONTEXT_MESSAGES:
            AI_CONTEXT[user_id] = AI_CONTEXT[user_id][-MAX_CONTEXT_MESSAGES:]
        
        messages = AI_CONTEXT[user_id].copy()
        
        headers = {
            "Authorization": f"Bearer {AI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": AI_MODEL,
            "messages": messages
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(AI_API_URL, headers=headers, json=data, timeout=30) as response:
                if response.status == 200:
                    result = await response.json()
                    ai_response = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    
                    AI_CONTEXT[user_id].append({"role": "assistant", "content": ai_response})
                    
                    if len(AI_CONTEXT[user_id]) > MAX_CONTEXT_MESSAGES:
                        AI_CONTEXT[user_id] = AI_CONTEXT[user_id][-MAX_CONTEXT_MESSAGES:]
                    
                    return ai_response
                elif response.status == 403:
                    print("[AI] Error 403: Telegram account not bound to Nararouter API")
                    return "ERROR: Please bind your Telegram account at https://router.bynara.id/settings"
                elif response.status == 404:
                    print("[AI] Error 404: Model not found")
                    return "ERROR: Model not available. Please check available models"
                else:
                    error_text = await response.text()
                    print(f"[AI] Error: {response.status} - {error_text}")
                    return None
    except asyncio.TimeoutError:
        print("[AI] Request timeout")
        return None
    except aiohttp.ClientConnectorError as e:
        print(f"[AI] Connection error: {e}")
        return None
    except Exception as e:
        print(f"[AI] Error: {e}")
        return None

async def clear_ai_context(user_id: int):
    global AI_CONTEXT
    if user_id in AI_CONTEXT:
        AI_CONTEXT[user_id] = []
        return True
    return False

async def ai_spam_loop():
    global AI_SPAM_ACTIVE, AI_SPAM_TARGET, AI_SPAM_TEXT, AI_SPAM_DELAY, AI_SPAM_END_TIME, AI_SPAM_MESSAGES_SENT, AI_SPAM_BOT_COUNT
    
    # Use only the user account (not multiple bots)
    if not clients:
        print("[AI SPAM] No client available!")
        return
    
    bot_count = 1  # Only one user account
    
    print(f"[AI SPAM] Started! Target: {AI_SPAM_TARGET}")
    print(f"[AI SPAM] Delay: {AI_SPAM_DELAY}s ({format_delay(AI_SPAM_DELAY)})")
    print(f"[AI SPAM] End: {AI_SPAM_END_TIME}")
    print(f"[AI SPAM] Text: {AI_SPAM_TEXT}")
    print(f"[AI SPAM] Using User Account")
    
    while AI_SPAM_ACTIVE and AI_SPAM_TARGET:
        if AI_SPAM_END_TIME and datetime.now() >= AI_SPAM_END_TIME:
            print(f"[AI SPAM] Duration completed! Stopping.")
            AI_SPAM_ACTIVE = False
            break
        
        try:
            await clients[0].send_message(AI_SPAM_TARGET, AI_SPAM_TEXT)
            AI_SPAM_MESSAGES_SENT += 1
            print(f"[AI SPAM] Sent ({AI_SPAM_MESSAGES_SENT})")
            
            await asyncio.sleep(AI_SPAM_DELAY)
            
        except FloodWaitError as e:
            print(f"[AI SPAM] Flood wait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[AI SPAM] Error: {e}")
            await asyncio.sleep(5)
    
    print(f"[AI SPAM] Stopped! Total: {AI_SPAM_MESSAGES_SENT}")

# SPAMTAG FUNCTION
async def spamtag_loop():
    global SPAMTAG_ACTIVE, SPAMTAG_TARGET, SPAMTAG_TAG, SPAMTAG_DELAY, SPAMTAG_BOT_COUNT, SPAMTAG_MESSAGES_SENT
    
    # Use only the user account
    if not clients:
        print("[SPAMTAG] No client available!")
        return
    
    # Load fosh list from file
    try:
        with open(FOSH_FILE, "r", encoding="utf-8") as f:
            fosh_list = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        fosh_list = ["بیا پایین", "کصخل", "برو گمشو"]
        print("[SPAMTAG] fosh.txt not found! Using default list.")
    
    if not fosh_list:
        print("[SPAMTAG] Fosh list is empty!")
        return
    
    SPAMTAG_MESSAGES_SENT = 0
    
    print(f"[SPAMTAG] Started! Target: {SPAMTAG_TARGET}")
    print(f"[SPAMTAG] Tag: {SPAMTAG_TAG}")
    print(f"[SPAMTAG] Delay: {SPAMTAG_DELAY}s")
    print(f"[SPAMTAG] Fosh count: {len(fosh_list)}")
    print(f"[SPAMTAG] Using User Account")
    
    while SPAMTAG_ACTIVE and SPAMTAG_TARGET:
        try:
            # Select random fosh text
            fosh_text = random.choice(fosh_list)
            
            # Add tag to fosh text
            if SPAMTAG_TAG:
                final_text = f"{SPAMTAG_TAG} {fosh_text}"
            else:
                final_text = fosh_text
            
            await clients[0].send_message(SPAMTAG_TARGET, final_text)
            SPAMTAG_MESSAGES_SENT += 1
            print(f"[SPAMTAG] Sent: {final_text[:50]}... ({SPAMTAG_MESSAGES_SENT})")
            
            # Wait for delay
            await asyncio.sleep(SPAMTAG_DELAY)
            
        except FloodWaitError as e:
            print(f"[SPAMTAG] Flood wait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[SPAMTAG] Error: {e}")
            await asyncio.sleep(5)
    
    print(f"[SPAMTAG] Stopped! Total messages sent: {SPAMTAG_MESSAGES_SENT}")

async def spam_loop(client_instance, target, text, speed, bot_index):
    while bot_spam_states.get(bot_index, {}).get('active', False) and target and client_instance:
        try:
            await client_instance.send_message(target, text)
            print(f"[USER] Sent to {target} | Speed: {speed}s")
        except FloodWaitError as e:
            print(f"[USER] Flood wait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[USER] [ERROR] Spam failed: {e}")
        await asyncio.sleep(speed)

async def all_spam_loop():
    global SPAM_TARGET, SPAM_TEXT, SPAM_SPEED
    
    if not SPAM_TARGET:
        print("[ALL SPAM] No target set!")
        return
    
    if not clients:
        print("[ALL SPAM] No client available!")
        return
    
    print(f"[ALL SPAM] Starting User Account to spam target: {SPAM_TARGET}")
    
    for i, client in enumerate(clients):
        if i not in bot_spam_states:
            bot_spam_states[i] = {'active': False, 'task': None}
        
        if bot_spam_states[i]['task'] and not bot_spam_states[i]['task'].done():
            bot_spam_states[i]['task'].cancel()
        
        bot_spam_states[i]['active'] = True
        bot_spam_states[i]['task'] = asyncio.create_task(
            spam_loop(client, SPAM_TARGET, SPAM_TEXT, SPAM_SPEED, i)
        )
        print(f"[ALL SPAM] User account started spamming")
    
    print(f"[ALL SPAM] User account is now spamming!")

async def stop_all_spam():
    for i in bot_spam_states:
        bot_spam_states[i]['active'] = False
        if bot_spam_states[i]['task'] and not bot_spam_states[i]['task'].done():
            bot_spam_states[i]['task'].cancel()
            bot_spam_states[i]['task'] = None
    
    print("[ALL SPAM] User stopped spamming")

async def on_off_loop(client_instance, chat_id):
    global ON_OFF_ACTIVE, ON_OFF_SEQUENCE, ON_OFF_DELAY
    while ON_OFF_ACTIVE and client_instance:
        for item in ON_OFF_SEQUENCE:
            if not ON_OFF_ACTIVE:
                break
            try:
                await client_instance.send_message(chat_id, item)
            except Exception as e:
                print(f"[ERROR] on/off send failed: {e}")
            await asyncio.sleep(ON_OFF_DELAY)
        await asyncio.sleep(0)

async def send_loading_animation(event):
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
    loading_msg = await event.reply(" Loading...\n" + loading_steps[0])
    for i in range(1, len(loading_steps)):
        await asyncio.sleep(0.3)
        try:
            await loading_msg.edit(f" Loading...\n{loading_steps[i]}")
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

async def forward_spam_function(client_instance):
    global FORWARD_SPAM_ACTIVE
    print("Forward spam thread started")
    ensure_forward_files()
    while FORWARD_SPAM_ACTIVE and client_instance:
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
            source_message = await client_instance.get_messages(source_channel, ids=source_msg_id)
            if not source_message:
                print(f"Message {source_msg_id} not found in {source_channel}")
                FORWARD_SPAM_ACTIVE = False
                break

            await client_instance.forward_messages(target_id, source_message)

            if extra_text:
                if extra_pos == "before":
                    await client_instance.send_message(target_id, f"{extra_text}\n\n")
                else:
                    await client_instance.send_message(target_id, f"\n\n{extra_text}")

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
    global ADMIN_IDS, FOSHLIST, SPAM_TARGET, SPAM_TEXT, SPAM_SPEED
    global ON_OFF_ACTIVE, ON_OFF_TASK, ENEMY_TARGET, ENEMY_ACTIVE, REPLY_TO_ENEMY, ORIGINAL_NAME, ORIGINAL_PHOTO, FORWARD_SPAM_ACTIVE, FORWARD_SPAM_TASK, AI_MODE_ACTIVE
    global AI_SPAM_ACTIVE, AI_SPAM_TARGET, AI_SPAM_TEXT, AI_SPAM_DELAY, AI_SPAM_END_TIME, AI_SPAM_TASK, AI_SPAM_MESSAGES_SENT, AI_SPAM_TOTAL_DAYS, AI_SPAM_BOT_COUNT
    global SPAMTAG_ACTIVE, SPAMTAG_TARGET, SPAMTAG_TAG, SPAMTAG_DELAY, SPAMTAG_BOT_COUNT, SPAMTAG_TASK, SPAMTAG_MESSAGES_SENT
    
    user_id = event.sender_id
    client_instance = event.client
    
    if ENEMY_ACTIVE and REPLY_TO_ENEMY and FOSHLIST:
        if user_id == ENEMY_TARGET:
            reply_text = random.choice(FOSHLIST)
            await asyncio.sleep(0.5)
            try:
                await event.reply(reply_text)
                print(f"[USER] Enemy reply sent to {user_id}")
            except Exception as e:
                print(f"[ERROR] Enemy reply failed: {e}")
            return
    
    if not event.message or not event.message.text:
        return
    
    text = event.message.text.strip().lower() if event.message.text else ""
    
    print(f"[USER] DEBUG: Received command: '{text}' from {user_id}")
    
    me = await client_instance.get_me()

    if user_id not in ADMIN_IDS:
        print(f"[USER] Ignored non-admin message from {user_id}")
        return
    
    if event.is_private:
        location = "PRIVATE"
    elif event.is_group:
        location = "GROUP"
    elif event.is_channel:
        location = "CHANNEL"
    else:
        location = "UNKNOWN"
    
    print(f"[USER] Admin {user_id} in {location}: {text[:50]}")
    
    # SPAMTAG COMMANDS
    if text.startswith("spamtag"):
        parts = text.split()
        
        if len(parts) < 2:
            await event.reply(
                "Usage:\n"
                "spamtag (@tag) with 1-60 delay\n"
                "spamtag (@tag) with 1-60 delay with 3 bot\n"
                "spamtag off - Stop spamtag\n"
                "spamtag status - Check status"
            )
            return
        
        # Check if it's a command
        if parts[1].lower() == "off":
            if SPAMTAG_ACTIVE:
                SPAMTAG_ACTIVE = False
                if SPAMTAG_TASK and not SPAMTAG_TASK.done():
                    SPAMTAG_TASK.cancel()
                    SPAMTAG_TASK = None
                await event.reply(f"Spamtag stopped! Total sent: {SPAMTAG_MESSAGES_SENT}")
            else:
                await event.reply("Spamtag is not active!")
            return
        
        if parts[1].lower() == "status":
            status = "ON" if SPAMTAG_ACTIVE else "OFF"
            await event.reply(
                f"Spamtag Status:\n"
                f"Active: {status}\n"
                f"Target: {SPAMTAG_TARGET or 'Not set'}\n"
                f"Tag: {SPAMTAG_TAG or 'No tag'}\n"
                f"Delay: {SPAMTAG_DELAY}s\n"
                f"Messages sent: {SPAMTAG_MESSAGES_SENT}"
            )
            return
        
        # Parse spamtag command
        tag = None
        delay = 1.0
        
        # Extract tag from first argument
        if parts[1].startswith("@"):
            tag = parts[1]
            start_index = 2
        else:
            tag = None
            start_index = 1
        
        # Parse "with" and "delay"
        try:
            for i in range(start_index, len(parts)):
                if parts[i].lower() == "with" and i + 1 < len(parts):
                    if parts[i + 1].lower() == "delay" and i + 2 < len(parts):
                        try:
                            delay = float(parts[i + 2])
                            if delay < 0.5:
                                delay = 0.5
                            if delay > 60:
                                delay = 60
                        except ValueError:
                            delay = 1.0
                        i += 2
                    elif parts[i + 1].isdigit():
                        try:
                            delay = float(parts[i + 1])
                            if delay < 0.5:
                                delay = 0.5
                            if delay > 60:
                                delay = 60
                        except ValueError:
                            delay = 1.0
                        i += 1
        except Exception as e:
            print(f"[SPAMTAG] Parse error: {e}")
        
        # Set target to current chat
        SPAMTAG_TARGET = event.chat_id
        SPAMTAG_TAG = tag if tag else ""
        SPAMTAG_DELAY = delay
        SPAMTAG_MESSAGES_SENT = 0
        SPAMTAG_ACTIVE = True
        
        # Start spamtag task
        if SPAMTAG_TASK and not SPAMTAG_TASK.done():
            SPAMTAG_TASK.cancel()
        SPAMTAG_TASK = asyncio.create_task(spamtag_loop())
        
        await event.reply(
            f"Spamtag started!\n"
            f"Target: {SPAMTAG_TARGET}\n"
            f"Tag: {SPAMTAG_TAG or 'No tag'}\n"
            f"Delay: {SPAMTAG_DELAY}s\n"
            f"Using fosh.txt with {len(FOSHLIST)} items"
        )
        return
    
    # AI Spam Commands
    if text.startswith("spamhere"):
        AI_SPAM_TARGET = event.chat_id
        
        spam_text = "Hello"
        duration = 1
        delay = 60
        
        extracted_text = extract_text_in_parentheses(text)
        if extracted_text:
            spam_text = extracted_text
        
        clean_text = text
        if extracted_text:
            clean_text = text.replace(f"({extracted_text})", "").strip()
        
        parts = clean_text.split()
        for i, part in enumerate(parts):
            if part == "for" and i + 1 < len(parts):
                duration_text = parts[i + 1]
                if i + 2 < len(parts):
                    duration_text += " " + parts[i + 2]
                duration = parse_duration(duration_text)
            if part == "with" and i + 1 < len(parts) and parts[i + 1] == "delay":
                if i + 2 < len(parts):
                    delay_text = parts[i + 2]
                    if i + 3 < len(parts):
                        delay_text += " " + parts[i + 3]
                    delay = parse_delay(delay_text)
                    print(f"[DEBUG] Delay text: '{delay_text}' -> {delay} seconds")
        
        AI_SPAM_TOTAL_DAYS = duration
        AI_SPAM_END_TIME = datetime.now() + timedelta(days=duration)
        AI_SPAM_DELAY = delay
        AI_SPAM_TEXT = spam_text
        AI_SPAM_MESSAGES_SENT = 0
        AI_SPAM_BOT_COUNT = 1
        
        AI_SPAM_ACTIVE = True
        if AI_SPAM_TASK and not AI_SPAM_TASK.done():
            AI_SPAM_TASK.cancel()
        AI_SPAM_TASK = asyncio.create_task(ai_spam_loop())
        
        delay_text = format_delay(delay)
        
        await event.reply(
            f"AI Spam started!\n"
            f"Target: {AI_SPAM_TARGET}\n"
            f"Text: {spam_text}\n"
            f"Duration: {duration} days\n"
            f"End time: {AI_SPAM_END_TIME.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Delay: {delay_text} ({delay} seconds)\n"
            f"Using User Account"
        )
        return
    
    if text == "stopspam":
        if AI_SPAM_ACTIVE:
            AI_SPAM_ACTIVE = False
            if AI_SPAM_TASK and not AI_SPAM_TASK.done():
                AI_SPAM_TASK.cancel()
                AI_SPAM_TASK = None
            await event.reply(f"AI Spam stopped! Total messages sent: {AI_SPAM_MESSAGES_SENT}")
        else:
            await event.reply("No AI spam is running!")
        return
    
    if text == "spamstatus":
        if AI_SPAM_ACTIVE:
            remaining = AI_SPAM_END_TIME - datetime.now() if AI_SPAM_END_TIME else "Unknown"
            if isinstance(remaining, timedelta):
                days = remaining.days
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                remaining_str = f"{days}d {hours}h {minutes}m"
            else:
                remaining_str = str(remaining)
            
            delay_text = format_delay(AI_SPAM_DELAY)
            
            await event.reply(
                f"AI Spam Status:\n"
                f"Active: Yes\n"
                f"Target: {AI_SPAM_TARGET}\n"
                f"Text: {AI_SPAM_TEXT}\n"
                f"Delay: {delay_text}\n"
                f"Using User Account\n"
                f"Messages sent: {AI_SPAM_MESSAGES_SENT}\n"
                f"Remaining: {remaining_str}\n"
                f"End time: {AI_SPAM_END_TIME.strftime('%Y-%m-%d %H:%M:%S') if AI_SPAM_END_TIME else 'Unknown'}"
            )
        else:
            await event.reply("AI Spam is not active!")
        return
    
    # AI Mode Commands
    if text == "ai mod on":
        AI_MODE_ACTIVE = True
        await event.reply("AI Mode is now ON. You can chat with me!")
        print("[AI] AI Mode activated")
        return
    
    if text == "ai mod off":
        AI_MODE_ACTIVE = False
        await clear_ai_context(user_id)
        await event.reply("AI Mode is now OFF.")
        print("[AI] AI Mode deactivated and context cleared")
        return
    
    if text == "ai status":
        status = "ON" if AI_MODE_ACTIVE else "OFF"
        context_count = len(AI_CONTEXT.get(user_id, []))
        await event.reply(f"AI Mode: {status}\nContext messages: {context_count}/{MAX_CONTEXT_MESSAGES}")
        return
    
    if text == "ai clear":
        if await clear_ai_context(user_id):
            await event.reply("AI context cleared! I forgot our previous conversation.")
        else:
            await event.reply("No context to clear.")
        return
    
    # AI Chat
    if AI_MODE_ACTIVE and not text.startswith(("ai", "help", "spam", "set", "ping", "status", "id", "join", "sudo", "kiladmin", "clone", "enemy", "fosh", "fspam", "showfwd", "on", "off", "speed", "addfosh", "removefosh", "listfosh", "setenemy", "enemyoff", "setreply", "cloneback", "stopspam", "spamstatus", "spamhere", "spamtag")):
        
        replied_text = None
        if event.message.is_reply:
            try:
                replied_msg = await event.get_reply_message()
                if replied_msg and replied_msg.text:
                    sender = await client_instance.get_entity(replied_msg.sender_id)
                    sender_name = sender.first_name or "Unknown"
                    replied_text = f"[{sender_name}]: {replied_msg.text[:200]}"
                    print(f"[AI] Reply detected from {sender_name}")
            except Exception as e:
                print(f"[AI] Error getting reply message: {e}")
        
        await event.reply("Thinking...")
        ai_response = await get_ai_response(user_id, text, replied_text)
        if ai_response:
            if ai_response.startswith("ERROR:"):
                await event.reply(ai_response)
            else:
                await event.reply(ai_response)
        else:
            await event.reply("Sorry, I couldn't process your request.")
        return
    
    # Master control commands
    if text == "runall":
        if not ALL_BOTS_RUNNING:
            ALL_BOTS_RUNNING = True
            await event.reply("Starting User Account...")
            for client in clients:
                try:
                    await client.send_message(me.id, "START")
                except:
                    pass
        else:
            await event.reply("User account is already running!")
        return
    
    if text == "stopall":
        if ALL_BOTS_RUNNING:
            ALL_BOTS_RUNNING = False
            await event.reply("Stopping User Account...")
            for client in clients:
                try:
                    await client.send_message(me.id, "STOP")
                except:
                    pass
        else:
            await event.reply("User account is not running!")
        return
    
    # ALL SPAM COMMANDS
    if text == "allspam":
        if not SPAM_TARGET:
            await event.reply("No target set! Use `setid <chat_id>` first.")
            return
        
        any_active = False
        for i in bot_spam_states:
            if bot_spam_states[i].get('active', False):
                any_active = True
                break
        
        if any_active:
            await event.reply("User is already spamming! Use `allspamoff` first.")
            return
        
        await event.reply(f"Starting User Account to spam target: {SPAM_TARGET}\nText: {SPAM_TEXT}\nSpeed: {SPAM_SPEED}s")
        
        await all_spam_loop()
        await event.reply(f"User account is now spamming!")
        return
    
    if text == "allspamoff":
        any_active = False
        for i in bot_spam_states:
            if bot_spam_states[i].get('active', False):
                any_active = True
                break
        
        if not any_active:
            await event.reply("User is not currently spamming!")
            return
        
        await stop_all_spam()
        await event.reply(f"User stopped spamming!")
        return
    
    if text == "help" or text == "راهنما":
        await send_loading_animation(event)
        help_text = """
```spam - Start spam on this bot
spamoff - Stop spam on this bot
allspam - Start spam on ALL bots
allspamoff - Stop spam on ALL bots
setfosh <text> - Change spam text
speed <1-60> - Set speed
id - Get chat ID
setid <chat_id> - Set target
join <link> - Join link
ping - Check bot ping
status - Show status
help2
help3
runall - Start all bots
stopall - Stop all bots````
"""
        try:
            await client_instance.send_file(
                event.chat_id,
                HELP_IMAGE_URL,
                caption=help_text,
                reply_to=event.message.id,
            )
        except Exception as e:
            print(f"[ERROR] Help media send failed: {e}")
            try:
                await client_instance.send_message(event.chat_id, help_text, reply_to=event.message.id)
            except Exception as fallback_error:
                print(f"[ERROR] Help text fallback failed: {fallback_error}")
        return

    if text == "help2":
        await send_loading_animation(event)
        help_text = """
```sudo su <user_id> - add admin 
kiladmin <user_id> - remove admin
clone @user - Clone profile
cloneback - Restore original profile
on/off - number fight 
setenemy - mark use as enemy
enemyoff - remove user form enemy list
listfosh - show the fosh list
addfosh - add fosh 
removefosh - remove fosh
fspam_on - Start forward spam
fspam_off - Stop forward spam
showfwd - Show forward config
setfwd <link> - Set forward source
setfwd_delay <min> <max> - Set delay
setfwd_text <text> - Set extra text
setfwd_pos before/after - Set position````
"""
        try:
            await client_instance.send_file(
                event.chat_id,
                HELP_IMAGE_URL,
                caption=help_text,
                reply_to=event.message.id,
            )
        except Exception as e:
            print(f"[ERROR] Help2 media send failed: {e}")
            try:
                await client_instance.send_message(event.chat_id, help_text, reply_to=event.message.id)
            except Exception as fallback_error:
                print(f"[ERROR] Help2 text fallback failed: {fallback_error}")
        return

    if text == "help3":
        await send_loading_animation(event)
        help_text = """
````ai mod on - Turn on AI chat
ai mod off - Turn off AI chat
ai status - Check AI status
ai clear - Clear AI memory
spamhere for [days] with [delay] delay (text) - AI Spam
stopspam - Stop AI spam
spamstatus - Check AI spam status
spamtag (@tag) with 1-60 delay - Send FOSH with tag
spamtag off - Stop spamtag
spamtag status - Check spamtag status

Delay options: 1 sec to 60 min
Examples:
spamhere for 3 day with 1 sec delay (hello)
spamtag @target with 2 delay
spamtag @everyone with 5 delay````
"""
        try:
            await client_instance.send_file(
                event.chat_id,
                HELP_IMAGE_URL,
                caption=help_text,
                reply_to=event.message.id,
            )
        except Exception as e:
            print(f"[ERROR] Help3 media send failed: {e}")
            try:
                await client_instance.send_message(event.chat_id, help_text, reply_to=event.message.id)
            except Exception as fallback_error:
                print(f"[ERROR] Help3 text fallback failed: {fallback_error}")
        return
    
    if text == "on":
        if not ON_OFF_ACTIVE:
            ON_OFF_ACTIVE = True
            if ON_OFF_TASK and not ON_OFF_TASK.done():
                ON_OFF_TASK.cancel()
            ON_OFF_TASK = asyncio.create_task(on_off_loop(client_instance, event.chat_id))
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
                print(f"[USER] Spam speed changed to {SPAM_SPEED}s")
                await event.reply(f"Speed set to {SPAM_SPEED} seconds")
        except ValueError:
            pass
        return  
    
    if text == "spam":
        if not clients:
            await event.reply("User not connected!")
            return
        
        bot_index = 0
        
        if not SPAM_TARGET:
            await event.reply("No target chat set. Use `setid` first.")
            return
        
        if bot_index not in bot_spam_states:
            bot_spam_states[bot_index] = {'active': False, 'task': None}
        
        if bot_spam_states[bot_index].get('active', False):
            await event.reply("User is already spamming! Use `spamoff` to stop.")
            return
        
        await event.reply(
            f"Spam started on user account!\n"
            f"Target: {SPAM_TARGET}\n"
            f"Text: {SPAM_TEXT}\n"
            f"Speed: {SPAM_SPEED} seconds"
        )
        
        bot_spam_states[bot_index]['active'] = True
        if bot_spam_states[bot_index]['task'] and not bot_spam_states[bot_index]['task'].done():
            bot_spam_states[bot_index]['task'].cancel()
        bot_spam_states[bot_index]['task'] = asyncio.create_task(
            spam_loop(clients[0], SPAM_TARGET, SPAM_TEXT, SPAM_SPEED, bot_index)
        )
        return
    
    if text == "spamoff":
        bot_index = 0
        
        if bot_index not in bot_spam_states or not bot_spam_states[bot_index].get('active', False):
            await event.reply("User is not spamming!")
            return
        
        bot_spam_states[bot_index]['active'] = False
        if bot_spam_states[bot_index]['task'] and not bot_spam_states[bot_index]['task'].done():
            bot_spam_states[bot_index]['task'].cancel()
            bot_spam_states[bot_index]['task'] = None
        
        await event.reply("Spam stopped on user account!")
        return
    
    if text.startswith("setfosh "):
        SPAM_TEXT = text[8:].strip()
        await event.reply(f"Spam text set to:\n{SPAM_TEXT}")
        return
    
    if text == "id":
        chat_id = event.chat_id
        chat_type = "Private" if event.is_private else "Group" if event.is_group else "Channel"
        await event.reply(f"Chat ID {chat_id}\nType: {chat_type}")
        return
    
    if text.startswith("setid "):
        try:
            SPAM_TARGET = int(text[6:].strip())
            await event.reply(f"Target set to {SPAM_TARGET}")
            try:
                with open(TARGET_ID_FILE, "w", encoding="utf-8") as f:
                    f.write(str(SPAM_TARGET))
            except Exception as e:
                print(f"[ERROR] Could not save target ID file: {e}")
        except ValueError:
            await event.reply("Invalid chat ID! Must be a number.")
        return

    if text.startswith("setfwd "):
        link = text[7:].strip()
        if not link:
            await event.reply("Usage: setfwd <message_link>")
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
            await event.reply(f" Source set!\nChannel: {channel}\nMessage ID: {msg_id}")
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
            await event.reply(" Usage: setfwd_delay <min> <max>")
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
            await event.reply(" Usage: setfwd_pos before or setfwd_pos after")
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
        FORWARD_SPAM_TASK = asyncio.create_task(forward_spam_function(client_instance))
        await event.reply(" FWD SPAM RUNNING")
        return

    if text == "fspam_off":
        if FORWARD_SPAM_ACTIVE:
            FORWARD_SPAM_ACTIVE = False
            if FORWARD_SPAM_TASK and not FORWARD_SPAM_TASK.done():
                FORWARD_SPAM_TASK.cancel()
            await event.reply(" FWD SPAM STOPPED")
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
        await event.reply(f"Forward Config - {status}\n TARGET: {target}\n SOURCE: {source}/{msg_id}\n DELAY: {min_delay}-{max_delay} seconds")
        return

    if text.startswith("join "):
        invite_input = text[5:].strip()
        if not invite_input:
            await event.reply(" Usage: join <invite_link> or join @channelname")
            return

        invite_input = invite_input.strip()
        target = invite_input

        if "t.me/" in target or "telegram.me/" in target:
            target = target.replace("https://", "").replace("http://", "")
            target = target.replace("t.me/", "").replace("telegram.me/", "")
            target = target.split("?", 1)[0].split("/", 1)[0]
            if target.lower().startswith("joinchat"):
                target = target[len("joinchat"):]
            if target.startswith("+"):
                target = target[1:]

        target = target.strip()
        if not target:
            await event.reply(" Invalid invite link. Use a real Telegram invite link or public channel username.")
            return

        try:
            if not target.lower().startswith("joinchat") and not target.startswith("+"):
                try:
                    entity = await client_instance.get_entity(target if not target.startswith("@") else target[1:])
                    await client_instance(JoinChannelRequest(entity))
                    await event.reply(f" Joined successfully: {invite_input}")
                    return
                except Exception:
                    pass

            await client_instance(ImportChatInviteRequest(hash=target))
            await event.reply(f" Joined successfully via invite: {invite_input}")
        except Exception as e:
            error_text = str(e).lower()
            if "expired" in error_text or "invalid" in error_text or "not valid" in error_text or "already used" in error_text:
                await event.reply(" The invite link is expired, invalid, or already used. Please provide a fresh invite link.")
            else:
                await event.reply(f" Failed to join: {str(e)[:120]}")
        return
    
    if text == "addfosh":
        if not event.is_reply:
            await event.reply(" Reply to a message and type addfosh to add it to fosh list")
            return
        
        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.text:
            await event.reply(" The replied message has no text.")
            return
        
        FOSHLIST.append(replied_msg.text)
        save_fosh_file()
        await event.reply(
            f"Fosh added (Index #{len(FOSHLIST)-1})\n"
            f"Preview: {replied_msg.text[:50]}..."
        )
        return

    await _commands_handler(event, text, client_instance)

try:
    with open(FOSH_FILE, "r", encoding="utf-8") as f:
        FOSHLIST: List[str] = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    FOSHLIST: List[str] = [
        "بیا پایین",
        "کصخل",
        "برو گمشو"
    ]
    print("fosh.txt not found. Using default fosh list.")

async def _commands_handler(event, text, client):
    global ADMIN_IDS, FOSHLIST, ENEMY_TARGET, ENEMY_ACTIVE, REPLY_TO_ENEMY, ORIGINAL_NAME, ORIGINAL_PHOTO
    user_id = event.sender_id

    if text == "listfosh":
        if not FOSHLIST:
            await event.reply(" Foshlist is empty. Use addfosh to fill it.")
            return
        lines = []
        for i, item in enumerate(FOSHLIST):
            snippet = item.replace("\n", " ")[:60]
            lines.append(f"{i}: {snippet}...")
        msg = " FOSHLIST (index to use with removefosh):\n" + "\n".join(lines[:20])
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
                f" Removed fosh {idx}:\n{removed[:50]}..."
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
            f" Enemy set: @{target_user.username or target_user.first_name or 'Unknown'}\n"
            f"ID: {ENEMY_TARGET}\n"
        )
        return

    if text == "enemyoff":
        if ENEMY_ACTIVE:
            ENEMY_ACTIVE = False
            await event.reply(" Enemy mode deactivated.")
        else:
            await event.reply("Enemy mode is already off.")
        return

    if text.startswith("setreply "):
        mode = text[9:].strip().lower()
        if mode not in ["on", "off"]:
            await event.reply(" Usage: setreply on or setreply off")
            return
        REPLY_TO_ENEMY = mode == "on"
        await event.reply(f" Auto-reply set to: {REPLY_TO_ENEMY}")
        return
    
    if text.startswith("clone "):
        target_identifier = text[6:].strip()
        if target_identifier.startswith("@"):
            target_identifier = target_identifier[1:]
        
        await event.reply(f" Searching for user: {target_identifier}...")
        
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
                await event.reply(" Could not find user. Make sure they exist or use their ID.")
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
            
            await event.reply(f" Cloning {target_user.first_name or 'Unknown'}...")
            
            try:
                photos = await client.get_profile_photos(target_user, limit=1)
                
                if photos:
                    photo = photos[0]
                    photo_path = await client.download_media(photo, file="temp_profile.jpg")
                    
                    if photo_path:
                        await client(UploadProfilePhotoRequest(
                            file=await client.upload_file(photo_path)
                        ))
                        await event.reply(" Profile picture cloned successfully!")
                        try:
                            os.remove(photo_path)
                        except:
                            pass
                else:
                    await event.reply("Target user has no profile picture. Skipping photo clone.")
            except Exception as e:
                await event.reply(f" Failed to set profile picture: {str(e)[:100]}")
            
            new_first_name = target_user.first_name or ""
            new_last_name = target_user.last_name or ""
            
            try:
                await client(UpdateProfileRequest(
                    first_name=new_first_name,
                    last_name=new_last_name
                ))
                
                await event.reply(
                    f" Name cloned successfully\n"
                    f"New name: {new_first_name} {new_last_name}".strip()
                )
            except Exception as e:
                await event.reply(f" Failed to set name {str(e)[:100]}")
            
            await event.reply(
                f"CLONE COMPLETE!\n"
                f"Now impersonating: {target_user.first_name or 'Unknown'}\n"
                f"ID: {target_user.id}"
            )
            
        except Exception as e:
            await event.reply(f" Clone failed {str(e)[:200]}")
        return
    
    if text == "cloneback":
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
            
            await event.reply(" You're back to original")
        except Exception as e:
            await event.reply(f" Failed to restore: {str(e)[:100]}")
        return

    if text == "ping":
        start = time.perf_counter()
        await event.reply(" Pinging")  
        end = time.perf_counter()
        ping_ms = (end - start) * 1000
        await event.reply(f"ping is {ping_ms:.2f} ms")
        return
    
    if text == "status":
        context_count = len(AI_CONTEXT.get(user_id, []))
        ai_spam_status = "ON" if AI_SPAM_ACTIVE else "OFF"
        spamtag_status = "ON" if SPAMTAG_ACTIVE else "OFF"
        status_msg = f"""
BOT STATUS

Admins: {len(ADMIN_IDS)} users
Foshlist size: {len(FOSHLIST)} items
Spam target: {SPAM_TARGET or 'Not set'}
Spam text: {SPAM_TEXT[:50]}...
Spam speed: {SPAM_SPEED} seconds
Spam active: {SPAM_ACTIVE}
Enemy target: {ENEMY_TARGET or 'None'}
Enemy active: {ENEMY_ACTIVE}
AI Mode: {'ON' if AI_MODE_ACTIVE else 'OFF'}
AI Context: {context_count} messages
AI Spam: {ai_spam_status}
Spamtag: {spamtag_status}
"""
        await event.reply(status_msg)
        return
    
    if text.startswith("sudo su"):
        try:
            parts = text.split()
            if len(parts) < 3:
                await event.reply(" Please provide a user ID.")
                return
            try:
                new_admin = int(parts[2].strip())
            except ValueError:
                await event.reply(" Invalid user ID. Must be a number.")
                return

            if new_admin == user_id:
                await event.reply(" you have already root permission")
                return
            if new_admin in ADMIN_IDS:
                await event.reply(" User is already an admin.")
                return
            ADMIN_IDS.add(new_admin)
            await event.reply(f" User {new_admin} is now have root permission")
            print(f"[USER]  New admin added: {new_admin}")
            print(f"[USER]  Current admins: {ADMIN_IDS}")

            try:
                await client.send_message(
                    new_admin,
                    "you are new admin\n"
                    "Commands:\n"
                    "help - Show all commands\n"
                    "help2 - Show admin commands\n"
                    "help3 - Show AI and spamtag commands\n"
                    "spam - Start spamming\n"
                    "spamoff - Stop spamming\n"
                    "speed <1-60> - Set spam speed\n"
                    "setfosh <text> - Set spam message\n"
                    "id - Get chat ID\n"
                    "setid <chat_id> - Set target chat\n"
                    "addfosh - Save replied message\n"
                    "listfosh - Show all saved\n"
                    "setenemy - Mark enemy\n"
                    "clone @user - Clone profile\n"
                    "ping - Check latency\n"
                    "status - Show config\n"
                    "ai mod on - Turn on AI chat\n"
                    "ai mod off - Turn off AI chat\n"
                    "ai status - Check AI status\n"
                    "ai clear - Clear AI memory\n"
                    "spamhere for [days] with [delay] delay (text) - AI Spam\n"
                    "stopspam - Stop AI spam\n"
                    "spamstatus - Check AI spam status\n"
                    "spamtag (@tag) with 1-60 delay - Send FOSH with tag\n"
                    "spamtag off - Stop spamtag\n"
                    "spamtag status - Check spamtag status\n"
                )
                print(f"[USER]  Welcome message sent to {new_admin}")
            except Exception as e:
                print(f"[USER]  Failed to send welcome message: {e}")

            return
        except Exception as e:
            await event.reply(f" Failed to add admin: {str(e)[:100]}")
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
            await event.reply(f" User {rem_admin} dont have root permission any more")
            print(f"[USER]  Admin killed: {rem_admin}")
            print(f"[USER]  Current admins: {ADMIN_IDS}")
        except (ValueError, IndexError):
            await event.reply(" Invalid user ID.")
        return

async def run_user():
    global clients, MASTER_CLIENT
    
    print("=" * 60)
    print("[USER] Starting User Account...")
    print("[USER] You will be asked for your phone number and verification code")
    print("=" * 60)
    
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    clients.append(client)
    MASTER_CLIENT = client
    
    me = await client.get_me()
    
    print(f"[USER] Logged in as: {me.first_name} (@{me.username})")
    print(f"[USER] User ID: {me.id}")
    print("=" * 60)
    
    client.add_event_handler(handle_all_messages, events.NewMessage(incoming=True))
    
    await client.run_until_disconnected()

async def main():
    global ALL_BOTS_RUNNING
    
    print("=" * 60)
    print("[USER] Starting User Account System...")
    print(f"[USER] Admins: {ADMIN_IDS}")
    print("[AI] AI Mode: OFF (use 'ai mod on' to enable chat)")
    print("[AI] Using Model: agnes-2.0-flash")
    print("[AI] Context memory: ENABLED")
    print("[AI] Reply detection: ENABLED")
    print("[AI] AI Spam: Ready! Use 'spamhere' command")
    print("[AI] AI Spam: Delay from 1 sec to 60 min")
    print("[SPAMTAG] Spamtag: Ready! Use 'spamtag (@tag) with 1-60 delay'")
    print("[SPAMTAG] Reads from fosh.txt and adds tag to each message")
    print("=" * 60)
    
    ensure_forward_files()
    
    await run_user()

if __name__ == "__main__":
    asyncio.run(main())
