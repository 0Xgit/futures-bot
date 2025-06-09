import asyncio
import logging
from typing import Dict, List
from database.models import Database, SignalModel, UserModel
from exchanges.futures_trader import FuturesTrader
from config.settings import Config

logger = logging.getLogger(__name__)

class SignalProcessor:
    def __init__(self):
        self.db = Database()
        self.signal_model = SignalModel(self.db)
        self.user_model = UserModel(self.db)
        self.futures_trader = FuturesTrader()
        self.is_monitoring = False
        self.monitoring_task = None
    
    async def start_monitoring(self):
        """Start signal monitoring"""
        try:
            self.is_monitoring = True
            logger.info("📡 Signal monitoring started")
            
            while self.is_monitoring:
                await self.process_pending_signals()
                await asyncio.sleep(1)  # Check every second
                
        except Exception as e:
            logger.error(f"Signal monitoring error: {e}")
    
    async def stop_monitoring(self):
        """Stop signal monitoring"""
        self.is_monitoring = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
        logger.info("📡 Signal monitoring stopped")
    
    async def process_pending_signals(self):
        """Process pending signals"""
        try:
            # Get pending signals
            pending_signals = self.signal_model.get_pending_signals()
            
            for signal in pending_signals:
                await self.execute_signal(signal)
                
        except Exception as e:
            logger.error(f"Error processing signals: {e}")
    
    async def execute_signal(self, signal: Dict):
        """Execute a trading signal"""
        try:
            # Get all subscribed users
            subscribers = self.user_model.get_subscribed_users()
            
            for user in subscribers:
                try:
                    # Execute trade for each user
                    await self.futures_trader.execute_signal_trade(user, signal)
                    
                except Exception as e:
                    logger.error(f"Error executing signal for user {user['id']}: {e}")
            
            # Mark signal as processed
            self.signal_model.mark_signal_processed(signal['id'])
            
        except Exception as e:
            logger.error(f"Error executing signal {signal['id']}: {e}")
    
    async def broadcast_signal(self, signal: Dict, bot_instance):
        """Broadcast signal to all subscribers"""
        try:
            subscribers = self.user_model.get_subscribed_users()
            
            signal_text = (
                f"🚀 *NEW TRADING SIGNAL* 🚀\n\n"
                f"📊 **Pair:** `{signal['symbol']}`\n"
                f"📈 **Action:** `{signal['action']}`\n"
                f"💰 **Entry:** `${signal['entry_price']:,.2f}`\n"
                f"🛑 **Stop Loss:** `${signal['stop_loss']:,.2f}`\n"
                f"🎯 **Take Profit:** `${signal['take_profit']:,.2f}`\n"
                f"⚡ **Leverage:** `{signal.get('leverage', 10)}x`\n"
                f"📊 **Position Size:** `{signal.get('position_size', 5)}%`\n\n"
                f"🤖 **Auto-execution in progress...**\n"
                f"🆔 Signal ID: `{signal['id']}`"
            )
            
            sent_count = 0
            for subscriber in subscribers:
                try:
                    await bot_instance.send_message(
                        chat_id=subscriber['telegram_id'],
                        text=signal_text,
                        parse_mode='Markdown'
                    )
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send signal to {subscriber['telegram_id']}: {e}")
            
            logger.info(f"Signal broadcast to {sent_count}/{len(subscribers)} users")
            
        except Exception as e:
            logger.error(f"Error broadcasting signal: {e}")
