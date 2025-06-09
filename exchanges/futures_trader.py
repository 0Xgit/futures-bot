import asyncio
import logging
from typing import Dict, Optional
import ccxt
from config.settings import Config
from exchanges.auth_manager import ExchangeAuthManager

logger = logging.getLogger(__name__)

class FuturesTrader:
    def __init__(self):
        self.auth_manager = ExchangeAuthManager(Config.ENCRYPTION_KEY)
        self.exchanges = {}
    
    def get_exchange_client(self, exchange_name: str, api_key: str, api_secret: str, passphrase: str = '') -> ccxt.Exchange:
        """Get exchange client instance"""
        try:
            if exchange_name == 'binance':
                return ccxt.binance({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': Config.TESTNET_MODE,
                    'options': {'defaultType': 'future'}
                })
            elif exchange_name == 'bybit':
                return ccxt.bybit({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': Config.TESTNET_MODE,
                    'options': {'defaultType': 'linear'}
                })
            elif exchange_name == 'okx':
                return ccxt.okx({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'password': passphrase,
                    'sandbox': Config.TESTNET_MODE,
                    'options': {'defaultType': 'swap'}
                })
            elif exchange_name == 'bitget':
                return ccxt.bitget({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'password': passphrase,
                    'sandbox': Config.TESTNET_MODE,
                    'options': {'defaultType': 'swap'}
                })
            elif exchange_name == 'mexc':
                return ccxt.mexc({
                    'apiKey': api_key,
                    'secret': api_secret,
                    'sandbox': Config.TESTNET_MODE,
                    'options': {'defaultType': 'swap'}
                })
            else:
                raise ValueError(f"Unsupported exchange: {exchange_name}")
                
        except Exception as e:
            logger.error(f"Error creating exchange client: {e}")
            raise
    
    async def execute_trade(self, exchange_config: Dict, signal: Dict, user: Dict) -> Dict:
        """Execute a futures trade"""
        try:
            # Decrypt credentials
            api_key, api_secret, passphrase = self.auth_manager.decrypt_credentials(
                exchange_config['api_key_encrypted'],
                exchange_config['api_secret_encrypted'],
                exchange_config['passphrase_encrypted']
            )
            
            # Get exchange client
            exchange = self.get_exchange_client(
                exchange_config['exchange_name'], 
                api_key, 
                api_secret, 
                passphrase
            )
            
            # Calculate position size
            balance = await self.get_balance(exchange)
            position_size_percent = exchange_config.get('position_size_percent', 5)
            leverage = signal.get('leverage', exchange_config.get('leverage', 10))
            
            position_value = balance * (position_size_percent / 100) * leverage
            quantity = position_value / signal['entry_price']
            
            # Set leverage
            await self.set_leverage(exchange, signal['symbol'], leverage)
            
            # Place order
            side = 'buy' if signal['action'].upper() in ['BUY', 'LONG'] else 'sell'
            
            order = await exchange.create_market_order(
                symbol=signal['symbol'],
                side=side,
                amount=quantity,
                params={'reduceOnly': False}
            )
            
            # Set stop loss and take profit
            if signal.get('stop_loss'):
                await self.set_stop_loss(exchange, signal['symbol'], side, quantity, signal['stop_loss'])
            
            if signal.get('take_profit'):
                await self.set_take_profit(exchange, signal['symbol'], side, quantity, signal['take_profit'])
            
            return {
                'success': True,
                'order_id': order['id'],
                'entry_price': order['price'] or signal['entry_price'],
                'quantity': quantity,
                'side': side
            }
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_balance(self, exchange: ccxt.Exchange) -> float:
        """Get futures balance"""
        try:
            balance = await exchange.fetch_balance()
            return balance['USDT']['free'] if 'USDT' in balance else 0.0
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    async def set_leverage(self, exchange: ccxt.Exchange, symbol: str, leverage: int):
        """Set leverage for symbol"""
        try:
            if hasattr(exchange, 'set_leverage'):
                await exchange.set_leverage(leverage, symbol)
        except Exception as e:
            logger.error(f"Error setting leverage: {e}")
    
    async def set_stop_loss(self, exchange: ccxt.Exchange, symbol: str, side: str, quantity: float, stop_price: float):
        """Set stop loss order"""
        try:
            stop_side = 'sell' if side == 'buy' else 'buy'
            await exchange.create_order(
                symbol=symbol,
                type='stop_market',
                side=stop_side,
                amount=quantity,
                params={
                    'stopPrice': stop_price,
                    'reduceOnly': True
                }
            )
        except Exception as e:
            logger.error(f"Error setting stop loss: {e}")
    
    async def set_take_profit(self, exchange: ccxt.Exchange, symbol: str, side: str, quantity: float, take_profit_price: float):
        """Set take profit order"""
        try:
            tp_side = 'sell' if side == 'buy' else 'buy'
            await exchange.create_limit_order(
                symbol=symbol,
                side=tp_side,
                amount=quantity,
                price=take_profit_price,
                params={'reduceOnly': True}
            )
        except Exception as e:
            logger.error(f"Error setting take profit: {e}")
    
    async def get_current_price(self, exchange_name: str, symbol: str) -> Optional[float]:
        """Get current price for symbol"""
        try:
            # Use a simple client without credentials for price data
            if exchange_name == 'binance':
                exchange = ccxt.binance({'options': {'defaultType': 'future'}})
            elif exchange_name == 'bybit':
                exchange = ccxt.bybit({'options': {'defaultType': 'linear'}})
            elif exchange_name == 'okx':
                exchange = ccxt.okx({'options': {'defaultType': 'swap'}})
            elif exchange_name == 'bitget':
                exchange = ccxt.bitget({'options': {'defaultType': 'swap'}})
            elif exchange_name == 'mexc':
                exchange = ccxt.mexc({'options': {'defaultType': 'swap'}})
            else:
                return None
            
            ticker = await exchange.fetch_ticker(symbol)
            return ticker['last']
            
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return None
    
    async def close_position(self, trade: Dict) -> Dict:
        """Close an open position"""
        try:
            # Implementation for closing positions
            # This would involve creating a market order in the opposite direction
            return {
                'success': True,
                'close_price': 0.0,
                'pnl': 0.0
            }
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def execute_signal_trade(self, user: Dict, signal: Dict):
        """Execute signal trade for user"""
        try:
            # Get user exchanges and execute trades
            from database.models import ExchangeModel
            exchange_model = ExchangeModel(self.auth_manager.db)
            user_exchanges = exchange_model.get_user_exchanges(user['id'])
            
            for exchange_config in user_exchanges:
                if exchange_config.get('auto_trade', True):
                    result = await self.execute_trade(exchange_config, signal, user)
                    if result['success']:
                        logger.info(f"Signal executed for user {user['id']} on {exchange_config['exchange_name']}")
                        
        except Exception as e:
            logger.error(f"Error executing signal trade: {e}")
