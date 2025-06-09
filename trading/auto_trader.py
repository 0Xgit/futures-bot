import asyncio
import logging
from typing import Dict, List
from database.models import Database, TradeModel, ExchangeModel, UserModel
from exchanges.futures_trader import FuturesTrader
from config.settings import Config

logger = logging.getLogger(__name__)

class AutoTrader:
    def __init__(self):
        self.db = Database()
        self.trade_model = TradeModel(self.db)
        self.exchange_model = ExchangeModel(self.db)
        self.user_model = UserModel(self.db)
        self.futures_trader = FuturesTrader()
        self.is_trading = False
        self.trading_task = None
    
    async def start_trading_engine(self):
        """Start the automated trading engine"""
        try:
            self.is_trading = True
            logger.info("🤖 Auto-trading engine started")
            
            while self.is_trading:
                await self.monitor_positions()
                await self.check_stop_losses()
                await self.check_take_profits()
                await asyncio.sleep(5)  # Check every 5 seconds
                
        except Exception as e:
            logger.error(f"Auto-trading engine error: {e}")
    
    async def stop_trading_engine(self):
        """Stop the automated trading engine"""
        self.is_trading = False
        if self.trading_task:
            self.trading_task.cancel()
        logger.info("🤖 Auto-trading engine stopped")
    
    async def monitor_positions(self):
        """Monitor all open positions"""
        try:
            # Get all open trades
            open_trades = self.trade_model.get_open_trades()
            
            for trade in open_trades:
                await self.update_trade_pnl(trade)
                
        except Exception as e:
            logger.error(f"Error monitoring positions: {e}")
    
    async def update_trade_pnl(self, trade: Dict):
        """Update trade P&L"""
        try:
            # Get current price and calculate P&L
            current_price = await self.futures_trader.get_current_price(
                trade['exchange_name'], trade['symbol']
            )
            
            if current_price:
                # Calculate P&L
                if trade['side'].upper() == 'LONG':
                    pnl = (current_price - trade['entry_price']) * trade['quantity']
                else:
                    pnl = (trade['entry_price'] - current_price) * trade['quantity']
                
                # Update in database
                self.trade_model.update_trade_pnl(trade['id'], pnl, current_price)
                
        except Exception as e:
            logger.error(f"Error updating trade P&L: {e}")
    
    async def check_stop_losses(self):
        """Check and execute stop losses"""
        try:
            open_trades = self.trade_model.get_open_trades()
            
            for trade in open_trades:
                if not trade['stop_loss']:
                    continue
                
                current_price = await self.futures_trader.get_current_price(
                    trade['exchange_name'], trade['symbol']
                )
                
                if current_price:
                    should_close = False
                    
                    if trade['side'].upper() == 'LONG' and current_price <= trade['stop_loss']:
                        should_close = True
                    elif trade['side'].upper() == 'SHORT' and current_price >= trade['stop_loss']:
                        should_close = True
                    
                    if should_close:
                        await self.close_position(trade, 'STOP_LOSS')
                        
        except Exception as e:
            logger.error(f"Error checking stop losses: {e}")
    
    async def check_take_profits(self):
        """Check and execute take profits"""
        try:
            open_trades = self.trade_model.get_open_trades()
            
            for trade in open_trades:
                if not trade['take_profit']:
                    continue
                
                current_price = await self.futures_trader.get_current_price(
                    trade['exchange_name'], trade['symbol']
                )
                
                if current_price:
                    should_close = False
                    
                    if trade['side'].upper() == 'LONG' and current_price >= trade['take_profit']:
                        should_close = True
                    elif trade['side'].upper() == 'SHORT' and current_price <= trade['take_profit']:
                        should_close = True
                    
                    if should_close:
                        await self.close_position(trade, 'TAKE_PROFIT')
                        
        except Exception as e:
            logger.error(f"Error checking take profits: {e}")
    
    async def close_position(self, trade: Dict, reason: str):
        """Close a position"""
        try:
            # Close the position via futures trader
            result = await self.futures_trader.close_position(trade)
            
            if result['success']:
                # Update trade as closed
                self.trade_model.close_trade(
                    trade['id'], 
                    result['close_price'], 
                    result['pnl'],
                    reason
                )
                
                logger.info(f"Position closed: {trade['symbol']} - {reason} - P&L: {result['pnl']}")
                
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    async def execute_signal_trade(self, user: Dict, signal: Dict):
        """Execute a trade based on signal"""
        try:
            # Get user's exchanges
            user_exchanges = self.exchange_model.get_user_exchanges(user['id'])
            
            for exchange in user_exchanges:
                if not exchange.get('auto_trade', True):
                    continue
                
                # Execute trade on this exchange
                result = await self.futures_trader.execute_trade(
                    exchange, signal, user
                )
                
                if result['success']:
                    # Record trade in database
                    self.trade_model.create_trade(
                        user['id'],
                        exchange['id'],
                        signal['id'],
                        signal['symbol'],
                        signal['action'],
                        result['entry_price'],
                        result['quantity'],
                        signal['stop_loss'],
                        signal['take_profit'],
                        signal.get('leverage', 10)
                    )
                    
                    logger.info(f"Trade executed for user {user['id']}: {signal['symbol']}")
                
        except Exception as e:
            logger.error(f"Error executing signal trade: {e}")
