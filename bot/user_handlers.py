import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.models import Database, UserModel, ExchangeModel, SignalModel, TradeModel
from exchanges.auth_manager import ExchangeAuthManager
from exchanges.balance_checker import BalanceChecker
from config.settings import Config
import os

logger = logging.getLogger(__name__)

class UserHandlers:
    def __init__(self):
        self.db = Database()
        self.user_model = UserModel(self.db)
        self.exchange_model = ExchangeModel(self.db)
        self.signal_model = SignalModel(self.db)
        self.trade_model = TradeModel(self.db)
        self.auth_manager = ExchangeAuthManager(Config.ENCRYPTION_KEY)
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Handle /start command"""
        try:
            user = update.effective_user
            
            # Create or get user
            db_user = self.user_model.get_user(user.id)
            if not db_user:
                self.user_model.create_user(user.id, user.username, user.first_name, user.last_name)
            
            welcome_text = (
                "🚀 *Welcome to Professional Futures Trading Bot!* 🚀\n\n"
                "💰 **LIVE MAINNET TRADING**\n"
                "Connect your real exchange accounts for automated futures trading with professional signals!\n\n"
                "✨ **Features:**\n"
                "• 🔗 9 Major Exchanges (Binance, Bybit, OKX, etc.)\n"
                "• 🤖 Automated trade execution\n"
                "• 📊 Real-time balance monitoring\n"
                "• 🛡️ Advanced risk management\n"
                "• 📈 Professional trading signals\n"
                "• 💎 Live mainnet trading\n\n"
                "🎯 **Quick Start:**\n"
                "1. Connect your exchange → /connect\n"
                "2. Subscribe to signals → /subscribe\n"
                "3. Check your balance → /balance\n"
                "4. View your trades → /trades\n\n"
                "⚠️ **IMPORTANT:** This bot trades with real money on mainnet exchanges.\n"
                "📚 Need help? Use /help for detailed guide"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("🔗 Connect Exchange", callback_data="quick_connect"),
                    InlineKeyboardButton("💰 View Balance", callback_data="quick_balance")
                ],
                [
                    InlineKeyboardButton("📈 Subscribe to Signals", callback_data="quick_subscribe"),
                    InlineKeyboardButton("📚 Help & Guide", callback_data="quick_help")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in start_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def connect_command(self, update: Update, context: CallbackContext):
        """Handle /connect command with futures exchanges"""
        try:
            keyboard = []
            
            # Add all futures exchanges in rows of 2
            exchanges = list(Config.SUPPORTED_EXCHANGES.items())
            for i in range(0, len(exchanges), 2):
                row = []
                for j in range(2):
                    if i + j < len(exchanges):
                        exchange_id, exchange_info = exchanges[i + j]
                        row.append(InlineKeyboardButton(
                            exchange_info['display_name'],
                            callback_data=f"manual_{exchange_id}"
                        ))
                keyboard.append(row)
            
            # Add guide button
            keyboard.append([InlineKeyboardButton("📚 Setup Guides", callback_data="exchange_guides")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            connect_text = (
                "🔗 *CONNECT YOUR FUTURES EXCHANGES* 🔗\n\n"
                "💰 **LIVE MAINNET TRADING**\n"
                "Select your exchange to connect API keys for real futures trading:\n\n"
                "⚠️ **SECURITY REQUIREMENTS:**\n"
                "• ✅ Enable: Futures Trading, Read Account\n"
                "• ❌ Disable: Withdrawals (NEVER enable)\n"
                "• 🔒 Use IP restrictions if available\n"
                "• 🛡️ All credentials are encrypted\n\n"
                "🎯 **Supported Futures Exchanges:**\n"
                "• Binance USDT-M Futures\n"
                "• Bybit USDT Perpetual\n"
                "• OKX Perpetual Futures\n"
                "• Bitget USDT-M Futures\n"
                "• MEXC Futures\n"
                "• KuCoin Futures\n"
                "• Gate.io Futures\n"
                "• Huobi Linear Swaps\n"
                "• BingX Perpetual Futures"
            )
            
            await update.message.reply_text(connect_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in connect_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def connection_callback(self, update: Update, context: CallbackContext):
        """Handle exchange connection callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
        
            if data.startswith('manual_'):
                exchange = data.split('_')[1]
                await self._handle_manual_connection(query, exchange, context)
            elif data.startswith('oauth_'):
                exchange = data.split('_')[1]
                await self._handle_oauth_connection(query, exchange, context)
            elif data == 'exchange_guides':
                await self._show_exchange_guides(query)
            elif data == 'quick_connect':
                # Show connection options
                await self._show_connection_options(query)
            elif data == 'quick_balance':
                fake_update = type('obj', (object,), {
                    'message': query.message,
                    'effective_user': query.from_user
                })()
                await self.balance_command(fake_update, context)
            elif data == 'quick_subscribe':
                fake_update = type('obj', (object,), {
                    'message': query.message,
                    'effective_user': query.from_user
                })()
                await self.subscribe_command(fake_update, context)
            elif data == 'quick_help':
                fake_update = type('obj', (object,), {
                    'message': query.message,
                    'effective_user': query.from_user
                })()
                await self.help_command(fake_update, context)
            
        except Exception as e:
            logger.error(f"Error in connection_callback: {e}")
            try:
                await query.edit_message_text("❌ An error occurred. Please try again.")
            except:
                pass

    async def _show_connection_options(self, query):
        """Show connection method options"""
        try:
            keyboard = []
        
            # OAuth supported exchanges
            oauth_exchanges = ['kucoin', 'bybit', 'okx']
            for exchange in oauth_exchanges:
                if exchange in Config.SUPPORTED_EXCHANGES:
                    exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🔗 {exchange_info['display_name']} (OAuth)",
                            callback_data=f"oauth_{exchange}"
                        ),
                        InlineKeyboardButton(
                            f"📝 {exchange_info['display_name']} (Manual)",
                            callback_data=f"manual_{exchange}"
                        )
                    ])
        
            # Manual only exchanges
            manual_only = ['binance', 'bitget', 'mexc', 'gate', 'huobi', 'bingx']
            for exchange in manual_only:
                if exchange in Config.SUPPORTED_EXCHANGES:
                    exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📝 {exchange_info['display_name']} (Manual)",
                            callback_data=f"manual_{exchange}"
                        )
                    ])
        
            keyboard.append([InlineKeyboardButton("📚 Setup Guides", callback_data="exchange_guides")])
        
            reply_markup = InlineKeyboardMarkup(keyboard)
        
            connect_text = (
                "🔗 *CHOOSE CONNECTION METHOD* 🔗\n\n"
                "💰 **LIVE MAINNET TRADING**\n\n"
                "🔗 **OAuth (Recommended):** Secure authorization without sharing API keys\n"
                "📝 **Manual:** Traditional API key input\n\n"
                "⚠️ **Security:** OAuth is more secure as you never share your API keys directly!"
            )
        
            await query.edit_message_text(connect_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        except Exception as e:
            logger.error(f"Error in _show_connection_options: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")

    async def _handle_oauth_connection(self, query, exchange: str, context: CallbackContext):
        """Handle OAuth connection"""
        try:
            user_id = query.from_user.id
            callback_url = os.getenv('OAUTH_CALLBACK_URL', 'https://yourdomain.com/oauth/callback')
        
            oauth_url = self.auth_manager.generate_oauth_url(exchange, user_id, callback_url)
        
            if oauth_url:
                keyboard = [[InlineKeyboardButton(
                    "🔗 Authorize Now",
                    url=oauth_url
                )]]
                reply_markup = InlineKeyboardMarkup(keyboard)
            
                exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
            
                await query.edit_message_text(
                    f"✅ *OAuth Authorization for {exchange_info['display_name']}*\n\n"
                    f"🔐 **SECURE OAUTH CONNECTION**\n\n"
                    f"Click the button below to securely authorize the connection.\n"
                    f"You'll be redirected back automatically after authorization.\n\n"
                    f"🛡️ **Benefits of OAuth:**\n"
                    f"• No need to share API keys\n"
                    f"• Revocable access\n"
                    f"• Enhanced security\n"
                    f"• Automatic token refresh",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await query.edit_message_text(
                    f"❌ OAuth not available for {Config.SUPPORTED_EXCHANGES[exchange]['display_name']}\n\n"
                    f"Please use manual API key connection instead."
                )
        except Exception as e:
            logger.error(f"OAuth error: {e}")
            await query.edit_message_text("❌ OAuth configuration error. Please try manual connection.")
    
    async def _handle_manual_connection(self, query, exchange: str, context: CallbackContext):
        """Handle manual API key connection"""
        try:
            exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
            
            # Store selected exchange in user data
            user_id = query.from_user.id
            if not hasattr(context, 'user_data'):
                context.user_data = {}
            context.user_data[user_id] = {'selected_exchange': exchange}
            
            guide_text = (
                f"🔐 *Connecting to {exchange_info['display_name']} FUTURES*\n\n"
                f"💰 **MAINNET LIVE TRADING SETUP**\n\n"
                f"📋 **Step-by-step setup:**\n\n"
                f"1️⃣ **Create API Key:**\n"
                f"   • Visit: [API Settings]({exchange_info['guide_url']})\n"
                f"   • Create new API key for futures trading\n\n"
                f"2️⃣ **Set Permissions (CRITICAL):**\n"
                f"   ✅ Enable: {', '.join(exchange_info['permissions_required'])}\n"
                f"   ❌ Disable: Withdrawals, Transfers (SECURITY)\n"
                f"   🔒 Add IP restrictions if available\n\n"
                f"3️⃣ **Send Credentials:**\n"
            )
            
            if exchange_info['requires_passphrase']:
                guide_text += (
                    f"   Send in format: `API_KEY API_SECRET PASSPHRASE`\n"
                    f"   Example: `abc123def456 xyz789uvw012 mypassphrase123`\n\n"
                )
            else:
                guide_text += (
                    f"   Send in format: `API_KEY API_SECRET`\n"
                    f"   Example: `abc123def456 xyz789uvw012`\n\n"
                )
            
            guide_text += (
                f"⚠️ **SECURITY WARNINGS:**\n"
                f"• This connects to LIVE MAINNET (real money)\n"
                f"• NEVER enable withdrawal permissions\n"
                f"• Your keys are encrypted with military-grade security\n"
                f"• You can disconnect anytime\n"
                f"• Start with small position sizes\n\n"
                f"🔒 **Ready for LIVE trading?** Send your credentials now:"
            )
            
            keyboard = [
                [InlineKeyboardButton("📚 Detailed Guide", url=exchange_info['guide_url'])],
                [InlineKeyboardButton("🔙 Back to Exchanges", callback_data="back_to_connect")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(guide_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in _handle_manual_connection: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def _show_exchange_guides(self, query):
        """Show detailed exchange setup guides"""
        try:
            guides_text = (
                "📚 *FUTURES TRADING SETUP GUIDES* 📚\n\n"
                "💰 **MAINNET LIVE TRADING**\n"
                "Click on your exchange for detailed API setup instructions:\n\n"
                "⚠️ **Remember:** Only enable futures trading permissions!\n\n"
            )
            
            keyboard = []
            for exchange_id, exchange_info in Config.SUPPORTED_EXCHANGES.items():
                keyboard.append([InlineKeyboardButton(
                    f"{exchange_info['display_name']} Futures API Guide",
                    url=exchange_info['guide_url']
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Connect", callback_data="back_to_connect")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(guides_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in _show_exchange_guides: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def balance_command(self, update: Update, context: CallbackContext):
        """Handle /balance command - LIVE MAINNET BALANCES"""
        try:
            user_id = update.effective_user.id
            db_user = self.user_model.get_user(user_id)
            
            if not db_user:
                await update.message.reply_text("❌ Please start the bot first with /start")
                return
            
            exchanges = self.exchange_model.get_user_exchanges(db_user['id'])
            
            if not exchanges:
                await update.message.reply_text(
                    "❌ No connected exchanges found.\n\n"
                    "Use /connect to link your futures trading accounts."
                )
                return
            
            await update.message.reply_text("🔄 Checking LIVE mainnet balances...")
            
            total_balance = 0
            balance_text = "💰 *YOUR LIVE FUTURES BALANCES* 💰\n\n"
            
            for exchange in exchanges:
                try:
                    # Decrypt credentials
                    api_key, api_secret, passphrase = self.auth_manager.decrypt_credentials(
                        exchange['api_key_encrypted'],
                        exchange['api_secret_encrypted'],
                        exchange['passphrase_encrypted']
                    )
                    
                    # Get LIVE balance
                    balance = await BalanceChecker.get_balance(
                        exchange['exchange_name'], api_key, api_secret, passphrase
                    )
                    
                    total_balance += balance
                    exchange_name = Config.SUPPORTED_EXCHANGES[exchange['exchange_name']]['display_name']
                    
                    balance_text += (
                        f"{exchange_name}\n"
                        f"💵 Balance: `{balance:,.2f} USDT`\n"
                        f"🔴 Mode: LIVE MAINNET\n"
                        f"⚡ Leverage: `{exchange['leverage']}x`\n"
                        f"📈 Position Size: `{exchange['position_size_percent']}%`\n\n"
                    )
                    
                except Exception as e:
                    logger.error(f"Balance error for {exchange['exchange_name']}: {e}")
                    exchange_name = Config.SUPPORTED_EXCHANGES[exchange['exchange_name']]['display_name']
                    balance_text += (
                        f"{exchange_name}\n"
                        f"❌ Error: `{str(e)[:50]}...`\n\n"
                    )
            
            balance_text += (
                f"💎 **Total Portfolio Value:** `{total_balance:,.2f} USDT`\n\n"
                f"🔴 **LIVE MAINNET TRADING ACTIVE**\n"
                f"⚠️ Real money at risk - trade responsibly!"
            )
            
            await update.message.reply_text(balance_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in balance_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def help_command(self, update: Update, context: CallbackContext):
        """Handle /help command with comprehensive guide"""
        try:
            help_text = (
                "📚 *PROFESSIONAL FUTURES TRADING BOT GUIDE* 📚\n\n"
                "💰 **LIVE MAINNET TRADING**\n\n"
                "🔗 **CONNECTING EXCHANGES**\n"
                "1. Use `/connect` to see all supported futures exchanges\n"
                "2. Follow the setup guide for your exchange\n"
                "3. Create API keys with ONLY futures trading permissions\n"
                "4. NEVER enable withdrawal permissions\n\n"
                "🔑 **SUPPORTED FUTURES EXCHANGES:**\n"
            )
            
            for exchange_id, exchange_info in Config.SUPPORTED_EXCHANGES.items():
                help_text += f"• {exchange_info['display_name']}\n"
            
            help_text += (
                "\n⚠️ **CRITICAL API PERMISSIONS:**\n"
                "✅ Enable: Futures Trading, Read Account\n"
                "❌ Disable: Withdrawals, Transfers, Sub-account\n"
                "🔒 Use IP restrictions when available\n\n"
                "🤖 **AUTO-TRADING FEATURES**\n"
                "• Signals executed automatically on LIVE accounts\n"
                "• Position size based on your balance percentage\n"
                "• Stop-loss and take-profit included\n"
                "• Advanced risk management\n"
                "• Real-time trade monitoring\n\n"
                "📊 **AVAILABLE COMMANDS**\n"
                "• `/start` - Welcome & quick actions\n"
                "• `/connect` - Connect futures exchange accounts\n"
                "• `/balance` - Check LIVE account balances\n"
                "• `/subscribe` - Subscribe to trading signals\n"
                "• `/trades` - View your trade history\n"
                "• `/settings` - Adjust trading preferences\n"
                "• `/help` - This comprehensive guide\n\n"
                "🛡️ **RISK MANAGEMENT**\n"
                "• Maximum 10% position size per trade\n"
                "• Built-in stop-loss protection\n"
                "• Leverage limits (1x-50x)\n"
                "• Daily trade limits\n"
                "• Real-time risk monitoring\n\n"
                "💡 **TRADING TIPS**\n"
                "1. Start with small position sizes (1-2%)\n"
                "2. Use conservative leverage (5-10x)\n"
                "3. Monitor your trades regularly\n"
                "4. Adjust settings based on performance\n"
                "5. NEVER risk more than you can afford to lose\n\n"
                "⚠️ **IMPORTANT WARNINGS**\n"
                "• This bot trades with REAL MONEY on mainnet\n"
                "• Cryptocurrency trading involves substantial risk\n"
                "• Past performance doesn't guarantee future results\n"
                "• Only trade with funds you can afford to lose\n\n"
                "🆘 **SUPPORT**\n"
                "Need help? Contact admin for assistance."
            )
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in help_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def subscribe_command(self, update: Update, context: CallbackContext):
        """Handle /subscribe command"""
        try:
            user_id = update.effective_user.id
            db_user = self.user_model.get_user(user_id)
            
            if not db_user:
                await update.message.reply_text("❌ Please start the bot first with /start")
                return
            
            # Check if user has connected exchanges
            exchanges = self.exchange_model.get_user_exchanges(db_user['id'])
            if not exchanges:
                await update.message.reply_text(
                    "⚠️ **Connect an exchange first!**\n\n"
                    "You need to connect at least one futures exchange before subscribing to signals.\n\n"
                    "Use /connect to link your trading account."
                )
                return
            
            # Update subscription status
            conn = self.db.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE subscriptions SET is_subscribed = 1 WHERE user_id = ?",
                (db_user['id'],)
            )
            conn.commit()
            conn.close()
            
            await update.message.reply_text(
                "✅ *LIVE TRADING SUBSCRIPTION ACTIVATED!*\n\n"
                "🔴 **MAINNET TRADING ENABLED**\n"
                "You'll now receive all trading signals and trades will be executed automatically on your connected exchanges.\n\n"
                "⚠️ **IMPORTANT:** This involves real money trading. Monitor your positions regularly!",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in subscribe_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def trades_command(self, update: Update, context: CallbackContext):
        """Handle /trades command"""
        try:
            user_id = update.effective_user.id
            db_user = self.user_model.get_user(user_id)
            
            if not db_user:
                await update.message.reply_text("❌ Please start the bot first with /start")
                return
            
            trades = self.trade_model.get_user_trades(db_user['id'], limit=10)
            
            if not trades:
                await update.message.reply_text(
                    "📈 *LIVE TRADING HISTORY*\n\n"
                    "No trades executed yet.\n\n"
                    "Connect your exchange and subscribe to signals to start automated futures trading!"
                )
                return
            
            trades_text = "📈 *YOUR LIVE FUTURES TRADES* 📈\n\n"
            
            for i, trade in enumerate(trades, 1):
                pnl = trade['pnl'] or 0
                status_emoji = "🟢" if pnl > 0 else "🔴" if pnl < 0 else "🟡"
                
                trades_text += (
                    f"{i}. {status_emoji} **{trade['symbol']}** ({trade['side']})\n"
                    f"   💰 Entry: `${trade['entry_price']:,.2f}`\n"
                    f"   📊 Size: `{trade['quantity']:.4f}`\n"
                    f"   💹 PnL: `{pnl:+.2f} USDT`\n"
                    f"   🏢 Exchange: {trade['exchange_name'].title()}\n"
                    f"   📅 {trade['executed_at'][:16]}\n\n"
                )
            
            trades_text += "🔴 **LIVE MAINNET TRADING ACTIVE**"
            
            await update.message.reply_text(trades_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in trades_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def settings_command(self, update: Update, context: CallbackContext):
        """Handle /settings command"""
        try:
            await update.message.reply_text(
                "⚙️ *LIVE TRADING SETTINGS*\n\n"
                "🔴 **MAINNET TRADING ACTIVE**\n\n"
                "Settings panel coming soon...\n"
                "For now, use /subscribe to enable live trading signals.\n\n"
                "⚠️ **Current defaults:**\n"
                "• Position size: 5% per trade\n"
                "• Leverage: 10x\n"
                "• Auto-trading: Enabled",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error in settings_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_credentials(self, update: Update, context: CallbackContext):
        """Handle manual credential input"""
        try:
            user_id = update.effective_user.id
            
            # Get selected exchange from context
            user_data = getattr(context, 'user_data', {})
            exchange = user_data.get(user_id, {}).get('selected_exchange')
            
            if not exchange:
                await update.message.reply_text("❌ Please start with /connect first")
                return
            
            credentials = update.message.text.split()
            exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
            
            # Validate credential count
            required_count = 3 if exchange_info['requires_passphrase'] else 2
            if len(credentials) < required_count:
                await update.message.reply_text(
                    f"❌ Invalid format. Please provide {required_count} values.\n\n"
                    f"Expected format: {'API_KEY API_SECRET PASSPHRASE' if exchange_info['requires_passphrase'] else 'API_KEY API_SECRET'}"
                )
                return
            
            api_key = credentials[0]
            api_secret = credentials[1]
            passphrase = credentials[2] if len(credentials) > 2 else ''
            
            # Test the connection first
            await update.message.reply_text("🔄 Testing connection to LIVE exchange...")
            
            try:
                test_balance = await BalanceChecker.get_balance(exchange, api_key, api_secret, passphrase)
                
                # Encrypt credentials
                encrypted_key, encrypted_secret, encrypted_passphrase = \
                    self.auth_manager.encrypt_credentials(api_key, api_secret, passphrase)
                
                # Get user ID from database
                db_user = self.user_model.get_user(user_id)
                if not db_user:
                    await update.message.reply_text("❌ Please start the bot first with /start")
                    return
                
                # Save to database
                self.exchange_model.add_exchange(
                    db_user['id'], exchange, encrypted_key, encrypted_secret,
                    encrypted_passphrase, 'manual'
                )
                
                await update.message.reply_text(
                    f"✅ *{exchange_info['display_name']} CONNECTED SUCCESSFULLY!*\n\n"
                    f"🔴 **LIVE MAINNET CONNECTION**\n"
                    f"💰 Current Balance: `{test_balance:,.2f} USDT`\n\n"
                    f"Your exchange is now connected for live futures trading!\n\n"
                    f"Next steps:\n"
                    f"• Use /subscribe to enable trading signals\n"
                    f"• Use /balance to check all balances\n"
                    f"• Monitor your trades with /trades",
                    parse_mode='Markdown'
                )
                
                # Clear user data
                if hasattr(context, 'user_data') and user_id in context.user_data:
                    context.user_data.pop(user_id, None)
                    
            except Exception as e:
                await update.message.reply_text(
                    f"❌ **Connection Failed**\n\n"
                    f"Error: `{str(e)}`\n\n"
                    f"Please check:\n"
                    f"• API keys are correct\n"
                    f"• Futures trading is enabled\n"
                    f"• IP restrictions (if any)\n"
                    f"• Exchange API status\n\n"
                    f"Try again with correct credentials."
                )
                
        except Exception as e:
            logger.error(f"Credential handling error: {e}")
            await update.message.reply_text("❌ Error processing credentials. Please try again.")
