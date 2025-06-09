# Enhanced Telegram bot with auto-connection features

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from exchange_auth_manager import EnhancedExchangeConnector
import os
from cryptography.fernet import Fernet

# Initialize enhanced connector
ENCRYPTION_KEY = Fernet.generate_key()
exchange_connector = EnhancedExchangeConnector(ENCRYPTION_KEY)

async def connect_exchange_enhanced(update: Update, context: CallbackContext) -> None:
    """Enhanced exchange connection with auto-auth options"""
    
    keyboard = []
    
    # OAuth supported exchanges
    oauth_exchanges = ['kucoin', 'bybit']  # Add more as supported
    for exchange in oauth_exchanges:
        keyboard.append([
            InlineKeyboardButton(
                f"🔗 {exchange.title()} (OAuth)",
                callback_data=f"oauth_{exchange}"
            )
        ])
    
    # Auto API key generation (if master keys configured)
    auto_api_exchanges = ['binance', 'bybit']
    for exchange in auto_api_exchanges:
        if os.getenv(f'{exchange.upper()}_MASTER_KEY'):
            keyboard.append([
                InlineKeyboardButton(
                    f"🤖 {exchange.title()} (Auto)",
                    callback_data=f"auto_api_{exchange}"
                )
            ])
    
    # Manual connection option
    keyboard.append([
        InlineKeyboardButton(
            "📝 Manual Connection",
            callback_data="manual_connect"
        )
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '🔐 Choose connection method:\n\n'
        '🔗 OAuth: Secure authorization without sharing API keys\n'
        '🤖 Auto: Automatic API key generation\n'
        '📝 Manual: Traditional API key input',
        reply_markup=reply_markup
    )

async def enhanced_exchange_callback(update: Update, context: CallbackContext) -> None:
    """Handle enhanced exchange connection callbacks"""
    
    query = update.callback_query
    await query.answer()
    data = query.data.split('_')
    
    method = data[0]  # oauth, auto_api, or manual
    exchange = data[1] if len(data) > 1 else None
    user_id = update.effective_user.id
    
    if method == 'oauth':
        result = await exchange_connector.initiate_auto_connection(
            exchange, user_id, method='oauth'
        )
        
        if result['success']:
            keyboard = [[InlineKeyboardButton(
                "🔗 Authorize Now",
                url=result['auth_url']
            )]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"✅ {result['message']}\n\n"
                "Click the button below to authorize the connection.\n"
                "You'll be redirected back automatically after authorization.",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text(f"❌ {result['error']}")
    
    elif method == 'auto' and len(data) > 2 and data[2] == 'api':
        # Handle auto_api callback
        exchange = data[1]
        result = await exchange_connector.initiate_auto_connection(
            exchange, user_id, method='auto_api'
        )
        
        if result['success']:
            await query.edit_message_text(
                f"✅ {result['message']}\n\n"
                f"🔑 API Key: `{result['api_key'][:8]}...`\n"
                "Your account is now connected and ready for trading!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(f"❌ {result['error']}")
    
    elif method == 'manual':
        # Fall back to manual connection
        await show_manual_exchanges(query)

async def show_manual_exchanges(query):
    """Show manual exchange selection"""
    
    exchanges = ['binance', 'bybit', 'bitget', 'mexc']
    keyboard = []
    
    for exchange in exchanges:
        keyboard.append([InlineKeyboardButton(
            exchange.title(),
            callback_data=f"connect_{exchange}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        'Select exchange for manual connection:',
        reply_markup=reply_markup
    )

# OAuth callback handler (webhook endpoint)
async def oauth_callback_handler(request):
    """Handle OAuth callbacks from exchanges"""
    
    code = request.args.get('code')
    state = request.args.get('state')
    
    if not code or not state:
        return {'error': 'Missing code or state parameter'}
    
    try:
        result = await exchange_connector.handle_oauth_return(code, state)
        
        if result['success']:
            # Notify user via Telegram
            user_id = result.get('user_id')  # Extract from state
            if user_id:
                await send_telegram_message(
                    user_id,
                    f"✅ {result['message']}\n"
                    "Your exchange account is now connected!"
                )
            
            return {'success': True, 'message': 'Connection successful'}
        else:
            return {'error': result.get('error', 'Connection failed')}
    
    except Exception as e:
        return {'error': str(e)}

async def send_telegram_message(user_id: int, message: str):
    """Send message to Telegram user"""
    # Implementation depends on your bot setup
    pass
