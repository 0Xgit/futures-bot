import os
import json
import time
import hmac
import hashlib
import base64
import requests
from urllib.parse import urlencode, parse_qs
from cryptography.fernet import Fernet
import sqlite3
from typing import Dict, Optional, Tuple

class ExchangeAuthManager:
    """Handles automatic exchange authorization and API key management"""
    
    def __init__(self, encryption_key: bytes):
        self.cipher_suite = Fernet(encryption_key)
        self.auth_sessions = {}  # Store temporary auth sessions
        
    def generate_auth_url(self, exchange: str, user_id: int, callback_url: str) -> Optional[str]:
        """Generate authorization URL for supported exchanges"""
        
        if exchange == 'binance':
            return self._binance_auth_url(user_id, callback_url)
        elif exchange == 'bybit':
            return self._bybit_auth_url(user_id, callback_url)
        elif exchange == 'bitget':
            return self._bitget_auth_url(user_id, callback_url)
        elif exchange == 'kucoin':
            return self._kucoin_auth_url(user_id, callback_url)
        else:
            return None
    
    def _binance_auth_url(self, user_id: int, callback_url: str) -> str:
        """Generate Binance OAuth URL"""
        # Binance doesn't have traditional OAuth, but we can use their API key creation flow
        # This would redirect to a custom page that guides users through API creation
        
        state = self._generate_state_token(user_id, 'binance')
        params = {
            'response_type': 'code',
            'client_id': os.getenv('BINANCE_CLIENT_ID', 'your_app_id'),
            'redirect_uri': callback_url,
            'state': state,
            'scope': 'read,trade'  # Request necessary permissions
        }
        
        # Note: Binance doesn't have OAuth, so this would be a custom implementation
        base_url = "https://accounts.binance.com/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"
    
    def _bybit_auth_url(self, user_id: int, callback_url: str) -> str:
        """Generate Bybit OAuth URL"""
        state = self._generate_state_token(user_id, 'bybit')
        params = {
            'client_id': os.getenv('BYBIT_CLIENT_ID'),
            'response_type': 'code',
            'redirect_uri': callback_url,
            'state': state,
            'scope': 'read,trade'
        }
        
        base_url = "https://api.bybit.com/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"
    
    def _bitget_auth_url(self, user_id: int, callback_url: str) -> str:
        """Generate Bitget OAuth URL"""
        state = self._generate_state_token(user_id, 'bitget')
        params = {
            'client_id': os.getenv('BITGET_CLIENT_ID'),
            'response_type': 'code',
            'redirect_uri': callback_url,
            'state': state,
            'scope': 'read,trade'
        }
        
        base_url = "https://api.bitget.com/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"
    
    def _kucoin_auth_url(self, user_id: int, callback_url: str) -> str:
        """Generate KuCoin OAuth URL (KuCoin has proper OAuth support)"""
        state = self._generate_state_token(user_id, 'kucoin')
        params = {
            'client_id': os.getenv('KUCOIN_CLIENT_ID'),
            'response_type': 'code',
            'redirect_uri': callback_url,
            'state': state,
            'scope': 'General,Trade'
        }
        
        base_url = "https://api.kucoin.com/oauth/authorize"
        return f"{base_url}?{urlencode(params)}"
    
    def _generate_state_token(self, user_id: int, exchange: str) -> str:
        """Generate secure state token for OAuth"""
        import secrets
        state_data = {
            'user_id': user_id,
            'exchange': exchange,
            'timestamp': int(time.time()),
            'nonce': secrets.token_hex(16)
        }
        
        state_json = json.dumps(state_data)
        state_token = base64.urlsafe_b64encode(state_json.encode()).decode()
        
        # Store in temporary session
        self.auth_sessions[state_token] = state_data
        
        return state_token
    
    async def handle_oauth_callback(self, code: str, state: str) -> Dict:
        """Handle OAuth callback and exchange code for tokens"""
        
        if state not in self.auth_sessions:
            raise ValueError("Invalid or expired state token")
        
        session_data = self.auth_sessions[state]
        exchange = session_data['exchange']
        user_id = session_data['user_id']
        
        try:
            if exchange == 'kucoin':
                return await self._kucoin_exchange_code(code, user_id)
            elif exchange == 'bybit':
                return await self._bybit_exchange_code(code, user_id)
            elif exchange == 'bitget':
                return await self._bitget_exchange_code(code, user_id)
            else:
                raise ValueError(f"OAuth not supported for {exchange}")
        finally:
            # Clean up session
            self.auth_sessions.pop(state, None)
    
    async def _kucoin_exchange_code(self, code: str, user_id: int) -> Dict:
        """Exchange authorization code for KuCoin access token"""
        
        token_url = "https://api.kucoin.com/oauth/token"
        data = {
            'grant_type': 'authorization_code',
            'client_id': os.getenv('KUCOIN_CLIENT_ID'),
            'client_secret': os.getenv('KUCOIN_CLIENT_SECRET'),
            'code': code,
            'redirect_uri': os.getenv('OAUTH_CALLBACK_URL')
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            
            # Store encrypted tokens
            access_token = token_data['access_token']
            refresh_token = token_data.get('refresh_token', '')
            
            await self._store_oauth_tokens(user_id, 'kucoin', access_token, refresh_token)
            
            return {
                'success': True,
                'exchange': 'kucoin',
                'message': 'KuCoin connected successfully via OAuth'
            }
        else:
            raise Exception(f"Token exchange failed: {response.text}")
    
    async def _store_oauth_tokens(self, user_id: int, exchange: str, access_token: str, refresh_token: str = ''):
        """Store OAuth tokens securely in database"""
        
        encrypted_access = self.cipher_suite.encrypt(access_token.encode())
        encrypted_refresh = self.cipher_suite.encrypt(refresh_token.encode()) if refresh_token else b''
        
        conn = sqlite3.connect('trading_bot.db')
        c = conn.cursor()
        
        # Create OAuth tokens table if not exists
        c.execute('''CREATE TABLE IF NOT EXISTS oauth_tokens (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            exchange_name TEXT,
            access_token_encrypted TEXT,
            refresh_token_encrypted TEXT,
            expires_at INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )''')
        
        # Calculate expiration (usually 1 hour for access tokens)
        expires_at = int(time.time()) + 3600
        
        c.execute('''INSERT INTO oauth_tokens 
                  (user_id, exchange_name, access_token_encrypted, refresh_token_encrypted, expires_at) 
                  VALUES (?, ?, ?, ?, ?)''',
                  (user_id, exchange, encrypted_access, encrypted_refresh, expires_at))
        
        conn.commit()
        conn.close()

class AutoAPIKeyGenerator:
    """Generate API keys programmatically for supported exchanges"""
    
    def __init__(self, encryption_key: bytes):
        self.cipher_suite = Fernet(encryption_key)
    
    async def create_binance_api_key(self, master_key: str, master_secret: str, user_id: int) -> Dict:
        """Create sub-account API key for Binance (requires master account)"""
        
        try:
            from binance.client import Client
            
            # Initialize master client
            master_client = Client(master_key, master_secret)
            
            # Create sub-account
            sub_account_email = f"user_{user_id}_{int(time.time())}@yourdomain.com"
            
            # Note: This requires Binance Broker API or Sub-Account API
            sub_account = master_client.create_sub_account(email=sub_account_email)
            
            # Create API key for sub-account
            api_key_response = master_client.create_sub_account_api_key(
                email=sub_account_email,
                canTrade=True,
                marginTrade=False,
                futuresTrade=True
            )
            
            api_key = api_key_response['apiKey']
            secret_key = api_key_response['secretKey']
            
            # Store encrypted credentials
            await self._store_generated_keys(user_id, 'binance', api_key, secret_key)
            
            return {
                'success': True,
                'exchange': 'binance',
                'api_key': api_key,
                'message': 'Binance API key created successfully'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def create_bybit_api_key(self, master_key: str, master_secret: str, user_id: int) -> Dict:
        """Create API key for Bybit using master account"""
        
        try:
            # Bybit API key creation endpoint
            url = "https://api.bybit.com/v5/user/create-sub-api-key"
            
            timestamp = str(int(time.time() * 1000))
            
            params = {
                'api_key': master_key,
                'timestamp': timestamp,
                'readOnly': 0,
                'unified': 1,
                'uta': 1,
                'note': f'Auto-generated for user {user_id}'
            }
            
            # Create signature
            param_str = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = hmac.new(
                master_secret.encode('utf-8'),
                param_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': master_key,
                'X-BAPI-SIGN': signature,
                'X-BAPI-TIMESTAMP': timestamp,
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=params, headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                if result['retCode'] == 0:
                    api_data = result['result']
                    api_key = api_data['apiKey']
                    secret = api_data['secret']
                    
                    await self._store_generated_keys(user_id, 'bybit', api_key, secret)
                    
                    return {
                        'success': True,
                        'exchange': 'bybit',
                        'api_key': api_key,
                        'message': 'Bybit API key created successfully'
                    }
            
            return {
                'success': False,
                'error': 'Failed to create Bybit API key'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _store_generated_keys(self, user_id: int, exchange: str, api_key: str, secret: str, passphrase: str = ''):
        """Store generated API keys in database"""
        
        encrypted_key = self.cipher_suite.encrypt(api_key.encode())
        encrypted_secret = self.cipher_suite.encrypt(secret.encode())
        encrypted_passphrase = self.cipher_suite.encrypt(passphrase.encode()) if passphrase else b''
        
        conn = sqlite3.connect('trading_bot.db')
        c = conn.cursor()
        
        c.execute('''INSERT INTO exchanges 
                  (user_id, exchange_name, api_key_encrypted, api_secret_encrypted, passphrase_encrypted) 
                  VALUES (?, ?, ?, ?, ?)''',
                  (user_id, exchange, encrypted_key, encrypted_secret, encrypted_passphrase))
        
        conn.commit()
        conn.close()

# Integration with main bot
class EnhancedExchangeConnector:
    """Enhanced exchange connector with auto-auth capabilities"""
    
    def __init__(self, encryption_key: bytes):
        self.auth_manager = ExchangeAuthManager(encryption_key)
        self.api_generator = AutoAPIKeyGenerator(encryption_key)
        self.base_callback_url = os.getenv('OAUTH_CALLBACK_URL', 'https://yourdomain.com/oauth/callback')
    
    async def initiate_auto_connection(self, exchange: str, user_id: int, method: str = 'oauth') -> Dict:
        """Initiate automatic exchange connection"""
        
        if method == 'oauth':
            auth_url = self.auth_manager.generate_auth_url(exchange, user_id, self.base_callback_url)
            if auth_url:
                return {
                    'success': True,
                    'method': 'oauth',
                    'auth_url': auth_url,
                    'message': f'Click the link to authorize {exchange.title()}'
                }
            else:
                return {
                    'success': False,
                    'error': f'OAuth not supported for {exchange}'
                }
        
        elif method == 'auto_api':
            # This requires master API keys to be configured
            master_key = os.getenv(f'{exchange.upper()}_MASTER_KEY')
            master_secret = os.getenv(f'{exchange.upper()}_MASTER_SECRET')
            
            if not master_key or not master_secret:
                return {
                    'success': False,
                    'error': 'Master API keys not configured for auto-generation'
                }
            
            if exchange == 'binance':
                return await self.api_generator.create_binance_api_key(master_key, master_secret, user_id)
            elif exchange == 'bybit':
                return await self.api_generator.create_bybit_api_key(master_key, master_secret, user_id)
            else:
                return {
                    'success': False,
                    'error': f'Auto API key generation not supported for {exchange}'
                }
        
        else:
            return {
                'success': False,
                'error': 'Invalid connection method'
            }
    
    async def handle_oauth_return(self, code: str, state: str) -> Dict:
        """Handle OAuth callback"""
        return await self.auth_manager.handle_oauth_callback(code, state)

# Usage example functions
async def demo_oauth_flow():
    """Demonstrate OAuth flow"""
    
    encryption_key = Fernet.generate_key()
    connector = EnhancedExchangeConnector(encryption_key)
    
    # Initiate OAuth for KuCoin
    result = await connector.initiate_auto_connection('kucoin', user_id=12345, method='oauth')
    
    if result['success']:
        print(f"OAuth URL: {result['auth_url']}")
        print("User should visit this URL to authorize the application")
        
        # Simulate callback handling (in real implementation, this comes from webhook)
        # code = "received_from_callback"
        # state = "received_from_callback"
        # callback_result = await connector.handle_oauth_return(code, state)
        # print(f"Callback result: {callback_result}")

async def demo_auto_api_generation():
    """Demonstrate automatic API key generation"""
    
    encryption_key = Fernet.generate_key()
    connector = EnhancedExchangeConnector(encryption_key)
    
    # Auto-generate API key for Binance
    result = await connector.initiate_auto_connection('binance', user_id=12345, method='auto_api')
    
    if result['success']:
        print(f"API Key created: {result['api_key']}")
        print("User can now trade automatically")
    else:
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    import asyncio
    
    print("OAuth Flow Demo:")
    asyncio.run(demo_oauth_flow())
    
    print("\nAuto API Generation Demo:")
    asyncio.run(demo_auto_api_generation())
