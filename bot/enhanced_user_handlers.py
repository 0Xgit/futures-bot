import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot.user_handlers import UserHandlers
from bot.easy_connect_handlers import EasyConnectHandlers

logger = logging.getLogger(__name__)

class EnhancedUserHandlers(UserHandlers):
    """Enhanced user handlers with easy connect integration"""
    
    def __init__(self):
        super().__init__()
        self.easy_connect_handlers = EasyConnectHandlers(self.db, self.auth_manager)
    
    async def start_command(self, update: Update, context: CallbackContext):
        """Enhanced start command with easy connect option"""
        try:
            user = update.effective_user
            
            # Create or get user
            db_user = self.user_model.get_user(user.id)
            if not db_user:
                self.user_model.create_user(user.id, user.username, user.first_name, user.last_name)
            
            # Check if user has exchanges
            exchanges = self.exchange_model.get_user_exchanges(db_user['id'] if db_user else None)
            
            if not exchanges:
                # New user - show easy connect
                welcome_text = (
                    "🚀 *Welcome to Professional Futures Trading Bot!* 🚀\n\n"
                    "💰 **LIVE MAINNET TRADING**\n"
                    "Get started with automated futures trading in just 2 minutes!\n\n"
                    "✨ **What You'll Get:**\n"
                    "• 🤖 Automated trade execution\n"
                    "• 📊 Professional trading signals\n"
                    "• 🛡️ Advanced risk management\n"
                    "• 💎 Live mainnet trading\n"
                    "• 🔗 9 Major exchanges supported\n\n"
                    "🎯 **Choose Your Setup Method:**"
                )
                
                keyboard = [
                    [InlineKeyboardButton(
                        "🚀 Easy Connect (2 minutes)",
                        callback_data="start_easy_connect"
                    )],
                    [InlineKeyboardButton(
                        "⚙️ Advanced Setup",
                        callback_data="start_advanced_setup"
                    )],
                    [InlineKeyboardButton(
                        "📚 Learn More First",
                        callback_data="learn_more"
                    )]
                ]
            else:
                # Returning user - show dashboard
                total_exchanges = len(exchanges)
                welcome_text = (
                    f"👋 *Welcome back!*\n\n"
                    f"📊 **Your Trading Dashboard:**\n"
                    f"• Connected Exchanges: `{total_exchanges}`\n"
                    f"• Status: 🔴 LIVE TRADING ACTIVE\n\n"
                    f"🎯 **Quick Actions:**"
                )
                
                keyboard = [
                    [
                        InlineKeyboardButton("💰 Check Balance", callback_data="quick_balance"),
                        InlineKeyboardButton("📈 View Trades", callback_data="quick_trades")
                    ],
                    [
                        InlineKeyboardButton("🔗 Add Exchange", callback_data="start_easy_connect"),
                        InlineKeyboardButton("⚙️ Settings", callback_data="quick_settings")
                    ],
                    [
                        InlineKeyboardButton("📊 Subscribe to Signals", callback_data="quick_subscribe")
                    ]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in enhanced start_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def connection_callback(self, update: Update, context: CallbackContext):
        """Enhanced connection callback with easy connect support"""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            
            # Easy connect callbacks
            if data == "start_easy_connect":
                await self.easy_connect_handlers.start_easy_connect(
                    type('obj', (object,), {'message': query.message, 'effective_user': query.from_user})(),
                    context
                )
                return
            
            elif data == "start_advanced_setup":
                # Show traditional exchange selection
                await self._show_advanced_setup(query)
                return
            
            elif data == "learn_more":
                await self._show_learn_more(query)
                return
            
            elif data.startswith('profile_'):
                await self.easy_connect_handlers.handle_profile_answer(
                    type('obj', (object,), {'callback_query': query})(),
                    context
                )
                return
            
            elif data.startswith(('auto_connect_', 'guided_setup_', 'mobile_setup_', 'live_help_')):
                await self.easy_connect_handlers.handle_connection_method(
                    type('obj', (object,), {'callback_query': query})(),
                    context
                )
                return
            
            elif data.startswith('step_'):
                await self._handle_step_navigation(query, context)
                return
            
            # Handle other callbacks from parent class
            await super().connection_callback(update, context)
            
        except Exception as e:
            logger.error(f"Error in enhanced connection_callback: {e}")
            try:
                await query.edit_message_text("❌ An error occurred. Please try again.")
            except:
                pass
    
    async def _show_advanced_setup(self, query):
        """Show advanced setup options"""
        try:
            advanced_text = (
                "⚙️ *Advanced Setup*\n\n"
                "For experienced users who prefer manual configuration.\n\n"
                "🔗 **Supported Exchanges:**"
            )
            
            keyboard = []
            for exchange_id, exchange_info in Config.SUPPORTED_EXCHANGES.items():
                keyboard.append([InlineKeyboardButton(
                    exchange_info['display_name'],
                    callback_data=f"manual_{exchange_id}"
                )])
            
            keyboard.append([InlineKeyboardButton(
                "🔙 Back to Easy Connect",
                callback_data="start_easy_connect"
            )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(advanced_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in _show_advanced_setup: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def _show_learn_more(self, query):
        """Show educational content"""
        try:
            learn_text = (
                "📚 *Learn About Futures Trading*\n\n"
                "🎯 **What is Futures Trading?**\n"
                "Trade cryptocurrency contracts with leverage to amplify profits (and risks).\n\n"
                "🛡️ **Safety Features:**\n"
                "• Automatic stop-loss protection\n"
                "• Position size limits\n"
                "• Risk management tools\n"
                "• Professional signals\n\n"
                "⚠️ **Important Warnings:**\n"
                "• High risk, high reward\n"
                "• Only trade what you can afford to lose\n"
                "• Start with small positions\n"
                "• This bot uses real money\n\n"
                "🚀 **Ready to start?**"
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    "🚀 Yes, Let's Connect!",
                    callback_data="start_easy_connect"
                )],
                [InlineKeyboardButton(
                    "📖 Read More Guides",
                    url="https://your-domain.com/trading-guide"
                )],
                [InlineKeyboardButton(
                    "🔙 Back to Start",
                    callback_data="back_to_start"
                )]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(learn_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in _show_learn_more: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_credentials(self, update: Update, context: CallbackContext):
        """Enhanced credential handling with easy connect support"""
        try:
            # First try easy connect processing
            if await self.easy_connect_handlers.process_easy_credentials(update, context):
                return  # Handled by easy connect
            
            # Fall back to traditional processing
            await super().handle_credentials(update, context)
            
        except Exception as e:
            logger.error(f"Error in enhanced handle_credentials: {e}")
            await update.message.reply_text("❌ An error occurred processing your credentials.")
