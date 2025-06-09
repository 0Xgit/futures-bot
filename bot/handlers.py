import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.models import Database, UserModel, ExchangeModel, TradeModel, PortfolioModel
from exchanges.auth_manager import ExchangeAuthManager
from exchanges.balance_checker import BalanceChecker
from exchanges.futures_trader import FuturesTrader
from config.settings import Config
import asyncio

logger = logging.getLogger(__name__)

class BotHandlers:
    def __init__(self):
        self.db = Database()
        self.user_model = UserModel(self.db)
        self.exchange_model = ExchangeModel(self.db)
        self.trade_model = TradeModel(self.db)
        self.portfolio_model = PortfolioModel(self.db)
        self.auth_manager = ExchangeAuthManager(Config.ENCRYPTION_KEY)
        self.user_sessions = {}
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Enhanced start command with dashboard"""
        try:
            user = update.effective_user
            
            # Create or get user
            db_user = self.user_model.get_user(user.id)
            if not db_user:
                user_id = self.user_model.create_user(user.id, user.username, user.first_name, user.last_name)
            else:
                user_id = db_user['id']
            
            welcome_text = (
                "🚀 *AUTOMATED FUTURES TRADING BOT* 🚀\n\n"
                "💎 **Professional Trading Features:**\n"
                "• 🤖 Fully automated signal execution\n"
                "• 📊 Real-time portfolio tracking\n"
                "• 🛡️ Advanced risk management\n"
                "• 💰 Live P&L monitoring\n"
                "• 📈 Multi-exchange support\n"
                "• 🎯 Professional trading signals\n\n"
                "🔥 **Supported Futures Exchanges:**\n"
                "• Binance USDT-M Futures\n"
                "• Bybit USDT Perpetual\n"
                "• OKX Perpetual Futures\n"
                "• Bitget USDT-M Futures\n"
                "• MEXC Futures\n\n"
                "🚀 **Get Started:**\n"
                "1. Connect your futures exchange\n"
                "2. Subscribe to trading signals\n\n"
                "⚠️ **LIVE MAINNET TRADING** - Real money at risk!"
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "🔗 Connect Exchange",
                    callback_data="connect_exchange"
                )],
                [
                    InlineKeyboardButton("💰 Check Balance", callback_data="check_balance"),
                    InlineKeyboardButton("📊 Portfolio", callback_data="view_portfolio")
                ],
                [
                    InlineKeyboardButton("📈 Trades", callback_data="view_trades"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="view_settings")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def connect_command(self, update: Update, context: CallbackContext):
        """Connect futures exchanges"""
        try:
            connect_text = (
                "🔗 *CONNECT FUTURES EXCHANGES* 🔗\n\n"
                "💰 **LIVE MAINNET TRADING**\n"
                "Select your futures exchange to connect:\n\n"
                "⚠️ **API REQUIREMENTS:**\n"
                "• ✅ Enable: Futures Trading, Read Account\n"
                "• ❌ Disable: Withdrawals (NEVER enable)\n"
                "• 🔒 Use IP restrictions if available\n\n"
                "🎯 **Supported Futures Exchanges:**"
            )
            
            keyboard = []
            for exchange_id, exchange_info in Config.SUPPORTED_EXCHANGES.items():
                keyboard.append([InlineKeyboardButton(
                    f"{exchange_info['display_name']} Futures",
                    callback_data=f"connect_{exchange_id}"
                )])
            
            keyboard.append([InlineKeyboardButton(
                "📚 API Setup Guides",
                callback_data="api_guides"
            )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(connect_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in connect_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def balance_command(self, update: Update, context: CallbackContext):
        """Check balances across all exchanges"""
        try:
            user_id = update.effective_user.id
            db_user = self.user_model.get_user(user_id)
            
            if not db_user:
                await update.message.reply_text("❌ Please start the bot first with /start")
                return
            
            exchanges = self.exchange_model.get_user_exchanges(db_user['id'])
            
            if not exchanges:
                await update.message.reply_text(
                    "❌ No connected exchanges.\n\nUse /connect to link your futures accounts."
                )
                return
            
            await update.message.reply_text("🔄 Checking live futures balances...")
            
            total_balance = 0
            balance_text = "💰 *LIVE FUTURES BALANCES* 💰\n\n"
            
            for exchange in exchanges:
                try:
                    # Decrypt credentials
                    api_key, api_secret, passphrase = self.auth_manager.decrypt_credentials(
                        exchange['api_key_encrypted'],
                        exchange['api_secret_encrypted'],
                        exchange['passphrase_encrypted']
                    )
                    
                    # Get balance
                    balance = await BalanceChecker.get_balance(
                        exchange['exchange_name'], api_key, api_secret, passphrase
                    )
                    
                    total_balance += balance
                    exchange_name = Config.SUPPORTED_EXCHANGES[exchange['exchange_name']]['display_name']
                    
                    balance_text += (
                        f"🏢 **{exchange_name}**\n"
                        f"💵 Balance: `{balance:,.2f} USDT`\n"
                        f"⚡ Leverage: `{exchange.get('leverage', 10)}x`\n"
                        f"📊 Position Size: `{exchange.get('position_size_percent', 5)}%`\n"
                        f"🤖 Auto-Trade: {'🟢 ON' if exchange.get('auto_trade', True) else '🔴 OFF'}\n\n"
                    )
                    
                except Exception as e:
                    logger.error(f"Balance error for {exchange['exchange_name']}: {e}")
                    exchange_name = Config.SUPPORTED_EXCHANGES[exchange['exchange_name']]['display_name']
                    balance_text += (
                        f"🏢 **{exchange_name}**\n"
                        f"❌ Error: `{str(e)[:50]}...`\n\n"
                    )
            
            balance_text += (
                f"💎 **TOTAL PORTFOLIO:** `{total_balance:,.2f} USDT`\n\n"
                f"🔴 **LIVE MAINNET TRADING**\n"
                f"⚠️ Real money at risk!"
            )
            
            await update.message.reply_text(balance_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in balance_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def subscribe_command(self, update: Update, context: CallbackContext):
        """Subscribe to trading signals"""
        try:
            user_id = update.effective_user.id
            db_user = self.user_model.get_user(user_id)
            
            if not db_user:
                await update.message.reply_text("❌ Please start the bot first with /start")
                return
            
            # Check if user has exchanges
            exchanges = self.exchange_model.get_user_exchanges(db_user['id'])
            if not exchanges:
                await update.message.reply_text(
                    "⚠️ **Connect an exchange first!**\n\n"
                    "You need at least one futures exchange connected.\n\n"
                    "Use /connect to link your trading account."
                )
                return
            
            # Update subscription
            self.user_model.update_subscription(db_user['id'], True, True)
            
            await update.message.reply_text(
                "✅ *SIGNAL SUBSCRIPTION ACTIVATED!* ✅\n\n"
                "🤖 **AUTO-TRADING ENABLED**\n"
                "You'll now receive professional trading signals and trades will execute automatically!\n\n"
                "📊 **What You'll Get:**\n"
                "• Instant signal notifications\n"
                "• Automatic trade execution\n"
                "• Real-time P&L updates\n"
                "• Risk management protection\n"
                "• Professional market analysis\n\n"
                "🔴 **LIVE TRADING ACTIVE** - Monitor your positions!",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in subscribe_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Show help"""
        help_text = (
            "📚 *AUTOMATED FUTURES TRADING BOT HELP* 📚\n\n"
            "🤖 **MAIN COMMANDS:**\n"
            "• `/start` - Dashboard and overview\n"
            "• `/connect` - Connect futures exchanges\n"
            "• `/balance` - Check account balances\n"
            "• `/subscribe` - Enable signal trading\n"
            "• `/help` - This help message\n\n"
            "🔗 **SUPPORTED EXCHANGES:**\n"
            "• Binance USDT-M Futures\n"
            "• Bybit USDT Perpetual\n"
            "• OKX Perpetual Futures\n"
            "• Bitget USDT-M Futures\n"
            "• MEXC Futures\n\n"
            "⚠️ **IMPORTANT:**\n"
            "• This bot trades with REAL MONEY\n"
            "• Only enable futures trading permissions\n"
            "• NEVER enable withdrawal permissions\n"
            "• Monitor your positions regularly\n\n"
            "🆘 **Support:** Contact admin for assistance"
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def callback_handler(self, update: Update, context: CallbackContext):
        """Handle all callback queries"""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            
            if data == "connect_exchange":
                await self._show_exchange_list(query)
            elif data.startswith('connect_'):
                exchange = data.split('_')[1]
                await self._handle_exchange_connection(query, exchange, context)
            else:
                await query.edit_message_text("Feature coming soon...")
                
        except Exception as e:
            logger.error(f"Error in callback_handler: {e}")
            try:
                await query.edit_message_text("❌ An error occurred. Please try again.")
            except:
                pass
    
    async def _show_exchange_list(self, query):
        """Show list of supported exchanges"""
        try:
            connect_text = (
                "🔗 *CONNECT FUTURES EXCHANGES* 🔗\n\n"
                "💰 **LIVE MAINNET TRADING**\n"
                "Select your futures exchange to connect:\n\n"
                "⚠️ **API REQUIREMENTS:**\n"
                "• ✅ Enable: Futures Trading, Read Account\n"
                "• ❌ Disable: Withdrawals (NEVER enable)\n"
                "• 🔒 Use IP restrictions if available\n\n"
                "🎯 **Supported Futures Exchanges:**"
            )
            
            keyboard = []
            for exchange_id, exchange_info in Config.SUPPORTED_EXCHANGES.items():
                keyboard.append([InlineKeyboardButton(
                    f"{exchange_info['display_name']} Futures",
                    callback_data=f"connect_{exchange_id}"
                )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(connect_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing exchange list: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def _handle_exchange_connection(self, query, exchange: str, context: CallbackContext):
        """Handle exchange connection setup"""
        try:
            # Check if exchange exists in supported exchanges
            if exchange not in Config.SUPPORTED_EXCHANGES:
                await query.edit_message_text(f"❌ Exchange '{exchange}' not supported.")
                return
                
            exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
            
            # Store selected exchange
            user_id = query.from_user.id
            self.user_sessions[user_id] = {'selected_exchange': exchange}
            
            setup_text = (
                f"🔐 *CONNECT {exchange_info['display_name']} FUTURES* 🔐\n\n"
                f"📋 **Setup Instructions:**\n\n"
                f"1️⃣ **Create API Key:**\n"
                f"   • Visit your {exchange_info['name']} account\n"
                f"   • Go to API Management\n"
                f"   • Create new API key\n\n"
                f"2️⃣ **Set Permissions:**\n"
                f"   ✅ Enable: Futures Trading, Read Account\n"
                f"   ❌ Disable: Withdrawals, Transfers\n\n"
                f"3️⃣ **Send Credentials:**\n"
            )
            
            if exchange_info['requires_passphrase']:
                setup_text += (
                    f"   Format: `API_KEY API_SECRET PASSPHRASE`\n"
                    f"   Example: `abc123 xyz789 mypass123`\n\n"
                )
            else:
                setup_text += (
                    f"   Format: `API_KEY API_SECRET`\n"
                    f"   Example: `abc123 xyz789`\n\n"
                )
            
            setup_text += (
                f"⚠️ **SECURITY:**\n"
                f"• LIVE MAINNET trading (real money)\n"
                f"• Your keys are encrypted\n"
                f"• NEVER enable withdrawals\n\n"
                f"🔒 **Ready?** Send your API credentials now:"
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    f"📚 {exchange_info['name']} API Guide",
                    url=exchange_info['guide_url']
                )],
                [InlineKeyboardButton(
                    "🔙 Choose Different Exchange",
                    callback_data="connect_exchange"
                )]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(setup_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in _handle_exchange_connection: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_credentials(self, update: Update, context: CallbackContext):
        """Handle API credential input"""
        try:
            user_id = update.effective_user.id
            
            # Get selected exchange
            session = self.user_sessions.get(user_id, {})
            exchange = session.get('selected_exchange')
            
            if not exchange:
                await update.message.reply_text("❌ Please start with /connect first")
                return
            
            credentials = update.message.text.split()
            exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
            
            # Validate format
            required_count = 3 if exchange_info['requires_passphrase'] else 2
            if len(credentials) < required_count:
                await update.message.reply_text(
                    f"❌ Invalid format. Please provide {required_count} values.\n\n"
                    f"Expected: {'API_KEY API_SECRET PASSPHRASE' if exchange_info['requires_passphrase'] else 'API_KEY API_SECRET'}"
                )
                return
            
            api_key = credentials[0]
            api_secret = credentials[1]
            passphrase = credentials[2] if len(credentials) > 2 else ''
            
            # Test connection
            await update.message.reply_text("🔄 Testing connection to LIVE exchange...")
            
            try:
                balance = await BalanceChecker.get_balance(exchange, api_key, api_secret, passphrase)
                
                # Encrypt and save
                encrypted_key, encrypted_secret, encrypted_passphrase = \
                    self.auth_manager.encrypt_credentials(api_key, api_secret, passphrase)
                
                db_user = self.user_model.get_user(user_id)
                if not db_user:
                    user_db_id = self.user_model.create_user(user_id)
                else:
                    user_db_id = db_user['id']
                
                self.exchange_model.add_exchange(
                    user_db_id, exchange, encrypted_key, encrypted_secret,
                    encrypted_passphrase, 'manual'
                )
                
                await update.message.reply_text(
                    f"✅ *{exchange_info['display_name']} CONNECTED!* ✅\n\n"
                    f"🔴 **LIVE MAINNET CONNECTION**\n"
                    f"💰 Current Balance: `{balance:,.2f} USDT`\n\n"
                    f"🤖 **Auto-Trading Ready!**\n"
                    f"Use /subscribe to enable signal trading.\n\n"
                    f"📊 **Next Steps:**\n"
                    f"• Check /balance for all accounts\n"
                    f"• Use /subscribe for signals\n"
                    f"• Monitor your positions regularly",
                    parse_mode='Markdown'
                )
                
                # Clear session
                self.user_sessions.pop(user_id, None)
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ **Connection Failed**\n\n"
                    f"Error: `{str(e)}`\n\n"
                    f"Please check:\n"
                    f"• API keys are correct\n"
                    f"• Futures trading enabled\n"
                    f"• No typos in credentials\n\n"
                    f"Try again with correct keys."
                )
                
        except Exception as e:
            logger.error(f"Error in handle_credentials: {e}")
            await update.message.reply_text("❌ Error processing credentials. Please try again.")
    
    # Placeholder methods for other commands
    async def portfolio_command(self, update: Update, context: CallbackContext):
        await update.message.reply_text("📊 Portfolio feature coming soon...")
    
    async def trades_command(self, update: Update, context: CallbackContext):
        await update.message.reply_text("📈 Trades feature coming soon...")
    
    async def settings_command(self, update: Update, context: CallbackContext):
        await update.message.reply_text("⚙️ Settings feature coming soon...")
    
    async def status_command(self, update: Update, context: CallbackContext):
        await update.message.reply_text("📊 Status feature coming soon...")
    
    async def pnl_command(self, update: Update, context: CallbackContext):
        await update.message.reply_text("📈 P&L feature coming soon...")
