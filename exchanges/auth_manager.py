import json
import time
import hmac
import hashlib
import base64
import secrets
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import requests
import sqlite3
import asyncio
import logging

logger = logging.getLogger(__name__)

class ExchangeAuthManager:
    def __init__(self, encryption_key: str):
        """Initialize with encryption key"""
        self.fernet = self._setup_encryption(encryption_key)
        self.auth_sessions = {}
    
    def _setup_encryption(self, key: str) -> Fernet:
        """Set up encryption with key derivation"""
        try:
            # Use key derivation to get a proper length key
            salt = b'trading_bot_salt'  # Fixed salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
            return Fernet(derived_key)
        except Exception as e:
            logger.error(f"Encryption setup error: {e}")
            raise
    
    def encrypt_credentials(self, api_key: str, api_secret: str, 
                           passphrase: str = '') -> Tuple[bytes, bytes, bytes]:
        """Encrypt API credentials"""
        try:
            encrypted_key = self.fernet.encrypt(api_key.encode())
            encrypted_secret = self.fernet.encrypt(api_secret.encode())
            encrypted_passphrase = self.fernet.encrypt(passphrase.encode()) if passphrase else b''
            
            return encrypted_key, encrypted_secret, encrypted_passphrase
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise
    
    def decrypt_credentials(self, encrypted_key: bytes, encrypted_secret: bytes,
                           encrypted_passphrase: bytes = b'') -> Tuple[str, str, str]:
        """Decrypt API credentials"""
        try:
            api_key = self.fernet.decrypt(encrypted_key).decode()
            api_secret = self.fernet.decrypt(encrypted_secret).decode()
            passphrase = self.fernet.decrypt(encrypted_passphrase).decode() if encrypted_passphrase else ''
            
            return api_key, api_secret, passphrase
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise
    
    def generate_oauth_url(self, exchange: str, user_id: int, callback_url: str) -> Optional[str]:
        """Generate OAuth URL for exchange"""
        try:
            # Currently only implemented for specific exchanges
            if exchange == 'kucoin':
                # Example KuCoin OAuth implementation
                base_url = 'https://www.kucoin.com/oauth2/authorize'
                params = {
                    'client_id': os.getenv('KUCOIN_CLIENT_ID', ''),
                    'response_type': 'code',
                    'redirect_uri': callback_url,
                    'state': f'user_{user_id}',
                    'scope': 'trade:futures,read:futures'
                }
                return f"{base_url}?{urlencode(params)}"
            else:
                logger.warning(f"OAuth not implemented for {exchange}")
                return None
        except Exception as e:
            logger.error(f"OAuth URL generation error: {e}")
            return None
    
    def _generate_state_token(self, user_id: int, exchange: str) -> str:
        """Generate secure state token for OAuth"""
        state_data = {
            'user_id': user_id,
            'exchange': exchange,
            'timestamp': int(time.time()),
            'nonce': secrets.token_hex(16)
        }
        
        state_json = json.dumps(state_data)
        state_token = base64.urlsafe_b64encode(state_json.encode()).decode()
        
        # Store in temporary session (expires in 10 minutes)
        self.auth_sessions[state_token] = {
            **state_data,
            'expires_at': int(time.time()) + 600
        }
        
        return state_token
    
    def validate_state_token(self, state: str) -> Optional[Dict]:
        """Validate and return state token data"""
        if state not in self.auth_sessions:
            return None
        
        session_data = self.auth_sessions[state]
        
        # Check if expired
        if int(time.time()) > session_data['expires_at']:
            self.auth_sessions.pop(state, None)
            return None
        
        return session_data
    
    def cleanup_expired_sessions(self):
        """Clean up expired auth sessions"""
        current_time = int(time.time())
        expired_sessions = [
            state for state, data in self.auth_sessions.items()
            if current_time > data['expires_at']
        ]
        
        for state in expired_sessions:
            self.auth_sessions.pop(state, None)

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
            elif exchange == 'okx':
                return await self._okx_exchange_code(code, user_id)
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

    async def _bybit_exchange_code(self, code: str, user_id: int) -> Dict:
        """Exchange authorization code for Bybit access token"""
        
        token_url = "https://api.bybit.com/oauth/token"
        data = {
            'grant_type': 'authorization_code',
            'client_id': os.getenv('BYBIT_CLIENT_ID'),
            'client_secret': os.getenv('BYBIT_CLIENT_SECRET'),
            'code': code,
            'redirect_uri': os.getenv('OAUTH_CALLBACK_URL')
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            
            access_token = token_data['access_token']
            refresh_token = token_data.get('refresh_token', '')
            
            await self._store_oauth_tokens(user_id, 'bybit', access_token, refresh_token)
            
            return {
                'success': True,
                'exchange': 'bybit',
                'message': 'Bybit connected successfully via OAuth'
            }
        else:
            raise Exception(f"Token exchange failed: {response.text}")

    async def _okx_exchange_code(self, code: str, user_id: int) -> Dict:
        """Exchange authorization code for OKX access token"""
        
        token_url = "https://www.okx.com/oauth/token"
        data = {
            'grant_type': 'authorization_code',
            'client_id': os.getenv('OKX_CLIENT_ID'),
            'client_secret': os.getenv('OKX_CLIENT_SECRET'),
            'code': code,
            'redirect_uri': os.getenv('OAUTH_CALLBACK_URL')
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            
            access_token = token_data['access_token']
            refresh_token = token_data.get('refresh_token', '')
            
            await self._store_oauth_tokens(user_id, 'okx', access_token, refresh_token)
            
            return {
                'success': True,
                'exchange': 'okx',
                'message': 'OKX connected successfully via OAuth'
            }
        else:
            raise Exception(f"Token exchange failed: {response.text}")

    async def _store_oauth_tokens(self, user_id: int, exchange: str, access_token: str, refresh_token: str = ''):
        """Store OAuth tokens securely in database"""
        
        encrypted_access = self.fernet.encrypt(access_token.encode())
        encrypted_refresh = self.fernet.encrypt(refresh_token.encode()) if refresh_token else b''
        
        conn = sqlite3.connect('data/trading_bot.db')
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

    async def refresh_oauth_token(self, user_id: int, exchange: str) -> bool:
        """Refresh OAuth token for a user and exchange"""
        
        conn = sqlite3.connect('data/trading_bot.db')
        c = conn.cursor()
        
        # Get refresh token
        c.execute('''SELECT refresh_token_encrypted FROM oauth_tokens 
                     WHERE user_id = ? AND exchange_name = ?''', (user_id, exchange))
        result = c.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return False
        
        refresh_token = self.fernet.decrypt(result[0]).decode()
        
        try:
            if exchange == 'kucoin':
                new_tokens = await self._refresh_kucoin_token(refresh_token)
            elif exchange == 'bybit':
                new_tokens = await self._refresh_bybit_token(refresh_token)
            elif exchange == 'okx':
                new_tokens = await self._refresh_okx_token(refresh_token)
            else:
                conn.close()
                return False
            
            # Update tokens in database
            encrypted_access = self.fernet.encrypt(new_tokens['access_token'].encode())
            encrypted_refresh = self.fernet.encrypt(new_tokens.get('refresh_token', refresh_token).encode())
            expires_at = int(time.time()) + 3600
            
            c.execute('''UPDATE oauth_tokens 
                         SET access_token_encrypted = ?, refresh_token_encrypted = ?, expires_at = ?
                         WHERE user_id = ? AND exchange_name = ?''',
                      (encrypted_access, encrypted_refresh, expires_at, user_id, exchange))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            conn.close()
            return False

    async def _refresh_kucoin_token(self, refresh_token: str) -> Dict:
        """Refresh KuCoin OAuth token"""
        
        token_url = "https://api.kucoin.com/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'client_id': os.getenv('KUCOIN_CLIENT_ID'),
            'client_secret': os.getenv('KUCOIN_CLIENT_SECRET'),
            'refresh_token': refresh_token
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token refresh failed: {response.text}")

    async def _refresh_bybit_token(self, refresh_token: str) -> Dict:
        """Refresh Bybit OAuth token"""
        
        token_url = "https://api.bybit.com/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'client_id': os.getenv('BYBIT_CLIENT_ID'),
            'client_secret': os.getenv('BYBIT_CLIENT_SECRET'),
            'refresh_token': refresh_token
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token refresh failed: {response.text}")

    async def _refresh_okx_token(self, refresh_token: str) -> Dict:
        """Refresh OKX OAuth token"""
        
        token_url = "https://www.okx.com/oauth/token"
        data = {
            'grant_type': 'refresh_token',
            'client_id': os.getenv('OKX_CLIENT_ID'),
            'client_secret': os.getenv('OKX_CLIENT_SECRET'),
            'refresh_token': refresh_token
        }
        
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Token refresh failed: {response.text}")

    def get_oauth_token(self, user_id: int, exchange: str) -> Optional[str]:
        """Get valid OAuth token for user and exchange"""
        
        conn = sqlite3.connect('data/trading_bot.db')
        c = conn.cursor()
        
        c.execute('''SELECT access_token_encrypted, expires_at FROM oauth_tokens 
                     WHERE user_id = ? AND exchange_name = ?''', (user_id, exchange))
        result = c.fetchone()
        conn.close()
        
        if not result:
            return None
        
        access_token_encrypted, expires_at = result
        
        # Check if token is expired
        if int(time.time()) >= expires_at:
            # Try to refresh token
            if asyncio.run(self.refresh_oauth_token(user_id, exchange)):
                # Get new token
                conn = sqlite3.connect('data/trading_bot.db')
                c = conn.cursor()
                c.execute('''SELECT access_token_encrypted FROM oauth_tokens 
                             WHERE user_id = ? AND exchange_name = ?''', (user_id, exchange))
                result = c.fetchone()
                conn.close()
                
                if result:
                    access_token_encrypted = result[0]
                else:
                    return None
            else:
                return None
        
        return self.fernet.decrypt(access_token_encrypted).decode()
