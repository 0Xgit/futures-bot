import asyncio
import requests
import time
import hmac
import hashlib
import base64
import json
import logging
import ccxt
from typing import Dict, Any, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class BalanceChecker:
    @staticmethod
    async def get_balance(exchange_name: str, api_key: str, api_secret: str, passphrase: str = '') -> float:
        """Get USDT futures balance for specified exchange"""
        
        try:
            if exchange_name == 'binance':
                return await BalanceChecker._get_binance_futures_balance(api_key, api_secret)
            elif exchange_name == 'bybit':
                return await BalanceChecker._get_bybit_futures_balance(api_key, api_secret)
            elif exchange_name == 'okx':
                return await BalanceChecker._get_okx_futures_balance(api_key, api_secret, passphrase)
            elif exchange_name == 'bitget':
                return await BalanceChecker._get_bitget_futures_balance(api_key, api_secret, passphrase)
            elif exchange_name == 'mexc':
                return await BalanceChecker._get_mexc_futures_balance(api_key, api_secret)
            elif exchange_name == 'kucoin':
                return await BalanceChecker._get_kucoin_futures_balance(api_key, api_secret, passphrase)
            elif exchange_name == 'gate':
                return await BalanceChecker._get_gate_futures_balance(api_key, api_secret)
            elif exchange_name == 'huobi':
                return await BalanceChecker._get_huobi_futures_balance(api_key, api_secret)
            elif exchange_name == 'bingx':
                return await BalanceChecker._get_bingx_futures_balance(api_key, api_secret)
            else:
                # Initialize exchange
                exchange_class = getattr(ccxt, exchange_name)
                exchange_config = {
                    'apiKey': api_key,
                    'secret': api_secret,
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'future',  # Use futures wallet
                    }
                }
                
                # Add passphrase if required
                if passphrase:
                    exchange_config['password'] = passphrase
                
                exchange = exchange_class(exchange_config)
                
                # Load markets to ensure proper initialization
                await exchange.load_markets()
                
                # Get balance based on exchange
                balance = await exchange.fetch_balance()
                return float(balance.get('total', {}).get('USDT', 0))
        
        except Exception as e:
            logger.error(f"Error getting balance from {exchange_name}: {e}")
            raise Exception(f"Failed to get {exchange_name} futures balance: {str(e)}")
    
    @staticmethod
    async def _get_binance_futures_balance(api_key: str, api_secret: str) -> float:
        """Get Binance USDT-M Futures balance"""
        try:
            url = "https://fapi.binance.com/fapi/v2/account"
            timestamp = int(time.time() * 1000)
            
            params = {
                'timestamp': timestamp
            }
            
            query_string = urlencode(params)
            signature = hmac.new(
                api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            params['signature'] = signature
            
            headers = {
                'X-MBX-APIKEY': api_key
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                # Get USDT balance from futures account
                usdt_balance = float(data.get('totalWalletBalance', 0))
                return usdt_balance
            else:
                raise Exception(f"Binance API error: {response.text}")
                
        except Exception as e:
            logger.error(f"Error getting Binance balance: {e}")
            raise Exception(f"Binance futures API error: {str(e)}")
    
    @staticmethod
    async def _get_bybit_futures_balance(api_key: str, api_secret: str) -> float:
        """Get Bybit USDT Perpetual balance"""
        try:
            url = "https://api.bybit.com/v5/account/wallet-balance"
            timestamp = str(int(time.time() * 1000))
            
            params = {
                'accountType': 'UNIFIED'
            }
            
            param_str = urlencode(params)
            
            # Create signature
            sign_payload = timestamp + api_key + '5000' + param_str
            signature = hmac.new(
                api_secret.encode('utf-8'),
                sign_payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BAPI-API-KEY': api_key,
                'X-BAPI-SIGN': signature,
                'X-BAPI-TIMESTAMP': timestamp,
                'X-BAPI-RECV-WINDOW': '5000'
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['retCode'] == 0:
                    coins = data['result']['list'][0]['coin']
                    usdt_coin = next((coin for coin in coins if coin['coin'] == 'USDT'), None)
                    return float(usdt_coin['walletBalance']) if usdt_coin else 0.0
                else:
                    raise Exception(f"Bybit API error: {data['retMsg']}")
            else:
                raise Exception(f"Bybit HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting Bybit balance: {e}")
            raise Exception(f"Bybit futures API error: {str(e)}")
    
    @staticmethod
    async def _get_okx_futures_balance(api_key: str, api_secret: str, passphrase: str) -> float:
        """Get OKX futures balance"""
        try:
            url = "https://www.okx.com/api/v5/account/balance"
            timestamp = str(int(time.time()))
            
            # Create signature
            message = timestamp + 'GET' + '/api/v5/account/balance'
            signature = base64.b64encode(
                hmac.new(api_secret.encode('utf-8'), message.encode('utf-8'), hashlib.sha256).digest()
            ).decode()
            
            headers = {
                'OK-ACCESS-KEY': api_key,
                'OK-ACCESS-SIGN': signature,
                'OK-ACCESS-TIMESTAMP': timestamp,
                'OK-ACCESS-PASSPHRASE': passphrase,
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == '0':
                    balances = data['data'][0]['details']
                    usdt_balance = next((bal for bal in balances if bal['ccy'] == 'USDT'), None)
                    return float(usdt_balance['availBal']) if usdt_balance else 0.0
                else:
                    raise Exception(f"OKX API error: {data['msg']}")
            else:
                raise Exception(f"OKX HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting OKX balance: {e}")
            raise Exception(f"OKX futures API error: {str(e)}")
    
    @staticmethod
    async def _get_bitget_futures_balance(api_key: str, api_secret: str, passphrase: str) -> float:
        """Get Bitget futures balance"""
        try:
            url = "https://api.bitget.com/api/mix/v1/account/accounts"
            timestamp = str(int(time.time() * 1000))
            
            params = {
                'productType': 'umcbl'  # USDT-M futures
            }
            
            query_string = urlencode(params)
            message = timestamp + "GET" + "/api/mix/v1/account/accounts?" + query_string
            
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
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == '00000':
                    accounts = data['data']
                    usdt_account = next((acc for acc in accounts if acc['marginCoin'] == 'USDT'), None)
                    return float(usdt_account['available']) if usdt_account else 0.0
                else:
                    raise Exception(f"Bitget API error: {data['msg']}")
            else:
                raise Exception(f"Bitget HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting Bitget balance: {e}")
            raise Exception(f"Bitget futures API error: {str(e)}")
    
    @staticmethod
    async def _get_mexc_futures_balance(api_key: str, api_secret: str) -> float:
        """Get MEXC futures balance"""
        try:
            url = "https://contract.mexc.com/api/v1/private/account/assets"
            timestamp = str(int(time.time() * 1000))
            
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(
                api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                "ApiKey": api_key,
                "Request-Time": timestamp,
                "Signature": signature,
                "Content-Type": "application/json"
            }
            
            params = {
                "timestamp": timestamp
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    assets = data['data']
                    usdt_asset = next((asset for asset in assets if asset['currency'] == 'USDT'), None)
                    return float(usdt_asset['availableBalance']) if usdt_asset else 0.0
                else:
                    raise Exception(f"MEXC API error: {data.get('message', 'Unknown error')}")
            else:
                raise Exception(f"MEXC HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting MEXC balance: {e}")
            raise Exception(f"MEXC futures API error: {str(e)}")
    
    @staticmethod
    async def _get_kucoin_futures_balance(api_key: str, api_secret: str, passphrase: str) -> float:
        """Get KuCoin futures balance"""
        try:
            url = "https://api-futures.kucoin.com/api/v1/account-overview"
            timestamp = str(int(time.time() * 1000))
            
            str_to_sign = timestamp + 'GET' + '/api/v1/account-overview'
            signature = base64.b64encode(
                hmac.new(api_secret.encode('utf-8'), str_to_sign.encode('utf-8'), hashlib.sha256).digest()
            ).decode()
            
            passphrase_encrypted = base64.b64encode(
                hmac.new(api_secret.encode('utf-8'), passphrase.encode('utf-8'), hashlib.sha256).digest()
            ).decode()
            
            headers = {
                'KC-API-SIGN': signature,
                'KC-API-TIMESTAMP': timestamp,
                'KC-API-KEY': api_key,
                'KC-API-PASSPHRASE': passphrase_encrypted,
                'KC-API-KEY-VERSION': '2'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == '200000':
                    account_equity = float(data['data']['accountEquity'])
                    return account_equity
                else:
                    raise Exception(f"KuCoin API error: {data['msg']}")
            else:
                raise Exception(f"KuCoin HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting KuCoin balance: {e}")
            raise Exception(f"KuCoin futures API error: {str(e)}")
    
    @staticmethod
    async def _get_gate_futures_balance(api_key: str, api_secret: str) -> float:
        """Get Gate.io futures balance"""
        try:
            url = "https://api.gateio.ws/api/v4/futures/usdt/accounts"
            timestamp = str(int(time.time()))
            
            # Create signature for Gate.io
            query_string = ""
            body_hash = hashlib.sha512("".encode('utf-8')).hexdigest()
            sign_string = f"GET\n/api/v4/futures/usdt/accounts\n{query_string}\n{body_hash}\n{timestamp}"
            
            signature = hmac.new(
                api_secret.encode('utf-8'),
                sign_string.encode('utf-8'),
                hashlib.sha512
            ).hexdigest()
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'KEY': api_key,
                'Timestamp': timestamp,
                'SIGN': signature
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                available_balance = float(data.get('available', 0))
                return available_balance
            else:
                raise Exception(f"Gate.io HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting Gate.io balance: {e}")
            raise Exception(f"Gate.io futures API error: {str(e)}")
    
    @staticmethod
    async def _get_huobi_futures_balance(api_key: str, api_secret: str) -> float:
        """Get Huobi futures balance"""
        try:
            url = "https://api.hbdm.com/linear-swap-api/v1/swap_account_info"
            timestamp = str(int(time.time()))
            
            params = {
                'AccessKeyId': api_key,
                'SignatureMethod': 'HmacSHA256',
                'SignatureVersion': '2',
                'Timestamp': timestamp
            }
            
            # Create signature
            sorted_params = sorted(params.items())
            query_string = '&'.join([f"{k}={v}" for k, v in sorted_params])
            
            payload = f"GET\napi.hbdm.com\n/linear-swap-api/v1/swap_account_info\n{query_string}"
            signature = base64.b64encode(
                hmac.new(api_secret.encode('utf-8'), payload.encode('utf-8'), hashlib.sha256).digest()
            ).decode()
            
            params['Signature'] = signature
            
            response = requests.get(url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'ok':
                    accounts = data['data']
                    usdt_account = next((acc for acc in accounts if acc['margin_asset'] == 'USDT'), None)
                    return float(usdt_account['margin_balance']) if usdt_account else 0.0
                else:
                    raise Exception(f"Huobi API error: {data.get('err_msg', 'Unknown error')}")
            else:
                raise Exception(f"Huobi HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting Huobi balance: {e}")
            raise Exception(f"Huobi futures API error: {str(e)}")
    
    @staticmethod
    async def _get_bingx_futures_balance(api_key: str, api_secret: str) -> float:
        """Get BingX futures balance"""
        try:
            url = "https://open-api.bingx.com/openApi/swap/v2/user/balance"
            timestamp = str(int(time.time() * 1000))
            
            query_string = f"timestamp={timestamp}"
            signature = hmac.new(
                api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            headers = {
                'X-BX-APIKEY': api_key,
                'Content-Type': 'application/json'
            }
            
            params = {
                'timestamp': timestamp,
                'signature': signature
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data['code'] == 0:
                    balance_info = data['data']['balance']
                    available_margin = float(balance_info.get('availableMargin', 0))
                    return available_margin
                else:
                    raise Exception(f"BingX API error: {data['msg']}")
            else:
                raise Exception(f"BingX HTTP error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting BingX balance: {e}")
            raise Exception(f"BingX futures API error: {str(e)}")

    @staticmethod
    async def _get_binance_balance(exchange) -> float:
        """Get Binance futures balance"""
        try:
            balance = await exchange.fapiPrivateGetAccount()
            assets = balance.get('assets', [])
            for asset in assets:
                if asset.get('asset') == 'USDT':
                    return float(asset.get('walletBalance', 0))
            return 0
        except Exception as e:
            logger.error(f"Error getting Binance balance: {e}")
            raise
    
    @staticmethod
    async def _get_bybit_balance(exchange) -> float:
        """Get Bybit futures balance"""
        try:
            balance = await exchange.privateGetV2PrivateWalletBalance()
            result = balance.get('result', {})
            usdt = result.get('USDT', {})
            return float(usdt.get('wallet_balance', 0))
        except Exception as e:
            logger.error(f"Error getting Bybit balance: {e}")
            raise
    
    @staticmethod
    async def _get_okx_balance(exchange) -> float:
        """Get OKX futures balance"""
        try:
            balance = await exchange.privateGetAccountBalance()
            data = balance.get('data', [{}])[0]
            details = data.get('details', [])
            for detail in details:
                if detail.get('ccy') == 'USDT':
                    return float(detail.get('cashBal', 0))
            return 0
        except Exception as e:
            logger.error(f"Error getting OKX balance: {e}")
            raise
    
    @staticmethod
    async def _get_bitget_balance(exchange) -> float:
        """Get Bitget futures balance"""
        try:
            balance = await exchange.privateGetApiV3AccountAssets()
            assets = balance.get('data', [])
            for asset in assets:
                if asset.get('coinName') == 'USDT':
                    return float(asset.get('available', 0))
            return 0
        except Exception as e:
            logger.error(f"Error getting Bitget balance: {e}")
            raise
    
    @staticmethod
    async def _get_mexc_balance(exchange) -> float:
        """Get MEXC futures balance"""
        try:
            balance = await exchange.contractPrivateGetAccountAssets()
            assets = balance.get('data', [])
            for asset in assets:
                if asset.get('currency') == 'USDT':
                    return float(asset.get('marginAvailable', 0))
            return 0
        except Exception as e:
            logger.error(f"Error getting MEXC balance: {e}")
            raise
