import logging
import sys
import os
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from telegram import Update
from config.settings import Config
from bot.handlers import BotHandlers
from bot.admin_handlers import AdminHandlers
from trading.signal_processor import SignalProcessor
from trading.auto_trader import AutoTrader

# Setup logging with directory creation
os.makedirs('logs', exist_ok=True)
os.makedirs('data', exist_ok=True)

logging.basicConfig(
    format=Config.LOG_FORMAT,
    level=getattr(logging, Config.LOG_LEVEL),
    handlers=[
        logging.FileHandler(Config.LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main function to run the automated futures trading bot"""
    try:
        # Validate configuration
        Config.validate()
        
        # Initialize handlers and processors
        bot_handlers = BotHandlers()
        admin_handlers = AdminHandlers()
        signal_processor = SignalProcessor()
        auto_trader = AutoTrader()
        
        # Create application
        application = ApplicationBuilder().token(Config.BOT_TOKEN).build()
        
        # User command handlers
        application.add_handler(CommandHandler("start", bot_handlers.start_command))
        application.add_handler(CommandHandler("help", bot_handlers.help_command))
        application.add_handler(CommandHandler("connect", bot_handlers.connect_command))
        application.add_handler(CommandHandler("balance", bot_handlers.balance_command))
        application.add_handler(CommandHandler("portfolio", bot_handlers.portfolio_command))
        application.add_handler(CommandHandler("trades", bot_handlers.trades_command))
        application.add_handler(CommandHandler("subscribe", bot_handlers.subscribe_command))
        application.add_handler(CommandHandler("settings", bot_handlers.settings_command))
        application.add_handler(CommandHandler("status", bot_handlers.status_command))
        application.add_handler(CommandHandler("pnl", bot_handlers.pnl_command))
        
        # Admin command handlers
        application.add_handler(CommandHandler("admin", admin_handlers.admin_command))
        application.add_handler(CommandHandler("signal", admin_handlers.signal_command))
        application.add_handler(CommandHandler("broadcast", admin_handlers.broadcast_command))
        application.add_handler(CommandHandler("stats", admin_handlers.stats_command))
        application.add_handler(CommandHandler("users", admin_handlers.users_command))
        application.add_handler(CommandHandler("close", admin_handlers.close_positions_command))
        
        # Callback query handlers
        application.add_handler(CallbackQueryHandler(bot_handlers.callback_handler))
        application.add_handler(CallbackQueryHandler(admin_handlers.admin_callback_handler, pattern="^admin_"))
        
        # Message handler for credentials
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            bot_handlers.handle_credentials
        ))
        
        # Initialize the application
        await application.initialize()
        
        # Start background tasks
        asyncio.create_task(signal_processor.start_monitoring())
        asyncio.create_task(auto_trader.start_trading_engine())
        
        # Start bot
        logger.info("🚀 Automated Futures Trading Bot starting up...")
        logger.info(f"📊 Supported Exchanges: {len(Config.SUPPORTED_EXCHANGES)}")
        logger.info(f"👨‍💼 Admin ID: {Config.ADMIN_ID}")
        logger.info("🤖 Auto-trading engine: ACTIVE")
        logger.info("📡 Signal monitoring: ACTIVE")
        
        print("🚀 AUTOMATED FUTURES TRADING BOT")
        print("=" * 50)
        print("✅ FEATURES ACTIVE:")
        print("  🤖 Automated signal execution")
        print("  📊 Real-time portfolio tracking")
        print("  🛡️ Advanced risk management")
        print("  📈 Multi-exchange trading")
        print("  💰 Live P&L monitoring")
        print("  🔄 Auto position management")
        print("  📱 Telegram notifications")
        print("  🎯 Professional signals")
        print(f"\n📊 Exchanges: {', '.join(Config.SUPPORTED_EXCHANGES.keys())}")
        print(f"👨‍💼 Admin: {Config.ADMIN_ID}")
        print("\n🔄 Bot is running... Press Ctrl+C to stop")
        
        # Start polling
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        finally:
            # Cleanup
            await signal_processor.stop_monitoring()
            await auto_trader.stop_trading_engine()
            await application.updater.stop()
            await application.stop()
            await application.shutdown()
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot startup failed: {e}")
        print(f"❌ Error: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
