import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from exchanges.easy_connect import EasyConnectManager, UserProfiler, LiveSupportManager
from exchanges.balance_checker import BalanceChecker
from config.settings import Config
from database.models import UserModel, ExchangeModel

logger = logging.getLogger(__name__)

class EasyConnectHandlers:
    """Enhanced handlers for easy exchange connection"""
    
    def __init__(self, db, auth_manager):
        self.db = db
        self.auth_manager = auth_manager
        self.user_model = UserModel(db)
        self.exchange_model = ExchangeModel(db)
        self.easy_connect = EasyConnectManager(auth_manager, db)
        self.profiler = UserProfiler()
        self.support = LiveSupportManager()
        self.user_sessions = {}  # Store user session data
    
    async def start_easy_connect(self, update: Update, context: CallbackContext):
        """Start the easy connect process"""
        try:
            user_id = update.effective_user.id
            
            # Initialize user session
            self.user_sessions[user_id] = {
                'step': 'profiling',
                'profile_answers': {},
                'current_question': 0
            }
            
            welcome_text = (
                "🚀 *Welcome to Easy Connect!* 🚀\n\n"
                "Let's get you connected to start trading in just a few minutes!\n\n"
                "First, let me ask you 3 quick questions to recommend the best setup for you.\n\n"
                "This will take less than 30 seconds! 😊"
            )
            
            # Start with first profiling question
            questions = self.profiler.get_profiling_questions()
            first_question = questions[0]
            
            keyboard = self.profiler.create_question_keyboard(first_question)
            
            await update.message.reply_text(
                welcome_text + f"\n\n**Question 1/3:**\n{first_question['question']}",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in start_easy_connect: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_profile_answer(self, update: Update, context: CallbackContext):
        """Handle profiling question answers"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data.split('_')  # profile_question_id_answer
            
            if len(data) != 3 or data[0] != 'profile':
                return
            
            question_id = data[1]
            answer = data[2]
            
            # Store answer
            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = {'profile_answers': {}, 'current_question': 0}
            
            self.user_sessions[user_id]['profile_answers'][question_id] = answer
            self.user_sessions[user_id]['current_question'] += 1
            
            questions = self.profiler.get_profiling_questions()
            current_q = self.user_sessions[user_id]['current_question']
            
            if current_q < len(questions):
                # Show next question
                next_question = questions[current_q]
                keyboard = self.profiler.create_question_keyboard(next_question)
                
                await query.edit_message_text(
                    f"**Question {current_q + 1}/{len(questions)}:**\n{next_question['question']}",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                # Profiling complete, show recommendations
                await self.show_recommendations(query, user_id)
                
        except Exception as e:
            logger.error(f"Error in handle_profile_answer: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_recommendations(self, query, user_id: int):
        """Show personalized recommendations based on profile"""
        try:
            answers = self.user_sessions[user_id]['profile_answers']
            user_level = self.easy_connect.assess_user_level(answers)
            recommended_exchange = self.easy_connect.get_recommended_exchange(user_level)
            safe_settings = self.easy_connect.get_safe_settings(user_level)
            
            # Create recommendation text
            level_descriptions = {
                'beginner': '🆕 **Beginner Trader**',
                'intermediate': '📈 **Intermediate Trader**',
                'advanced': '💎 **Advanced Trader**'
            }
            
            exchange_info = Config.SUPPORTED_EXCHANGES[recommended_exchange]
            
            recommendation_text = (
                f"✅ **Profile Complete!**\n\n"
                f"{level_descriptions[user_level]}\n\n"
                f"🎯 **Perfect Exchange for You:**\n"
                f"{exchange_info['display_name']} {exchange_info['name']}\n\n"
                f"🛡️ **Your Safe Settings:**\n"
                f"• Leverage: {safe_settings['leverage']}x (conservative)\n"
                f"• Position Size: {safe_settings['position_size']}% per trade\n"
                f"• Stop Loss: {'✅ Enabled' if safe_settings['stop_loss'] else '❌ Disabled'}\n"
                f"• Take Profit: {'✅ Enabled' if safe_settings['take_profit'] else '❌ Disabled'}\n\n"
                f"🚀 **Ready to connect?** Choose your preferred method:"
            )
            
            keyboard = self.easy_connect.create_connection_keyboard(recommended_exchange, user_level)
            
            await query.edit_message_text(
                recommendation_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
            # Store recommendation in session
            self.user_sessions[user_id].update({
                'step': 'connection',
                'recommended_exchange': recommended_exchange,
                'user_level': user_level,
                'safe_settings': safe_settings
            })
            
        except Exception as e:
            logger.error(f"Error in show_recommendations: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_connection_method(self, update: Update, context: CallbackContext):
        """Handle connection method selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = query.from_user.id
            data = query.data
            
            if data.startswith('auto_connect_'):
                exchange = data.split('_')[2]
                await self.handle_auto_connect(query, user_id, exchange)
                
            elif data.startswith('guided_setup_'):
                exchange = data.split('_')[2]
                await self.handle_guided_setup(query, user_id, exchange)
                
            elif data.startswith('mobile_setup_'):
                exchange = data.split('_')[2]
                await self.handle_mobile_setup(query, user_id, exchange)
                
            elif data.startswith('live_help_'):
                exchange = data.split('_')[2]
                await self.handle_live_help(query, user_id, exchange)
                
            elif data == 'back_to_exchanges':
                await self.show_exchange_selection(query, user_id)
                
        except Exception as e:
            logger.error(f"Error in handle_connection_method: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_auto_connect(self, query, user_id: int, exchange: str):
        """Handle automatic connection"""
        try:
            if not self.easy_connect.can_auto_connect(exchange):
                await query.edit_message_text(
                    "❌ Auto-connect not available for this exchange.\n\n"
                    "Please choose the guided setup option instead."
                )
                return
            
            await query.edit_message_text(
                "🤖 **Auto-connecting...**\n\n"
                "⏳ Generating secure API keys...\n"
                "🔒 Setting up safe permissions...\n"
                "🧪 Testing connection...\n\n"
                "This will take about 30 seconds..."
            )
            
            # Perform auto-connection
            result = await self.easy_connect.auto_connect_exchange(user_id, exchange)
            
            if result['success']:
                # Test the connection
                try:
                    balance = await BalanceChecker.get_balance(
                        exchange, result['api_key'], result['secret_key'], ''
                    )
                    success_msg = self.easy_connect.get_success_message(exchange, 'auto', balance)
                except:
                    success_msg = self.easy_connect.get_success_message(exchange, 'auto')
                
                await query.edit_message_text(success_msg, parse_mode='Markdown')
            else:
                await query.edit_message_text(
                    f"❌ **Auto-connect failed**\n\n"
                    f"Error: {result['error']}\n\n"
                    f"Please try the guided setup option instead."
                )
                
        except Exception as e:
            logger.error(f"Error in handle_auto_connect: {e}")
            await query.edit_message_text("❌ Auto-connect failed. Please try guided setup.")
    
    async def handle_guided_setup(self, query, user_id: int, exchange: str):
        """Handle guided step-by-step setup"""
        try:
            user_level = self.user_sessions.get(user_id, {}).get('user_level', 'beginner')
            steps = self.easy_connect.get_step_by_step_guide(exchange, user_level)
            
            if not steps:
                await query.edit_message_text("❌ Guided setup not available for this exchange.")
                return
            
            # Store setup session
            self.user_sessions[user_id].update({
                'setup_method': 'guided',
                'setup_exchange': exchange,
                'setup_steps': steps,
                'current_step': 0
            })
            
            # Show first step
            await self.show_setup_step(query, user_id, 0)
            
        except Exception as e:
            logger.error(f"Error in handle_guided_setup: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_setup_step(self, query, user_id: int, step_index: int):
        """Show a specific setup step"""
        try:
            session = self.user_sessions[user_id]
            steps = session['setup_steps']
            
            if step_index >= len(steps):
                # Setup complete, wait for credentials
                await self.wait_for_credentials(query, user_id)
                return
            
            step = steps[step_index]
            
            step_text = (
                f"📋 **Step {step['step']}/{len(steps)}: {step['title']}**\n\n"
                f"{step['description']}\n\n"
                f"💡 **Tips:**\n"
            )
            
            for tip in step['tips']:
                step_text += f"• {tip}\n"
            
            # Create navigation keyboard
            keyboard = []
            
            if step_index > 0:
                keyboard.append([InlineKeyboardButton(
                    "⬅️ Previous Step",
                    callback_data=f"step_prev_{step_index}"
                )])
            
            if step_index < len(steps) - 1:
                keyboard.append([InlineKeyboardButton(
                    "➡️ Next Step",
                    callback_data=f"step_next_{step_index}"
                )])
            else:
                keyboard.append([InlineKeyboardButton(
                    "✅ I've Got My Keys",
                    callback_data="step_complete"
                )])
            
            keyboard.append([InlineKeyboardButton(
                "🆘 Need Help?",
                callback_data=f"step_help_{step_index}"
            )])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                step_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in show_setup_step: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def wait_for_credentials(self, query, user_id: int):
        """Wait for user to send credentials"""
        try:
            session = self.user_sessions[user_id]
            exchange = session['setup_exchange']
            exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
            
            credential_text = (
                f"🔑 **Almost Done!**\n\n"
                f"Now send me your API credentials in this format:\n\n"
            )
            
            if exchange_info['requires_passphrase']:
                credential_text += (
                    f"📝 **Format:** `API_KEY API_SECRET PASSPHRASE`\n\n"
                    f"**Example:**\n"
                    f"`abc123def456 xyz789uvw012 mypassphrase123`"
                )
            else:
                credential_text += (
                    f"📝 **Format:** `API_KEY API_SECRET`\n\n"
                    f"**Example:**\n"
                    f"`abc123def456 xyz789uvw012`"
                )
            
            credential_text += (
                f"\n\n⚠️ **Important:**\n"
                f"• Send both keys in ONE message\n"
                f"• Separate them with a SPACE\n"
                f"• Don't include any other text\n\n"
                f"🔒 Your keys will be encrypted and stored securely!"
            )
            
            # Update session to expect credentials
            self.user_sessions[user_id]['step'] = 'waiting_credentials'
            
            await query.edit_message_text(credential_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in wait_for_credentials: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_mobile_setup(self, query, user_id: int, exchange: str):
        """Handle mobile-specific setup"""
        try:
            mobile_guide_url = self.easy_connect.get_mobile_guide_url(exchange)
            
            mobile_text = (
                f"📱 **Mobile Setup for {exchange.title()}**\n\n"
                f"🎯 **Quick Mobile Steps:**\n"
                f"1. Download the official {exchange.title()} app\n"
                f"2. Create API keys in the app\n"
                f"3. Take screenshots of your keys\n"
                f"4. Send them to this bot\n\n"
                f"📚 **Detailed Mobile Guide:**\n"
                f"Tap the button below for step-by-step mobile instructions."
            )
            
            keyboard = [
                [InlineKeyboardButton(
                    f"📱 Open {exchange.title()} Mobile Guide",
                    url=mobile_guide_url
                )],
                [InlineKeyboardButton(
                    "📋 Switch to Desktop Guide",
                    callback_data=f"guided_setup_{exchange}"
                )],
                [InlineKeyboardButton(
                    "🔙 Back to Options",
                    callback_data="back_to_connection_methods"
                )]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                mobile_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Update session
            self.user_sessions[user_id].update({
                'setup_method': 'mobile',
                'setup_exchange': exchange,
                'step': 'waiting_credentials'
            })
            
        except Exception as e:
            logger.error(f"Error in handle_mobile_setup: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_live_help(self, query, user_id: int, exchange: str):
        """Handle live support request"""
        try:
            support_text = (
                f"🆘 **Live Support for {exchange.title()}**\n\n"
                f"Our support team is here to help you connect your exchange!\n\n"
                f"Choose your preferred support method:"
            )
            
            keyboard = self.support.get_support_keyboard(exchange)
            
            await query.edit_message_text(
                support_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in handle_live_help: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def process_easy_credentials(self, update: Update, context: CallbackContext):
        """Process credentials sent during easy connect"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is in credential waiting state
            session = self.user_sessions.get(user_id, {})
            if session.get('step') != 'waiting_credentials':
                return False  # Not in easy connect flow
            
            exchange = session.get('setup_exchange')
            if not exchange:
                return False
            
            # Process the credentials
            credentials = update.message.text.split()
            exchange_info = Config.SUPPORTED_EXCHANGES[exchange]
            
            # Validate format
            required_count = 3 if exchange_info['requires_passphrase'] else 2
            if len(credentials) < required_count:
                await update.message.reply_text(
                    f"❌ **Wrong format!**\n\n"
                    f"Please send exactly {required_count} values separated by spaces.\n\n"
                    f"Expected: {'API_KEY API_SECRET PASSPHRASE' if exchange_info['requires_passphrase'] else 'API_KEY API_SECRET'}"
                )
                return True
            
            api_key = credentials[0]
            api_secret = credentials[1]
            passphrase = credentials[2] if len(credentials) > 2 else ''
            
            # Test connection
            await update.message.reply_text("🔄 Testing your connection...")
            
            try:
                balance = await BalanceChecker.get_balance(exchange, api_key, api_secret, passphrase)
                
                # Save to database
                encrypted_key, encrypted_secret, encrypted_passphrase = \
                    self.auth_manager.encrypt_credentials(api_key, api_secret, passphrase)
                
                db_user = self.user_model.get_user(user_id)
                if not db_user:
                    db_user_id = self.user_model.create_user(user_id)
                else:
                    db_user_id = db_user['id']
                
                # Apply safe settings from profile
                safe_settings = session.get('safe_settings', {})
                
                self.exchange_model.add_exchange(
                    db_user_id, exchange, encrypted_key, encrypted_secret,
                    encrypted_passphrase, 'easy_connect',
                    safe_settings.get('leverage', 10)
                )
                
                # Success!
                method = session.get('setup_method', 'guided')
                success_msg = self.easy_connect.get_success_message(exchange, method, balance)
                
                await update.message.reply_text(success_msg, parse_mode='Markdown')
                
                # Clean up session
                self.user_sessions.pop(user_id, None)
                
                return True
                
            except Exception as e:
                await update.message.reply_text(
                    f"❌ **Connection Test Failed**\n\n"
                    f"Error: `{str(e)}`\n\n"
                    f"Please check:\n"
                    f"• API keys are correct\n"
                    f"• Futures trading is enabled\n"
                    f"• No typos in the keys\n\n"
                    f"Try sending your keys again."
                )
                return True
                
        except Exception as e:
            logger.error(f"Error in process_easy_credentials: {e}")
            await update.message.reply_text("❌ An error occurred processing your credentials.")
            return True
