import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

class Config:
    # Bot configuration
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    ADMIN_ID = int(os.getenv('ADMIN_ID', 0))
    ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY', 'your-secret-key-here')
    
    # Webhook configuration (optional)
    WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
    WEBHOOK_PORT = int(os.getenv('WEBHOOK_PORT', 8443))
    WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')
    
    # OAuth configuration (optional)
    OAUTH_CALLBACK_URL = os.getenv('OAUTH_CALLBACK_URL', '')
    
    # Supported exchanges with their configurations
    SUPPORTED_EXCHANGES = {
        'binance': {
            'name': 'Binance',
            'display_name': 'Binance',
            'requires_passphrase': False,
            'supports_oauth': False,
            'guide_url': 'https://www.binance.com/en/support/faq/how-to-create-api-keys-360002502072',
            'futures_enabled': True,
            'testnet_url': 'https://testnet.binancefuture.com',
            'mainnet_url': 'https://fapi.binance.com'
        },
        'bybit': {
            'name': 'Bybit',
            'display_name': 'Bybit',
            'requires_passphrase': False,
            'supports_oauth': False,
            'guide_url': 'https://learn.bybit.com/bybit-guide/bybit-api-key/',
            'futures_enabled': True,
            'testnet_url': 'https://api-testnet.bybit.com',
            'mainnet_url': 'https://api.bybit.com'
        },
        'okx': {
            'name': 'OKX',
            'display_name': 'OKX',
            'requires_passphrase': True,
            'supports_oauth': False,
            'guide_url': 'https://www.okx.com/help-center/api-key',
            'futures_enabled': True,
            'testnet_url': 'https://www.okx.com/api/v5/mock',
            'mainnet_url': 'https://www.okx.com/api/v5'
        },
        'bitget': {
            'name': 'Bitget',
            'display_name': 'Bitget',
            'requires_passphrase': False,
            'supports_oauth': False,
            'guide_url': 'https://bitget.zendesk.com/hc/en-us/articles/900006092183-API-Management',
            'futures_enabled': True,
            'testnet_url': 'https://api-demo.bitget.com',
            'mainnet_url': 'https://api.bitget.com'
        },
        'mexc': {
            'name': 'MEXC',
            'display_name': 'MEXC',
            'requires_passphrase': False,
            'supports_oauth': False,
            'guide_url': 'https://mexc.zendesk.com/hc/en-001/articles/360037600751-How-to-Create-an-API',
            'futures_enabled': True,
            'testnet_url': 'https://contract.mexc.com/api',
            'mainnet_url': 'https://contract.mexc.com/api'
        }
    }
    
    # Trading configuration
    DEFAULT_LEVERAGE = 10
    MAX_LEVERAGE = 50
    DEFAULT_POSITION_SIZE_PERCENT = 5.0
    MAX_POSITION_SIZE_PERCENT = 10.0
    USE_STOP_LOSS = True
    USE_TAKE_PROFIT = True
    
    # Database configuration
    DB_PATH = os.getenv('DB_PATH', 'data/trading_bot.db')
    
    # Logging configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', 'logs/trading_bot.log')
    
    # Signal configuration
    SIGNAL_EXPIRY_HOURS = 24
    
    # Notification settings
    NOTIFY_ON_TRADE = True
    NOTIFY_ON_ERROR = True

    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required in .env file")
        if not cls.ADMIN_ID:
            raise ValueError("ADMIN_ID is required in .env file")
        
        # Create required directories
        os.makedirs(os.path.dirname(cls.DB_PATH), exist_ok=True)
        os.makedirs(os.path.dirname(cls.LOG_FILE), exist_ok=True)
        
        return True
