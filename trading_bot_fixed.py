import os
import sys
import logging
import sqlite3
import asyncio
import requests
import time
import hmac
import hashlib
from dotenv import load_dotenv
from cryptography.fernet import Fernet
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackContext,
    CallbackQueryHandler, filters
)
from binance.client import Client as BinanceClient
from pybit.unified_trading import HTTP as BybitClient

# Load environment variables from .env file
load_dotenv()

# Initialize logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration - Handle missing environment variables
def get_env_var(name, is_int=False):
    value = os.getenv(name)
    if value is None:
        logger.error(f"❌ Missing required environment variable: {name}")
        sys.exit(1)
    return int(value) if is_int and value is not None else value

try:
    TOKEN = get_env_var('TELEGRAM_TOKEN')
    ADMIN_ID = get_env_var('ADMIN_ID', is_int=True)
except SystemExit:
    logger.error("Bot startup failed due to missing environment variables")
    sys.exit(1)

# Initialize cryptography
ENCRYPTION_KEY = Fernet.generate_key()
cipher_suite = Fernet(ENCRYPTION_KEY)

# Supported exchanges
EXCHANGES = {
    'binance': {
        'name': 'Binance',
        'client': BinanceClient,
        'testnet': 'https://testnet.binance.vision',
        'balance_method': 'binance_balance'
    },
    'bybit': {
        'name': 'Bybit',
        'client': BybitClient,
        'testnet': 'https://api-testnet.bybit.com',
        'balance_method': 'bybit_balance'
    },
    'bitget': {
        'name': 'Bitget',
        'testnet': 'https://api.bitget.com',
        'balance_method': 'bitget_balance'
    },
    'mexc': {
        'name': 'MEXC',
        'testnet': 'https://api.mexc.com',
        'balance_method': 'mexc_balance'
    }
}

# Database setup - FIXED VERSION
def init_db():
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        telegram_id INTEGER UNIQUE,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    
    # Exchange connections table - FIXED SQL
    c.execute('''CREATE TABLE IF NOT EXISTS exchanges (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        exchange_name TEXT,
        api_key_encrypted TEXT,
        api_secret_encrypted TEXT,
        passphrase_encrypted TEXT,
        is_active BOOLEAN DEFAULT 1,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Subscriptions table
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        user_id INTEGER,
        is_subscribed BOOLEAN DEFAULT 1,
        auto_trade BOOLEAN DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    
    # Signals table
    c.execute('''CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY,
        symbol TEXT,
        action TEXT,
        entry_price REAL,
        stop_loss REAL,
        take_profit REAL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_by INTEGER
    )''')
    
    conn.commit()
    conn.close()
    logger.info("✅ Database initialized successfully")

# User management
def get_user(telegram_id):
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE telegram_id=?", (telegram_id,))
    user = c.fetchone()
    conn.close()
    return user[0] if user else None

def create_user(telegram_id):
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    c.execute("INSERT INTO users (telegram_id) VALUES (?)", (telegram_id,))
    user_id = c.lastrowid
    c.execute("INSERT INTO subscriptions (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    return user_id

# Exchange balance methods
async def binance_balance(api_key, api_secret):
    try:
        client = BinanceClient(api_key, api_secret, testnet=True)
        balance = client.get_account()
        usdt_balance = next(
            (item for item in balance['balances'] if item['asset'] == 'USDT'),
            {}
        ).get('free', 0)
        return float(usdt_balance)
    except Exception as e:
        logger.error(f"Binance balance error: {e}")
        raise

async def bybit_balance(api_key, api_secret):
    try:
        client = BybitClient(api_key, api_secret, testnet=True)
        balance = client.get_wallet_balance(accountType="UNIFIED")
        return float(balance['result']['list'][0]['coin'][0]['walletBalance'])
    except Exception as e:
        logger.error(f"Bybit balance error: {e}")
        raise

async def bitget_balance(api_key, api_secret, passphrase=""):
    try:
        url = "https://api.bitget.com/api/spot/v1/account/assets"
        timestamp = str(int(time.time() * 1000))
        message = timestamp + "GET" + "/api/spot/v1/account/assets"
        
        signature = hmac.new(
            api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "ACCESS-KEY": api_key,
            "ACCESS-SIGN": signature,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json"
        }
        
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            assets = response.json().get('data', [])
            usdt_balance = next(
                (item for item in assets if item['coinName'] == 'USDT'),
                {}
            ).get('available', 0)
            return float(usdt_balance)
        else:
            raise Exception(f"Bitget error: {response.text}")
    except Exception as e:
        logger.error(f"Bitget balance error: {e}")
        raise

async def mexc_balance(api_key, api_secret):
    try:
        url = "https://api.mexc.com/api/v3/account"
        timestamp = str(int(time.time() * 1000))
        query_string = f"timestamp={timestamp}"
        signature = hmac.new(
            api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-MEXC-APIKEY": api_key,
            "Content-Type": "application/json"
        }
        
        params = {
            "timestamp": timestamp,
            "signature": signature
        }
        
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            assets = response.json().get('balances', [])
            usdt_balance = next(
                (item for item in assets if item['asset'] == 'USDT'),
                {}
            ).get('free', 0)
            return float(usdt_balance)
        else:
            raise Exception(f"MEXC error: {response.text}")
    except Exception as e:
        logger.error(f"MEXC balance error: {e}")
        raise

# Command handlers
async def start(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if not get_user(user_id):
        create_user(user_id)
    
    await update.message.reply_text(
        "🚀 Welcome to Crypto Trading Bot!\n\n"
        "Available commands:\n"
        "/connect - Link exchange account\n"
        "/balance - Check your balance\n"
        "/subscribe - Receive trading signals\n"
        "/help - Show all commands\n\n"
        "Admin commands:\n"
        "/signal - Send trading signal to subscribers"
    )

async def help_command(update: Update, context: CallbackContext) -> None:
    help_text = (
        "🤖 *Trading Bot Help* 🤖\n\n"
        "*/start* - Start the bot and show welcome message\n"
        "*/connect* - Connect an exchange account (Binance, Bybit, Bitget, MEXC)\n"
        "*/balance* - Check your exchange account balance\n"
        "*/subscribe* - Subscribe to trading signals\n"
        "*/help* - Show this help message\n\n"
        "🔐 *Admin Commands:*\n"
        "*/signal* - Send trading signal to subscribers\n"
        "Format: `/signal SYMBOL ACTION ENTRY SL TP`\n"
        "Example: `/signal BTCUSDT BUY 35000 34000 36000`\n\n"
        "⚙️ *Supported Exchanges:*\n"
        "- Binance\n"
        "- Bybit\n"
        "- Bitget\n"
        "- MEXC"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def connect_exchange(update: Update, context: CallbackContext) -> None:
    keyboard = []
    for exchange in EXCHANGES:
        keyboard.append([InlineKeyboardButton(
            EXCHANGES[exchange]['name'],
            callback_data=f"connect_{exchange}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Select exchange to connect:',
        reply_markup=reply_markup
    )

async def exchange_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    
    if data[0] == 'connect':
        exchange_name = data[1]
        context.user_data['selected_exchange'] = exchange_name
        
        if exchange_name == 'bitget':
            await query.edit_message_text(
                f"Connecting to {EXCHANGES[exchange_name]['name']}:\n\n"
                "Please send your credentials in format:\n"
                "<api_key> <api_secret> <passphrase>\n\n"
                "Note: Passphrase is required for Bitget"
            )
        else:
            await query.edit_message_text(
                f"Connecting to {EXCHANGES[exchange_name]['name']}:\n\n"
                "Please send your API Key and Secret in format:\n"
                "<api_key> <api_secret>"
            )

async def handle_credentials(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    try:
        exchange_name = context.user_data.get('selected_exchange')
        
        if not exchange_name:
            await update.message.reply_text("❌ Please start with /connect first")
            return
        
        credentials = update.message.text.split()
        if len(credentials) < 2:
            await update.message.reply_text("❌ Invalid format. Please provide at least API key and secret.")
            return
            
        api_key = credentials[0]
        api_secret = credentials[1]
        passphrase = credentials[2] if len(credentials) > 2 else ""
        
        # Encrypt credentials
        encrypted_key = cipher_suite.encrypt(api_key.encode())
        encrypted_secret = cipher_suite.encrypt(api_secret.encode())
        encrypted_passphrase = cipher_suite.encrypt(passphrase.encode()) if passphrase else b''
        
        # Save to database
        conn = sqlite3.connect('trading_bot.db')
        c = conn.cursor()
        user_db_id = get_user(user_id)
        
        c.execute('''INSERT INTO exchanges 
                  (user_id, exchange_name, api_key_encrypted, api_secret_encrypted, passphrase_encrypted) 
                  VALUES (?, ?, ?, ?, ?)''',
                  (user_db_id, exchange_name, encrypted_key, encrypted_secret, encrypted_passphrase))
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ {EXCHANGES[exchange_name]['name']} connected successfully!\n"
            "Test connection with /balance"
        )
        
        # Clear the selected exchange from user data
        context.user_data.pop('selected_exchange', None)
        
    except Exception as e:
        logger.error(f"Connection error: {e}")
        await update.message.reply_text("❌ Invalid credentials format. Please try again")

async def get_balance(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_db_id = get_user(user_id)
    
    if not user_db_id:
        await update.message.reply_text("❌ Please start the bot first with /start")
        return
    
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM exchanges WHERE user_id=?", (user_db_id,))
    exchanges = c.fetchall()
    conn.close()
    
    if not exchanges:
        await update.message.reply_text("❌ No connected exchanges. Use /connect first")
        return
    
    for exchange in exchanges:
        ex_id, _, ex_name, api_key_enc, api_sec_enc, passphrase_enc, _ = exchange
        
        try:
            # Decrypt credentials
            api_key = cipher_suite.decrypt(api_key_enc).decode()
            api_secret = cipher_suite.decrypt(api_sec_enc).decode()
            passphrase = cipher_suite.decrypt(passphrase_enc).decode() if passphrase_enc else ""
            
            # Get balance using exchange-specific method
            balance_method = EXCHANGES[ex_name]['balance_method']
            
            if balance_method == 'binance_balance':
                balance = await binance_balance(api_key, api_secret)
            elif balance_method == 'bybit_balance':
                balance = await bybit_balance(api_key, api_secret)
            elif balance_method == 'bitget_balance':
                balance = await bitget_balance(api_key, api_secret, passphrase)
            elif balance_method == 'mexc_balance':
                balance = await mexc_balance(api_key, api_secret)
            else:
                balance = "Not implemented"
            
            await update.message.reply_text(
                f"💰 {EXCHANGES[ex_name]['name']} Balance:\n"
                f"{balance} USDT"
            )
            
        except Exception as e:
            logger.error(f"Balance error for {ex_name}: {e}")
            await update.message.reply_text(
                f"❌ Failed to get {EXCHANGES[ex_name]['name']} balance\n"
                f"Error: {str(e)}"
            )

async def send_signal(update: Update, context: CallbackContext) -> None:
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Admin only command")
        return
    
    try:
        if len(context.args) < 5:
            raise ValueError("Not enough arguments")
            
        symbol = context.args[0]
        action = context.args[1].upper()
        entry = float(context.args[2])
        sl = float(context.args[3])
        tp = float(context.args[4])
        
        if action not in ['BUY', 'SELL']:
            raise ValueError("Invalid action. Use BUY or SELL")
        
        # Save to database
        conn = sqlite3.connect('trading_bot.db')
        c = conn.cursor()
        c.execute('''INSERT INTO signals 
                  (symbol, action, entry_price, stop_loss, take_profit, created_by) 
                  VALUES (?, ?, ?, ?, ?, ?)''',
                  (symbol, action, entry, sl, tp, ADMIN_ID))
        signal_id = c.lastrowid
        
        # Get subscribers
        c.execute('''SELECT users.telegram_id 
                  FROM users 
                  JOIN subscriptions ON users.id = subscriptions.user_id
                  WHERE is_subscribed = 1''')
        subscribers = [row[0] for row in c.fetchall()]
        conn.close()
        
        # Format signal message
        signal_msg = (
            "🚀 **NEW TRADING SIGNAL** 🚀\n\n"
            f"• Pair: {symbol}\n"
            f"• Action: {action}\n"
            f"• Entry: ${entry:,}\n"
            f"• Stop Loss: ${sl:,}\n"
            f"• Take Profit: ${tp:,}"
        )
        
        # Send to subscribers
        sent_count = 0
        for user_id in subscribers:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=signal_msg,
                    parse_mode='Markdown'
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Signal send error to {user_id}: {e}")
        
        await update.message.reply_text(f"✅ Signal sent to {sent_count}/{len(subscribers)} subscribers!")
        
    except Exception as e:
        logger.error(f"Signal error: {e}")
        await update.message.reply_text(
            "❌ Invalid format. Use:\n"
            "`/signal SYMBOL ACTION ENTRY SL TP`\n"
            "Example: `/signal BTCUSDT BUY 35000 34000 36000`",
            parse_mode='Markdown'
        )

async def subscribe(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    user_db_id = get_user(user_id)
    
    if not user_db_id:
        await update.message.reply_text("❌ Please start the bot first with /start")
        return
    
    conn = sqlite3.connect('trading_bot.db')
    c = conn.cursor()
    c.execute("UPDATE subscriptions SET is_subscribed=1 WHERE user_id=?", (user_db_id,))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        "✅ You're now subscribed to trading signals!\n"
        "You'll receive all trade alerts from the admin."
    )

def main() -> None:
    try:
        # Initialize database
        init_db()
        
        # Create Telegram application
        application = Application.builder().token(TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("connect", connect_exchange))
        application.add_handler(CommandHandler("balance", get_balance))
        application.add_handler(CommandHandler("signal", send_signal))
        application.add_handler(CommandHandler("subscribe", subscribe))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(exchange_callback))
        
        # Message handlers
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_credentials
        ))
        
        # Start bot
        logger.info("🚀 Starting trading bot...")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Bot startup failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
