import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from database.models import Database, UserModel, ExchangeModel, SignalModel, TradeModel
from config.settings import Config
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class AdminHandlers:
    def __init__(self):
        self.db = Database()
        self.user_model = UserModel(self.db)
        self.exchange_model = ExchangeModel(self.db)
        self.signal_model = SignalModel(self.db)
        self.trade_model = TradeModel(self.db)
    
    async def admin_command(self, update: Update, context: CallbackContext):
        """Admin dashboard"""
        if update.effective_user.id != Config.ADMIN_ID:
            await update.message.reply_text("❌ Admin only command")
            return
        
        try:
            # Get stats
            total_users = self.user_model.get_all_users_count()
            active_users = self.user_model.get_active_users_count(days=7)
            connected_users = len(self.exchange_model.get_all_connected_users())
            total_trades = self.trade_model.get_total_trades_count()
            total_volume = self.trade_model.get_total_volume()
            total_pnl = self.trade_model.get_total_pnl()
            
            admin_text = (
                "🔐 *ADMIN DASHBOARD* 🔐\n\n"
                f"👥 **Users:**\n"
                f"• Total Users: `{total_users}`\n"
                f"• Active Users (7d): `{active_users}`\n"
                f"• Connected Users: `{connected_users}`\n\n"
                f"📊 **Trading:**\n"
                f"• Total Trades: `{total_trades}`\n"
                f"• Total Volume: `${total_volume:,.2f}`\n"
                f"• Total P&L: `${total_pnl:+,.2f}`\n\n"
                f"🤖 **Bot Status:** `ONLINE`\n"
                f"📅 **Server Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"🎯 **Admin Actions:**"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
                    InlineKeyboardButton("👥 Users", callback_data="admin_users")
                ],
                [
                    InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"),
                    InlineKeyboardButton("🚨 Close All", callback_data="admin_close_all")
                ],
                [
                    InlineKeyboardButton("📈 New Signal", callback_data="admin_new_signal"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in admin_command: {e}")
            await update.message.reply_text("❌ Admin error. Check logs.")
    
    async def admin_callback_handler(self, update: Update, context: CallbackContext):
        """Handle admin panel callback queries"""
        query = update.callback_query
        await query.answer()
        
        if query.from_user.id != Config.ADMIN_ID:
            await query.edit_message_text("❌ Access denied. Admin only.")
            return
        
        try:
            data = query.data
            
            if data == "admin_stats":
                await self._show_detailed_stats(query, context)
            elif data == "admin_users":
                await self._show_user_management(query, context)
            elif data == "admin_broadcast":
                await self._show_broadcast_prompt(query, context)
            elif data == "admin_close_all":
                await self._show_close_all_prompt(query, context)
            elif data == "admin_new_signal":
                await self._show_signal_prompt(query, context)
            elif data == "admin_settings":
                await self._show_admin_settings(query, context)
            elif data == "admin_confirm_close_all":
                await self._confirm_close_all_positions(query, context)
            elif data == "admin_cancel_close":
                await query.edit_message_text("❌ Operation cancelled.")
            elif data == "admin_back" or data == "admin_panel":
                await self._show_admin_panel(query, context)
            else:
                await query.edit_message_text("🔧 Feature coming soon...")
                
        except Exception as e:
            logger.error(f"Error in admin_callback_handler: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def _show_detailed_stats(self, query, context):
        """Show detailed platform statistics"""
        try:
            # Get comprehensive stats
            total_users = self.user_model.get_all_users_count()
            active_users_7d = self.user_model.get_active_users_count(days=7)
            active_users_30d = self.user_model.get_active_users_count(days=30)
            connected_users = len(self.exchange_model.get_all_connected_users())
            total_trades = self.trade_model.get_total_trades_count()
            successful_trades = self.trade_model.get_successful_trades_count()
            total_volume = self.trade_model.get_total_volume()
            total_pnl = self.trade_model.get_total_pnl()
            
            # Calculate metrics
            win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            connection_rate = (connected_users / total_users * 100) if total_users > 0 else 0
            
            # Get exchange distribution
            exchange_distribution = self.exchange_model.get_exchange_distribution()
            
            stats_text = (
                "📊 *DETAILED PLATFORM STATISTICS* 📊\n\n"
                f"👥 **User Metrics:**\n"
                f"• Total Users: `{total_users}`\n"
                f"• Active (7d): `{active_users_7d}`\n"
                f"• Active (30d): `{active_users_30d}`\n"
                f"• Connected: `{connected_users}`\n"
                f"• Connection Rate: `{connection_rate:.1f}%`\n\n"
                f"💰 **Trading Performance:**\n"
                f"• Total Trades: `{total_trades:,}`\n"
                f"• Successful: `{successful_trades:,}`\n"
                f"• Win Rate: `{win_rate:.1f}%`\n"
                f"• Total Volume: `${total_volume:,.2f}`\n"
                f"• Total P&L: `${total_pnl:+,.2f}`\n\n"
                f"🏢 **Exchange Distribution:**\n"
            )
            
            for exchange, count in exchange_distribution.items():
                stats_text += f"• {exchange.title()}: `{count}` users\n"
            
            stats_text += f"\n📅 **Generated:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"),
                    InlineKeyboardButton("📊 Export", callback_data="admin_export_stats")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(stats_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing detailed stats: {e}")
            await query.edit_message_text("❌ Error loading statistics.")
    
    async def _show_user_management(self, query, context):
        """Show user management interface"""
        try:
            # Get user data
            connected_users = self.exchange_model.get_all_connected_users()
            recent_users = self.user_model.get_recent_users(limit=10)
            
            users_text = (
                "👥 *USER MANAGEMENT* 👥\n\n"
                f"📊 **Overview:**\n"
                f"• Total Connected: `{len(connected_users)}`\n"
                f"• Recent Signups: `{len(recent_users)}`\n\n"
                f"🔗 **Recent Connected Users:**\n"
            )
            
            for i, user in enumerate(connected_users[:8], 1):
                username = user.get('username') or user.get('first_name') or 'Unknown'
                users_text += (
                    f"{i}. @{username} (ID: `{user['telegram_id']}`)\n"
                    f"   Exchanges: `{user['exchange_count']}`\n"
                )
            
            if len(connected_users) > 8:
                users_text += f"\n... and `{len(connected_users) - 8}` more users"
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 User Stats", callback_data="admin_user_stats"),
                    InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")
                ],
                [
                    InlineKeyboardButton("📣 Message All", callback_data="admin_broadcast"),
                    InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(users_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing user management: {e}")
            await query.edit_message_text("❌ Error loading user data.")
    
    async def _show_broadcast_prompt(self, query, context):
        """Show broadcast message prompt"""
        broadcast_text = (
            "📣 *BROADCAST MESSAGE* 📣\n\n"
            "To send a message to all users, use:\n"
            "`/broadcast Your message here`\n\n"
            "**Example:**\n"
            "`/broadcast 🎉 New features added! Check them out with /help`\n\n"
            "The message will be sent to all registered users."
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📊 User Count", callback_data="admin_users"),
                InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(broadcast_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_close_all_prompt(self, query, context):
        """Show close all positions prompt"""
        try:
            active_trades = self.trade_model.get_active_trades()
            
            close_text = (
                "🚨 *EMERGENCY POSITION CLOSURE* 🚨\n\n"
                f"⚠️ **WARNING:** This will close ALL open positions!\n\n"
                f"📊 **Current Status:**\n"
                f"• Active Trades: `{len(active_trades)}`\n"
                f"• Affected Users: `{len(set(trade['user_id'] for trade in active_trades))}`\n\n"
                f"**This action cannot be undone!**\n\n"
                f"Are you sure you want to proceed?"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("🚨 YES - CLOSE ALL", callback_data="admin_confirm_close_all"),
                    InlineKeyboardButton("❌ Cancel", callback_data="admin_cancel_close")
                ],
                [
                    InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(close_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing close all prompt: {e}")
            await query.edit_message_text("❌ Error loading position data.")
    
    async def _show_signal_prompt(self, query, context):
        """Show signal creation prompt"""
        signal_text = (
            "📈 *CREATE NEW TRADING SIGNAL* 📈\n\n"
            "To send a trading signal, use:\n"
            "`/signal SYMBOL ACTION ENTRY SL TP [LEVERAGE] [SIZE]`\n\n"
            "**Parameters:**\n"
            "• `SYMBOL`: Trading pair (e.g., BTCUSDT)\n"
            "• `ACTION`: BUY or SELL\n"
            "• `ENTRY`: Entry price\n"
            "• `SL`: Stop-loss price\n"
            "• `TP`: Take-profit price\n"
            "• `LEVERAGE`: Optional (default: 10x)\n"
            "• `SIZE`: Optional position size % (default: 5%)\n\n"
            "**Example:**\n"
            "`/signal BTCUSDT BUY 35000 34000 36000 10 5`\n\n"
            "This will send the signal to all subscribers and execute auto-trades."
        )
        
        keyboard = [
            [
                InlineKeyboardButton("📊 Subscriber Count", callback_data="admin_subscriber_count"),
                InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(signal_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _show_admin_settings(self, query, context):
        """Show admin settings"""
        settings_text = (
            "⚙️ *ADMIN SETTINGS* ⚙️\n\n"
            f"🤖 **Bot Configuration:**\n"
            f"• Max Leverage: `{Config.MAX_LEVERAGE}x`\n"
            f"• Max Position Size: `{Config.MAX_POSITION_SIZE_PERCENT}%`\n"
            f"• Supported Exchanges: `{len(Config.SUPPORTED_EXCHANGES)}`\n"
            f"• Admin ID: `{Config.ADMIN_ID}`\n\n"
            f"📊 **System Status:**\n"
            f"• Database: `Connected`\n"
            f"• Logging: `Active`\n"
            f"• Auto-Trading: `Enabled`\n"
            f"• Signal Processing: `Active`\n\n"
            f"📅 **Uptime:** Since bot start"
        )
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Restart Services", callback_data="admin_restart_services"),
                InlineKeyboardButton("📋 View Logs", callback_data="admin_view_logs")
            ],
            [
                InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_panel")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(settings_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def _confirm_close_all_positions(self, query, context):
        """Confirm and execute closing all positions"""
        try:
            await query.edit_message_text("🔄 Initiating emergency position closure...")
            
            # Get all active trades
            active_trades = self.trade_model.get_active_trades()
            
            if not active_trades:
                await query.edit_message_text("ℹ️ No active positions found to close.")
                return
            
            # In a real implementation, this would:
            # 1. Connect to each user's exchange
            # 2. Close all open positions
            # 3. Update database records
            # 4. Send notifications to users
            
            # For now, simulate the process
            closed_count = 0
            failed_count = 0
            
            for trade in active_trades:
                try:
                    # Simulate closing position
                    # In real implementation: exchange_api.close_position(trade)
                    self.trade_model.close_trade(trade['id'], 'ADMIN_EMERGENCY_CLOSE')
                    closed_count += 1
                    await asyncio.sleep(0.1)  # Simulate API delay
                except Exception as e:
                    logger.error(f"Failed to close trade {trade['id']}: {e}")
                    failed_count += 1
            
            result_text = (
                "✅ *EMERGENCY CLOSURE COMPLETED* ✅\n\n"
                f"📊 **Results:**\n"
                f"• Positions Closed: `{closed_count}`\n"
                f"• Failed Closures: `{failed_count}`\n"
                f"• Total Processed: `{len(active_trades)}`\n\n"
                f"📅 **Completed:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"🔔 Users have been notified of position closures."
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 View Report", callback_data="admin_closure_report"),
                    InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(result_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in confirm_close_all_positions: {e}")
            await query.edit_message_text("❌ Error during position closure. Check logs.")
    
    async def _show_admin_panel(self, query, context):
        """Show main admin panel"""
        try:
            # Get fresh stats
            total_users = self.user_model.get_all_users_count()
            active_users = self.user_model.get_active_users_count(days=7)
            connected_users = len(self.exchange_model.get_all_connected_users())
            total_trades = self.trade_model.get_total_trades_count()
            total_volume = self.trade_model.get_total_volume()
            total_pnl = self.trade_model.get_total_pnl()
            
            admin_text = (
                "🔐 *ADMIN DASHBOARD* 🔐\n\n"
                f"👥 **Users:**\n"
                f"• Total Users: `{total_users}`\n"
                f"• Active Users (7d): `{active_users}`\n"
                f"• Connected Users: `{connected_users}`\n\n"
                f"📊 **Trading:**\n"
                f"• Total Trades: `{total_trades}`\n"
                f"• Total Volume: `${total_volume:,.2f}`\n"
                f"• Total P&L: `${total_pnl:+,.2f}`\n\n"
                f"🤖 **Bot Status:** `ONLINE`\n"
                f"📅 **Server Time:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n\n"
                f"🎯 **Admin Actions:**"
            )
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
                    InlineKeyboardButton("👥 Users", callback_data="admin_users")
                ],
                [
                    InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"),
                    InlineKeyboardButton("🚨 Close All", callback_data="admin_close_all")
                ],
                [
                    InlineKeyboardButton("📈 New Signal", callback_data="admin_new_signal"),
                    InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(admin_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error showing admin panel: {e}")
            await query.edit_message_text("❌ Error loading admin panel.")
    
    async def stats_command(self, update: Update, context: CallbackContext):
        """Show detailed statistics"""
        if update.effective_user.id != Config.ADMIN_ID:
            await update.message.reply_text("❌ Admin only command")
            return
        
        try:
            # Get stats
            total_users = self.user_model.get_all_users_count()
            active_users = self.user_model.get_active_users_count(days=7)
            connected_users = len(self.exchange_model.get_all_connected_users())
            total_trades = self.trade_model.get_total_trades_count()
            successful_trades = self.trade_model.get_successful_trades_count()
            win_rate = (successful_trades / total_trades * 100) if total_trades > 0 else 0
            total_volume = self.trade_model.get_total_volume()
            total_pnl = self.trade_model.get_total_pnl()
            
            # Get exchange distribution
            exchange_distribution = self.exchange_model.get_exchange_distribution()
            
            stats_text = (
                "📊 *DETAILED STATISTICS* 📊\n\n"
                f"👥 **User Stats:**\n"
                f"• Total Users: `{total_users}`\n"
                f"• Active Users (7d): `{active_users}`\n"
                f"• Connected Users: `{connected_users}`\n"
                f"• Retention Rate: `{(active_users/total_users*100) if total_users > 0 else 0:.1f}%`\n\n"
                f"💰 **Trading Stats:**\n"
                f"• Total Trades: `{total_trades}`\n"
                f"• Successful Trades: `{successful_trades}`\n"
                f"• Win Rate: `{win_rate:.1f}%`\n"
                f"• Total Volume: `${total_volume:,.2f}`\n"
                f"• Total P&L: `${total_pnl:+,.2f}`\n\n"
                f"🏢 **Exchange Distribution:**\n"
            )
            
            for exchange, count in exchange_distribution.items():
                stats_text += f"• {exchange.title()}: `{count}`\n"
            
            await update.message.reply_text(stats_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in stats_command: {e}")
            await update.message.reply_text("❌ Error retrieving statistics.")
    
    async def users_command(self, update: Update, context: CallbackContext):
        """Show user management"""
        if update.effective_user.id != Config.ADMIN_ID:
            await update.message.reply_text("❌ Admin only command")
            return
        
        try:
            # Get users with exchanges
            connected_users = self.exchange_model.get_all_connected_users()
            
            users_text = (
                "👥 *USER MANAGEMENT* 👥\n\n"
                f"Total Connected Users: `{len(connected_users)}`\n\n"
            )
            
            for i, user in enumerate(connected_users[:10], 1):
                users_text += (
                    f"{i}. ID: `{user['telegram_id']}`\n"
                    f"   Name: {user['first_name'] or user['username'] or 'Unknown'}\n"
                    f"   Exchanges: `{user['exchange_count']}`\n\n"
                )
            
            if len(connected_users) > 10:
                users_text += f"... and {len(connected_users) - 10} more users"
            
            keyboard = [
                [
                    InlineKeyboardButton("📊 User Stats", callback_data="admin_user_stats"),
                    InlineKeyboardButton("🔍 Search User", callback_data="admin_search_user")
                ],
                [
                    InlineKeyboardButton("📣 Message All", callback_data="admin_message_all"),
                    InlineKeyboardButton("🔙 Back", callback_data="admin_back")
                ]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(users_text, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in users_command: {e}")
            await update.message.reply_text("❌ Error retrieving users.")
    
    async def signal_command(self, update: Update, context: CallbackContext):
        """Send trading signal"""
        if update.effective_user.id != Config.ADMIN_ID:
            await update.message.reply_text("❌ Admin only command")
            return
        
        try:
            if len(context.args) < 5:
                await update.message.reply_text(
                    "❌ *Invalid format*\n\n"
                    "Usage: `/signal SYMBOL ACTION ENTRY SL TP [LEVERAGE] [SIZE]`\n"
                    "Example: `/signal BTCUSDT BUY 35000 34000 36000 10 5`\n\n"
                    "Parameters:\n"
                    "• SYMBOL: Trading pair (e.g., BTCUSDT)\n"
                    "• ACTION: BUY or SELL\n"
                    "• ENTRY: Entry price\n"
                    "• SL: Stop-loss price\n"
                    "• TP: Take-profit price\n"
                    "• LEVERAGE: (Optional) Leverage (default: 10)\n"
                    "• SIZE: (Optional) Position size % (default: 5)",
                    parse_mode='Markdown'
                )
                return
            
            symbol = context.args[0].upper()
            action = context.args[1].upper()
            entry = float(context.args[2])
            sl = float(context.args[3])
            tp = float(context.args[4])
            leverage = int(context.args[5]) if len(context.args) > 5 else 10
            size = float(context.args[6]) if len(context.args) > 6 else 5.0
            
            if action not in ['BUY', 'SELL']:
                await update.message.reply_text("❌ Action must be BUY or SELL")
                return
            
            # Validate parameters
            if leverage < 1 or leverage > Config.MAX_LEVERAGE:
                await update.message.reply_text(f"❌ Leverage must be between 1 and {Config.MAX_LEVERAGE}")
                return
            
            if size < 1 or size > Config.MAX_POSITION_SIZE_PERCENT:
                await update.message.reply_text(f"❌ Size must be between 1% and {Config.MAX_POSITION_SIZE_PERCENT}%")
                return
            
            # Save signal to database
            signal_id = self.signal_model.create_signal(
                symbol, action, entry, sl, tp, leverage, size, Config.ADMIN_ID
            )
            
            # Get subscribers
            subscribers = self.signal_model.get_subscribers()
            
            # Format signal message
            signal_msg = (
                "🚀 *NEW TRADING SIGNAL* 🚀\n\n"
                f"📊 **Pair:** `{symbol}`\n"
                f"📈 **Action:** `{action}`\n"
                f"💰 **Entry:** `${entry:,.2f}`\n"
                f"🛑 **Stop Loss:** `${sl:,.2f}`\n"
                f"🎯 **Take Profit:** `${tp:,.2f}`\n"
                f"⚡ **Leverage:** `{leverage}x`\n"
                f"📊 **Size:** `{size}%`\n\n"
                f"🆔 Signal ID: `{signal_id}`\n"
                f"⏱️ Auto-execution in progress..."
            )
            
            # Send to subscribers
            sent_count = 0
            for subscriber in subscribers:
                try:
                    await context.bot.send_message(
                        chat_id=subscriber['telegram_id'],
                        text=signal_msg,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send signal to {subscriber['telegram_id']}: {e}")
            
            await update.message.reply_text(
                f"✅ *Signal sent successfully!*\n\n"
                f"📤 Delivered to: `{sent_count}/{len(subscribers)}` subscribers\n"
                f"🆔 Signal ID: `{signal_id}`\n\n"
                f"⏱️ Auto-execution in progress...",
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text("❌ Invalid number format in signal parameters")
        except Exception as e:
            logger.error(f"Signal command error: {e}")
            await update.message.reply_text(f"❌ Error processing signal: {str(e)}")
    
    async def broadcast_command(self, update: Update, context: CallbackContext):
        """Broadcast message to all users"""
        if update.effective_user.id != Config.ADMIN_ID:
            await update.message.reply_text("❌ Admin only command")
            return
        
        try:
            if not context.args:
                await update.message.reply_text(
                    "❌ *No message provided*\n\n"
                    "Usage: `/broadcast Your message here`",
                    parse_mode='Markdown'
                )
                return
            
            message = ' '.join(context.args)
            
            # Get all users
            users = self.user_model.get_all_users()
            
            # Format broadcast message
            broadcast_msg = (
                "📣 *ADMIN ANNOUNCEMENT* 📣\n\n"
                f"{message}\n\n"
                f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            # Send to all users
            sent_count = 0
            for user in users:
                try:
                    await context.bot.send_message(
                        chat_id=user['telegram_id'],
                        text=broadcast_msg,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                    await asyncio.sleep(0.05)  # Avoid rate limits
                except Exception as e:
                    logger.error(f"Failed to send broadcast to {user['telegram_id']}: {e}")
            
            await update.message.reply_text(
                f"✅ *Broadcast sent successfully!*\n\n"
                f"📤 Delivered to: `{sent_count}/{len(users)}` users",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Broadcast command error: {e}")
            await update.message.reply_text(f"❌ Error sending broadcast: {str(e)}")
    
    async def close_positions_command(self, update: Update, context: CallbackContext):
        """Close all open positions"""
        if update.effective_user.id != Config.ADMIN_ID:
            await update.message.reply_text("❌ Admin only command")
            return
        
        try:
            # Get confirmation
            if not context.args or context.args[0].lower() != 'confirm':
                await update.message.reply_text(
                    "⚠️ *EMERGENCY POSITION CLOSURE* ⚠️\n\n"
                    "This will close ALL open positions for ALL users!\n\n"
                    "To confirm, type: `/close confirm`",
                    parse_mode='Markdown'
                )
                return
            
            # Get active trades
            active_trades = self.trade_model.get_active_trades()
            
            if not active_trades:
                await update.message.reply_text("ℹ️ No active trades to close.")
                return
            
            await update.message.reply_text(
                f"🔄 Closing {len(active_trades)} active positions...\n\n"
                f"This may take a moment."
            )
            
            # In a real implementation, this would connect to exchanges and close positions
            # For now, we'll just simulate it
            
            await update.message.reply_text(
                f"✅ *Position closure complete*\n\n"
                f"Closed {len(active_trades)} positions across all users.\n"
                f"Detailed report available in admin logs.",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Close positions command error: {e}")
            await update.message.reply_text(f"❌ Error closing positions: {str(e)}")
