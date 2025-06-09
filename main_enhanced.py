import logging
import sys
import os
import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram import Update
from config.settings import Config
from bot.enhanced_user_handlers import EnhancedUserHandlers
from bot.admin_handlers import AdminHandlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

os.makedirs('logs', exist_ok=True)
file_handler = logging.FileHandler('logs/bot.log', encoding='utf-8')
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

logger = logging.getLogger(__name__)
logger.addHandler(file_handler)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

async def main():
    """Main function with enhanced easy connect features"""
    try:
        Config.validate()
        
        # Initialize enhanced handlers
        user_handlers = EnhancedUserHandlers()
        admin_handlers = AdminHandlers()
        
        application = (
            Application.builder()
            .token(Config.TELEGRAM_TOKEN)
            .connect_timeout(30)
            .read_timeout(30)
            .write_timeout(30)
            .pool_timeout(30)
            .build()
        )
        
        # Enhanced user command handlers
        application.add_handler(CommandHandler("start", user_handlers.start_command))
        application.add_handler(CommandHandler("help", user_handlers.help_command))
        application.add_handler(CommandHandler("connect", user_handlers.connect_command))
        application.add_handler(CommandHandler("balance", user_handlers.balance_command))
        application.add_handler(CommandHandler("subscribe", user_handlers.subscribe_command))
        application.add_handler(CommandHandler("settings", user_handlers.settings_command))
        application.add_handler(CommandHandler("trades", user_handlers.trades_command))
        
        # Admin command handlers
        application.add_handler(CommandHandler("admin", admin_handlers.admin_panel))
        application.add_handler(CommandHandler("signal", admin_handlers.signal_command))
        application.add_handler(CommandHandler("broadcast", admin_handlers.broadcast_command))
        
        # Enhanced callback query handlers
        application.add_handler(CallbackQueryHandler(user_handlers.connection_callback))
        application.add_handler(CallbackQueryHandler(admin_handlers.admin_callback_handler, pattern="^admin_"))
        
        # Enhanced message handler for credentials
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            user_handlers.handle_credentials
        ))
        
        await application.initialize()
        
        logger.info("🚀 Enhanced Futures Trading Bot starting up...")
        logger.info(f"📊 Supported Exchanges: {len(Config.SUPPORTED_EXCHANGES)}")
        logger.info(f"👨‍💼 Admin ID: {Config.ADMIN_ID}")
        logger.info("✨ Easy Connect System: ENABLED")
        
        print("🚀 Enhanced Futures Trading Bot is now running!")
        print("✨ NEW FEATURES:")
        print("  • 🤖 Easy Connect (2-minute setup)")
        print("  • 📋 Step-by-step guides")
        print("  • 📱 Mobile-friendly setup")
        print("  • 🆘 Live support system")
        print("  • 🎯 User profiling & recommendations")
        print(f"📊 Supported Exchanges: {', '.join(Config.SUPPORTED_EXCHANGES.keys())}")
        print(f"👨‍💼 Admin ID: {Config.ADMIN_ID}")
        print("🔄 Bot is polling for messages...")
        print("📝 Use Ctrl+C to stop the bot")
        
        await application.start()
        await application.updater.start_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Received stop signal")
        finally:
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
