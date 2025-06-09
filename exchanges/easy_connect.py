import os
import json
import qrcode
import io
import base64
from typing import Dict, List, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import logging

logger = logging.getLogger(__name__)

class EasyConnectManager:
    """Simplified exchange connection for normal users"""
    
    def __init__(self, auth_manager, db):
        self.auth_manager = auth_manager
        self.db = db
        self.user_profiles = {}
        
    def assess_user_level(self, answers: Dict) -> str:
        """Assess user experience level from simple questions"""
        score = 0
        
        # Question 1: Trading experience
        if answers.get('experience') == 'none':
            score += 0
        elif answers.get('experience') == 'some':
            score += 1
        elif answers.get('experience') == 'experienced':
            score += 2
            
        # Question 2: Risk tolerance
        if answers.get('risk') == 'low':
            score += 0
        elif answers.get('risk') == 'medium':
            score += 1
        elif answers.get('risk') == 'high':
            score += 2
            
        # Question 3: Technical comfort
        if answers.get('technical') == 'beginner':
            score += 0
        elif answers.get('technical') == 'intermediate':
            score += 1
        elif answers.get('technical') == 'advanced':
            score += 2
        
        if score <= 2:
            return 'beginner'
        elif score <= 4:
            return 'intermediate'
        else:
            return 'advanced'
    
    def get_recommended_exchange(self, user_level: str) -> str:
        """Recommend best exchange based on user level"""
        recommendations = {
            'beginner': 'binance',      # Most user-friendly
            'intermediate': 'bybit',    # Good features
            'advanced': 'okx'          # Advanced tools
        }
        return recommendations.get(user_level, 'binance')
    
    def get_safe_settings(self, user_level: str) -> Dict:
        """Get safe default settings for user level"""
        settings = {
            'beginner': {
                'leverage': 3,
                'position_size': 1.0,
                'stop_loss': True,
                'take_profit': True
            },
            'intermediate': {
                'leverage': 10,
                'position_size': 3.0,
                'stop_loss': True,
                'take_profit': True
            },
            'advanced': {
                'leverage': 20,
                'position_size': 5.0,
                'stop_loss': True,
                'take_profit': True
            }
        }
        return settings.get(user_level, settings['beginner'])
    
    def generate_mobile_qr(self, exchange: str, step: str) -> str:
        """Generate QR code for mobile setup steps"""
        try:
            # Create QR data
            qr_data = {
                'type': 'exchange_setup',
                'exchange': exchange,
                'step': step,
                'guide_url': f"https://your-domain.com/mobile-guide/{exchange}/{step}"
            }
            
            # Generate QR code
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(json.dumps(qr_data))
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return f"data:image/png;base64,{img_str}"
            
        except Exception as e:
            logger.error(f"QR generation error: {e}")
            return None
    
    def get_step_by_step_guide(self, exchange: str, user_level: str) -> List[Dict]:
        """Get detailed step-by-step setup guide"""
        
        guides = {
            'binance': [
                {
                    'step': 1,
                    'title': '📱 Open Binance App',
                    'description': 'Open the Binance app on your phone or visit binance.com',
                    'image': 'binance_step1.png',
                    'tips': ['Make sure you\'re logged into your account', 'Use the official Binance app only']
                },
                {
                    'step': 2,
                    'title': '⚙️ Go to API Management',
                    'description': 'Tap Profile → API Management → Create API',
                    'image': 'binance_step2.png',
                    'tips': ['Look for the gear icon in your profile', 'You might need to verify your identity']
                },
                {
                    'step': 3,
                    'title': '🔑 Create API Key',
                    'description': 'Name it "TradingBot" and enable only "Enable Futures"',
                    'image': 'binance_step3.png',
                    'tips': ['NEVER enable "Enable Withdrawals"', 'Only check "Enable Futures" box']
                },
                {
                    'step': 4,
                    'title': '📋 Copy Your Keys',
                    'description': 'Copy both API Key and Secret Key',
                    'image': 'binance_step4.png',
                    'tips': ['Save them somewhere safe temporarily', 'You\'ll need both keys']
                },
                {
                    'step': 5,
                    'title': '🤖 Send to Bot',
                    'description': 'Send both keys to this bot in format: API_KEY API_SECRET',
                    'image': 'binance_step5.png',
                    'tips': ['Separate the keys with a space', 'Send them in one message']
                }
            ],
            'bybit': [
                {
                    'step': 1,
                    'title': '📱 Open Bybit App',
                    'description': 'Open Bybit app or visit bybit.com',
                    'image': 'bybit_step1.png',
                    'tips': ['Make sure you\'re logged in', 'Use the official Bybit app']
                },
                {
                    'step': 2,
                    'title': '⚙️ Account Settings',
                    'description': 'Go to Account → API Management',
                    'image': 'bybit_step2.png',
                    'tips': ['Look for Account in the bottom menu', 'Find API Management section']
                },
                {
                    'step': 3,
                    'title': '🔑 Create New API',
                    'description': 'Click "Create New Key" and name it "TradingBot"',
                    'image': 'bybit_step3.png',
                    'tips': ['Choose a memorable name', 'This helps you identify the key later']
                },
                {
                    'step': 4,
                    'title': '✅ Set Permissions',
                    'description': 'Enable only "Contract Trading" and "Wallet"',
                    'image': 'bybit_step4.png',
                    'tips': ['NEVER enable "Asset Transfer"', 'Only trading permissions needed']
                },
                {
                    'step': 5,
                    'title': '📋 Copy Keys',
                    'description': 'Copy API Key and Secret Key',
                    'image': 'bybit_step5.png',
                    'tips': ['Both keys are needed', 'Keep them secure']
                },
                {
                    'step': 6,
                    'title': '🤖 Send to Bot',
                    'description': 'Send: API_KEY API_SECRET',
                    'image': 'bybit_step6.png',
                    'tips': ['One space between keys', 'Send in single message']
                }
            ]
        }
        
        return guides.get(exchange, [])
    
    def get_mobile_guide_url(self, exchange: str) -> str:
        """Get mobile-specific guide URL"""
        mobile_guides = {
            'binance': 'https://www.binance.com/en/support/faq/how-to-create-api-360002502072',
            'bybit': 'https://help.bybit.com/hc/en-us/articles/360039749613',
            'okx': 'https://www.okx.com/help-center/changes-to-v5-api-overview',
            'bitget': 'https://bitgetlimited.zendesk.com/hc/en-us/articles/360038485234'
        }
        return mobile_guides.get(exchange, '#')
    
    def create_connection_keyboard(self, exchange: str, user_level: str) -> InlineKeyboardMarkup:
        """Create smart keyboard based on user level and exchange capabilities"""
        
        keyboard = []
        
        # Auto-connect option (if available)
        if self.can_auto_connect(exchange):
            keyboard.append([InlineKeyboardButton(
                "🤖 Auto-Connect (30 seconds)",
                callback_data=f"auto_connect_{exchange}"
            )])
        
        # Guided setup (always available)
        keyboard.append([InlineKeyboardButton(
            "📋 Step-by-Step Guide (5 minutes)",
            callback_data=f"guided_setup_{exchange}"
        )])
        
        # Mobile setup
        keyboard.append([InlineKeyboardButton(
            "📱 Mobile Setup",
            callback_data=f"mobile_setup_{exchange}"
        )])
        
        # Video tutorial
        keyboard.append([InlineKeyboardButton(
            "🎥 Watch Video Tutorial",
            url=f"https://youtube.com/watch?v=tutorial_{exchange}"
        )])
        
        # Live help
        keyboard.append([InlineKeyboardButton(
            "🆘 Get Live Help",
            callback_data=f"live_help_{exchange}"
        )])
        
        # Back button
        keyboard.append([InlineKeyboardButton(
            "🔙 Choose Different Exchange",
            callback_data="back_to_exchanges"
        )])
        
        return InlineKeyboardMarkup(keyboard)
    
    def can_auto_connect(self, exchange: str) -> bool:
        """Check if auto-connect is available for exchange"""
        master_keys = {
            'binance': os.getenv('BINANCE_MASTER_KEY'),
            'bybit': os.getenv('BYBIT_MASTER_KEY'),
            'okx': os.getenv('OKX_MASTER_KEY')
        }
        return bool(master_keys.get(exchange))
    
    async def auto_connect_exchange(self, user_id: int, exchange: str) -> Dict:
        """Automatically connect exchange using master API"""
        try:
            # This would use the AutoAPIKeyGenerator from the previous implementation
            from exchanges.auth_manager import AutoAPIKeyGenerator
            
            generator = AutoAPIKeyGenerator(self.auth_manager.cipher_suite.key)
            
            master_key = os.getenv(f'{exchange.upper()}_MASTER_KEY')
            master_secret = os.getenv(f'{exchange.upper()}_MASTER_SECRET')
            
            if not master_key or not master_secret:
                return {'success': False, 'error': 'Auto-connect not configured'}
            
            if exchange == 'binance':
                result = await generator.create_binance_api_key(master_key, master_secret, user_id)
            elif exchange == 'bybit':
                result = await generator.create_bybit_api_key(master_key, master_secret, user_id)
            else:
                return {'success': False, 'error': 'Auto-connect not supported for this exchange'}
            
            return result
            
        except Exception as e:
            logger.error(f"Auto-connect error: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_success_message(self, exchange: str, method: str, balance: float = None) -> str:
        """Generate success message based on connection method"""
        
        base_message = f"🎉 *{exchange.title()} Connected Successfully!*\n\n"
        
        if method == 'auto':
            message = base_message + (
                "🤖 **AUTO-CONNECT COMPLETE**\n"
                "Your API keys were generated automatically and securely stored.\n\n"
            )
        elif method == 'guided':
            message = base_message + (
                "📋 **GUIDED SETUP COMPLETE**\n"
                "Great job following the step-by-step guide!\n\n"
            )
        elif method == 'mobile':
            message = base_message + (
                "📱 **MOBILE SETUP COMPLETE**\n"
                "Successfully connected via mobile app!\n\n"
            )
        else:
            message = base_message
        
        if balance is not None:
            message += f"💰 Current Balance: `{balance:,.2f} USDT`\n\n"
        
        message += (
            "✅ **What's Next:**\n"
            "• Use /subscribe to enable trading signals\n"
            "• Check /balance to see all your accounts\n"
            "• View /trades to monitor your performance\n"
            "• Adjust /settings for your preferences\n\n"
            "🔴 **LIVE TRADING ACTIVE** - Real money at risk!"
        )
        
        return message

class UserProfiler:
    """Simple user profiling system"""
    
    @staticmethod
    def get_profiling_questions() -> List[Dict]:
        """Get simple profiling questions"""
        return [
            {
                'id': 'experience',
                'question': '📊 How much trading experience do you have?',
                'options': [
                    {'text': '🆕 Complete beginner', 'value': 'none'},
                    {'text': '📈 Some experience', 'value': 'some'},
                    {'text': '💎 Very experienced', 'value': 'experienced'}
                ]
            },
            {
                'id': 'risk',
                'question': '🎯 What\'s your risk tolerance?',
                'options': [
                    {'text': '🛡️ Low risk (safe)', 'value': 'low'},
                    {'text': '⚖️ Medium risk (balanced)', 'value': 'medium'},
                    {'text': '🚀 High risk (aggressive)', 'value': 'high'}
                ]
            },
            {
                'id': 'technical',
                'question': '🔧 How comfortable are you with technology?',
                'options': [
                    {'text': '📱 Basic (just apps)', 'value': 'beginner'},
                    {'text': '💻 Good (websites, settings)', 'value': 'intermediate'},
                    {'text': '⚙️ Expert (APIs, coding)', 'value': 'advanced'}
                ]
            }
        ]
    
    @staticmethod
    def create_question_keyboard(question: Dict) -> InlineKeyboardMarkup:
        """Create keyboard for profiling question"""
        keyboard = []
        for option in question['options']:
            keyboard.append([InlineKeyboardButton(
                option['text'],
                callback_data=f"profile_{question['id']}_{option['value']}"
            )])
        return InlineKeyboardMarkup(keyboard)

class LiveSupportManager:
    """Manage live support requests"""
    
    def __init__(self):
        self.support_queue = []
        self.active_sessions = {}
    
    def create_support_request(self, user_id: int, exchange: str, issue: str) -> str:
        """Create new support request"""
        import uuid
        ticket_id = str(uuid.uuid4())[:8]
        
        request = {
            'ticket_id': ticket_id,
            'user_id': user_id,
            'exchange': exchange,
            'issue': issue,
            'status': 'pending',
            'created_at': time.time()
        }
        
        self.support_queue.append(request)
        return ticket_id
    
    def get_support_keyboard(self, exchange: str) -> InlineKeyboardMarkup:
        """Create support options keyboard"""
        keyboard = [
            [InlineKeyboardButton(
                "💬 Chat with Human Agent",
                callback_data=f"support_chat_{exchange}"
            )],
            [InlineKeyboardButton(
                "📞 Request Voice Call",
                callback_data=f"support_call_{exchange}"
            )],
            [InlineKeyboardButton(
                "🖥️ Screen Sharing Help",
                callback_data=f"support_screen_{exchange}"
            )],
            [InlineKeyboardButton(
                "📚 Check FAQ First",
                callback_data=f"support_faq_{exchange}"
            )]
        ]
        return InlineKeyboardMarkup(keyboard)
