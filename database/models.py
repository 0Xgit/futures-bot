import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import json
import sqlitecloud

class Database:
    def __init__(self):
        self.init_database()
    
    def get_connection(self):
        return sqlitecloud.connect(os.getenv("SQLITE_CLOUD"))
    
    def init_database(self):
        """Initialize all database tables"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_premium BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_active DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Exchange connections table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS exchanges (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                exchange_name TEXT NOT NULL,
                api_key_encrypted BLOB NOT NULL,
                api_secret_encrypted BLOB NOT NULL,
                passphrase_encrypted BLOB,
                connection_type TEXT DEFAULT 'manual',
                is_active BOOLEAN DEFAULT 1,
                auto_trade BOOLEAN DEFAULT 1,
                leverage INTEGER DEFAULT 10,
                position_size_percent REAL DEFAULT 5.0,
                balance REAL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                last_used DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Subscriptions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                is_subscribed BOOLEAN DEFAULT 1,
                auto_trade BOOLEAN DEFAULT 1,
                max_position_size REAL DEFAULT 5.0,
                use_stop_loss BOOLEAN DEFAULT 1,
                use_take_profit BOOLEAN DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Trading signals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY,
                symbol TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL,
                take_profit REAL,
                leverage INTEGER DEFAULT 10,
                position_size_percent REAL DEFAULT 5.0,
                status TEXT DEFAULT 'active',
                is_processed BOOLEAN DEFAULT 0,
                expires_at DATETIME,
                created_by INTEGER NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME,
                execution_results TEXT
            )
        ''')
        
        # Trade executions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trade_executions (
                id INTEGER PRIMARY KEY,
                signal_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                exchange_name TEXT NOT NULL,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                entry_price REAL NOT NULL,
                current_price REAL,
                pnl REAL DEFAULT 0,
                status TEXT DEFAULT 'open',
                order_id TEXT,
                executed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                closed_at DATETIME,
                FOREIGN KEY(signal_id) REFERENCES signals(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Portfolio tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolios (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                total_balance REAL DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                pnl_percentage REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                best_trade REAL DEFAULT 0,
                worst_trade REAL DEFAULT 0,
                average_trade REAL DEFAULT 0,
                first_trade_date DATETIME,
                last_updated DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')
        
        # Daily P&L tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_pnl (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                date DATE NOT NULL,
                pnl REAL DEFAULT 0,
                trades_count INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                UNIQUE(user_id, date)
            )
        ''')
        
        conn.commit()
        conn.close()

class UserModel:
    def __init__(self, db: Database):
        self.db = db
    
    def create_user(self, telegram_id: int, username: str = None, 
                   first_name: str = None, last_name: str = None) -> int:
        """Create new user and return user ID"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name) 
                VALUES (?, ?, ?, ?)
            ''', (telegram_id, username, first_name, last_name))
            user_id = cursor.lastrowid
            
            # Create default subscription
            cursor.execute('''
                INSERT INTO subscriptions (user_id) VALUES (?)
            ''', (user_id,))
            
            # Create portfolio record
            cursor.execute('''
                INSERT INTO portfolios (user_id) VALUES (?)
            ''', (user_id,))
            
            conn.commit()
            return user_id
        except sqlite3.IntegrityError:
            # User already exists, update last active
            cursor.execute('''
                UPDATE users SET last_active = CURRENT_TIMESTAMP 
                WHERE telegram_id = ?
            ''', (telegram_id,))
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            conn.commit()
            return cursor.fetchone()[0]
        finally:
            conn.close()
    
    def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Get user by telegram ID"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, telegram_id, username, first_name, last_name, 
                   is_premium, created_at, last_active
            FROM users WHERE telegram_id = ?
        ''', (telegram_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0], 'telegram_id': row[1], 'username': row[2],
                'first_name': row[3], 'last_name': row[4], 'is_premium': row[5],
                'created_at': row[6], 'last_active': row[7]
            }
        return None
    
    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, telegram_id, username, first_name, last_name, 
                   is_premium, created_at, last_active
            FROM users ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'telegram_id': row[1], 'username': row[2],
                'first_name': row[3], 'last_name': row[4], 'is_premium': row[5],
                'created_at': row[6], 'last_active': row[7]
            })
        return users
    
    def get_all_users_count(self) -> int:
        """Get total number of users"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_active_users_count(self, days: int = 7) -> int:
        """Get count of users active in last N days"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cutoff_date = datetime.now() - timedelta(days=days)
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE last_active >= ?
        ''', (cutoff_date,))
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_subscription(self, user_id: int) -> Optional[Dict]:
        """Get user subscription details"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT is_subscribed, auto_trade, max_position_size, 
                   use_stop_loss, use_take_profit
            FROM subscriptions WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'is_subscribed': row[0], 'auto_trade': row[1], 
                'max_position_size': row[2], 'use_stop_loss': row[3], 
                'use_take_profit': row[4]
            }
        return None
    
    def update_subscription(self, user_id: int, is_subscribed: bool, auto_trade: bool):
        """Update user subscription"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE subscriptions 
            SET is_subscribed = ?, auto_trade = ?
            WHERE user_id = ?
        ''', (is_subscribed, auto_trade, user_id))
        
        conn.commit()
        conn.close()

    def get_subscribed_users(self) -> List[Dict]:
        """Get all subscribed users with exchanges"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT u.id, u.telegram_id, u.username, u.first_name,
               s.auto_trade, s.max_position_size
        FROM users u
        JOIN subscriptions s ON u.id = s.user_id
        JOIN exchanges e ON u.id = e.user_id
        WHERE s.is_subscribed = 1 AND e.is_active = 1
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'telegram_id': row[1], 'username': row[2],
                'first_name': row[3], 'auto_trade': row[4], 'max_position_size': row[5]
            })
        return users

class ExchangeModel:
    def __init__(self, db: Database):
        self.db = db
    
    def add_exchange(self, user_id: int, exchange_name: str, 
                    api_key_encrypted: bytes, api_secret_encrypted: bytes,
                    passphrase_encrypted: bytes = b'', connection_type: str = 'manual',
                    leverage: int = 10) -> int:
        """Add exchange connection"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO exchanges 
            (user_id, exchange_name, api_key_encrypted, api_secret_encrypted, 
             passphrase_encrypted, connection_type, leverage) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, exchange_name, api_key_encrypted, api_secret_encrypted,
              passphrase_encrypted, connection_type, leverage))
        
        exchange_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return exchange_id
    
    def get_user_exchanges(self, user_id: int) -> List[Dict]:
        """Get all active exchanges for a user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, exchange_name, api_key_encrypted, api_secret_encrypted,
                   passphrase_encrypted, connection_type, is_active, auto_trade,
                   leverage, position_size_percent, balance, created_at, last_used
            FROM exchanges 
            WHERE user_id = ? AND is_active = 1
        ''', (user_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        exchanges = []
        for row in rows:
            exchanges.append({
                'id': row[0], 'exchange_name': row[1], 'api_key_encrypted': row[2],
                'api_secret_encrypted': row[3], 'passphrase_encrypted': row[4],
                'connection_type': row[5], 'is_active': row[6], 'auto_trade': row[7],
                'leverage': row[8], 'position_size_percent': row[9], 'balance': row[10],
                'created_at': row[11], 'last_used': row[12]
            })
        return exchanges
    
    def get_all_connected_users(self) -> List[Dict]:
        """Get all users with at least one connected exchange"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT u.id, u.telegram_id, u.username, u.first_name,
                   COUNT(e.id) as exchange_count
            FROM users u
            JOIN exchanges e ON u.id = e.user_id
            WHERE e.is_active = 1
            GROUP BY u.id, u.telegram_id, u.username, u.first_name
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        users = []
        for row in rows:
            users.append({
                'id': row[0], 'telegram_id': row[1], 'username': row[2],
                'first_name': row[3], 'exchange_count': row[4]
            })
        return users
    
    def get_exchange_distribution(self) -> Dict[str, int]:
        """Get distribution of exchanges"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT exchange_name, COUNT(*) as count
            FROM exchanges 
            WHERE is_active = 1
            GROUP BY exchange_name
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        distribution = {}
        for row in rows:
            distribution[row[0]] = row[1]
        return distribution
    
    def update_balance(self, exchange_id: int, balance: float):
        """Update exchange balance"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE exchanges 
            SET balance = ?, last_used = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (balance, exchange_id))
        
        conn.commit()
        conn.close()

class SignalModel:
    def __init__(self, db: Database):
        self.db = db
    
    def create_signal(self, symbol: str, signal_type: str, entry_price: float,
                     stop_loss: float = None, take_profit: float = None,
                     leverage: int = 10, position_size_percent: float = 5.0,
                     created_by: int = None, expires_hours: int = 24) -> int:
        """Create new trading signal"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(hours=expires_hours)
        
        cursor.execute('''
            INSERT INTO signals (symbol, signal_type, entry_price, stop_loss, 
                               take_profit, leverage, position_size_percent, 
                               created_by, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (symbol, signal_type, entry_price, stop_loss, take_profit,
              leverage, position_size_percent, created_by, expires_at))
        
        signal_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return signal_id
    
    def get_subscribers(self) -> List[Dict]:
        """Get all subscribed users"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT u.id, u.telegram_id, u.username, s.auto_trade,
                   s.max_position_size, s.use_stop_loss, s.use_take_profit
            FROM users u
            JOIN subscriptions s ON u.id = s.user_id
            JOIN exchanges e ON u.id = e.user_id
            WHERE s.is_subscribed = 1 AND e.is_active = 1
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        subscribers = []
        for row in rows:
            subscribers.append({
                'user_id': row[0], 'telegram_id': row[1], 'username': row[2],
                'auto_trade': row[3], 'max_position_size': row[4],
                'use_stop_loss': row[5], 'use_take_profit': row[6]
            })
        return subscribers
    
    def get_unprocessed_signals(self) -> List[Dict]:
        """Get unprocessed signals"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, signal_type, entry_price, stop_loss, take_profit,
                   leverage, position_size_percent, created_by, created_at
            FROM signals 
            WHERE is_processed = 0 AND status = 'active' 
            AND expires_at > CURRENT_TIMESTAMP
            ORDER BY created_at ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signals.append({
                'id': row[0], 'symbol': row[1], 'signal_type': row[2],
                'entry_price': row[3], 'stop_loss': row[4], 'take_profit': row[5],
                'leverage': row[6], 'position_size_percent': row[7],
                'created_by': row[8], 'created_at': row[9]
            })
        return signals
    
    def mark_signal_processed(self, signal_id: int):
        """Mark signal as processed"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals SET is_processed = 1 WHERE id = ?
        ''', (signal_id,))
        
        conn.commit()
        conn.close()
    
    def update_signal_results(self, signal_id: int, results: Dict):
        """Update signal with execution results"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals SET execution_results = ? WHERE id = ?
        ''', (json.dumps(results), signal_id))
        
        conn.commit()
        conn.close()

    def get_pending_signals(self) -> List[Dict]:
        """Get pending signals that need processing"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, symbol, signal_type, entry_price, stop_loss, take_profit,
               leverage, position_size_percent, created_by, created_at
        FROM signals 
        WHERE status = 'pending' AND expires_at > CURRENT_TIMESTAMP
        ORDER BY created_at ASC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        signals = []
        for row in rows:
            signals.append({
                'id': row[0], 'symbol': row[1], 'signal_type': row[2],
                'entry_price': row[3], 'stop_loss': row[4], 'take_profit': row[5],
                'leverage': row[6], 'position_size_percent': row[7],
                'created_by': row[8], 'created_at': row[9],
                'action': row[2]  # Add action field for compatibility
            })
        return signals

    def mark_signal_processed(self, signal_id: int):
        """Mark signal as processed"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE signals SET status = 'processed' WHERE id = ?
        ''', (signal_id,))
        
        conn.commit()
        conn.close()

class TradeModel:
    def __init__(self, db: Database):
        self.db = db
    
    def record_trade_execution(self, signal_id: int, user_id: int, exchange_name: str,
                             symbol: str, side: str, quantity: float, entry_price: float,
                             order_id: str = None) -> int:
        """Record a trade execution"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO trade_executions 
            (signal_id, user_id, exchange_name, symbol, side, quantity, 
             entry_price, order_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (signal_id, user_id, exchange_name, symbol, side, quantity,
              entry_price, order_id))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id
    
    def get_user_trades(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get recent trades for a user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.id, t.symbol, t.side, t.quantity, t.entry_price,
                   t.current_price, t.pnl, t.status, t.executed_at,
                   s.signal_type, t.exchange_name, t.order_id
            FROM trade_executions t
            JOIN signals s ON t.signal_id = s.id
            WHERE t.user_id = ?
            ORDER BY t.executed_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trades.append({
                'id': row[0], 'symbol': row[1], 'side': row[2], 'quantity': row[3],
                'entry_price': row[4], 'current_price': row[5], 'pnl': row[6],
                'status': row[7], 'executed_at': row[8], 'signal_type': row[9],
                'exchange_name': row[10], 'order_id': row[11]
            })
        return trades
    
    def get_active_trades(self) -> List[Dict]:
        """Get all active trades"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, signal_id, user_id, exchange_name, symbol, side,
                   quantity, entry_price, order_id, executed_at
            FROM trade_executions 
            WHERE status = 'open'
            ORDER BY executed_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trades.append({
                'id': row[0], 'signal_id': row[1], 'user_id': row[2],
                'exchange_name': row[3], 'symbol': row[4], 'side': row[5],
                'quantity': row[6], 'entry_price': row[7], 'order_id': row[8],
                'executed_at': row[9]
            })
        return trades
    
    def get_total_trades_count(self) -> int:
        """Get total number of trades"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trade_executions")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_successful_trades_count(self) -> int:
        """Get number of profitable trades"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM trade_executions WHERE pnl > 0")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_total_volume(self) -> float:
        """Get total trading volume"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(quantity * entry_price) FROM trade_executions")
        volume = cursor.fetchone()[0] or 0
        conn.close()
        return volume
    
    def get_total_pnl(self) -> float:
        """Get total P&L across all trades"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(pnl) FROM trade_executions")
        pnl = cursor.fetchone()[0] or 0
        conn.close()
        return pnl
    
    def get_daily_pnl(self, user_id: int, days: int = 7) -> List[Dict]:
        """Get daily P&L for user"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT date, pnl, trades_count
            FROM daily_pnl 
            WHERE user_id = ?
            ORDER BY date DESC
            LIMIT ?
        ''', (user_id, days))
        
        rows = cursor.fetchall()
        conn.close()
        
        daily_data = []
        for row in rows:
            daily_data.append({
                'date': row[0], 'pnl': row[1], 'trades_count': row[2]
            })
        return daily_data
    
    def get_monthly_pnl(self, user_id: int) -> Dict:
        """Get monthly P&L summary"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(pnl) as monthly_pnl, SUM(trades_count) as monthly_trades
            FROM daily_pnl 
            WHERE user_id = ? AND date >= date('now', '-30 days')
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'monthly_pnl': row[0] or 0,
                'monthly_trades': row[1] or 0
            }
        return {'monthly_pnl': 0, 'monthly_trades': 0}

    def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.id, t.signal_id, t.user_id, t.exchange_name, t.symbol, 
               t.side, t.quantity, t.entry_price, t.current_price, t.pnl,
               t.order_id, t.executed_at, s.stop_loss, s.take_profit
        FROM trade_executions t
        JOIN signals s ON t.signal_id = s.id
        WHERE t.status = 'open'
        ORDER BY t.executed_at DESC
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        trades = []
        for row in rows:
            trades.append({
                'id': row[0], 'signal_id': row[1], 'user_id': row[2],
                'exchange_name': row[3], 'symbol': row[4], 'side': row[5],
                'quantity': row[6], 'entry_price': row[7], 'current_price': row[8],
                'pnl': row[9], 'order_id': row[10], 'executed_at': row[11],
                'stop_loss': row[12], 'take_profit': row[13]
            })
        return trades

    def update_trade_pnl(self, trade_id: int, pnl: float, current_price: float):
        """Update trade P&L and current price"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trade_executions 
            SET pnl = ?, current_price = ?
            WHERE id = ?
        ''', (pnl, current_price, trade_id))
        
        conn.commit()
        conn.close()

    def close_trade(self, trade_id: int, close_price: float, final_pnl: float, reason: str):
        """Close a trade"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE trade_executions 
            SET status = 'closed', current_price = ?, pnl = ?, closed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (close_price, final_pnl, trade_id))
        
        conn.commit()
        conn.close()

    def create_trade(self, user_id: int, exchange_id: int, signal_id: int, symbol: str,
                action: str, entry_price: float, quantity: float, stop_loss: float = None,
                take_profit: float = None, leverage: int = 10) -> int:
        """Create a new trade record"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        side = 'BUY' if action.upper() in ['LONG', 'BUY'] else 'SELL'
        
        cursor.execute('''
            INSERT INTO trade_executions 
            (signal_id, user_id, exchange_name, symbol, side, quantity, entry_price)
        SELECT ?, ?, e.exchange_name, ?, ?, ?, ?
        FROM exchanges e WHERE e.id = ?
        ''', (signal_id, user_id, symbol, side, quantity, entry_price, exchange_id))
        
        trade_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return trade_id

class PortfolioModel:
    def __init__(self, db: Database):
        self.db = db
    
    def get_user_portfolio(self, user_id: int) -> Optional[Dict]:
        """Get user portfolio overview"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT total_balance, total_pnl, pnl_percentage, total_trades,
                   winning_trades, losing_trades, win_rate, best_trade,
                   worst_trade, average_trade, first_trade_date, last_updated
            FROM portfolios WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'total_balance': row[0], 'total_pnl': row[1], 'pnl_percentage': row[2],
                'total_trades': row[3], 'winning_trades': row[4], 'losing_trades': row[5],
                'win_rate': row[6], 'best_trade': row[7], 'worst_trade': row[8],
                'average_trade': row[9], 'first_trade_date': row[10], 'last_updated': row[11]
            }
        return None
    
    def update_user_portfolio(self, user_id: int, total_pnl: float, 
                            total_trades: int, winning_trades: int, losing_trades: int):
        """Update user portfolio statistics"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Calculate derived metrics
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        average_trade = total_pnl / total_trades if total_trades > 0 else 0
        
        cursor.execute('''
            UPDATE portfolios 
            SET total_pnl = ?, total_trades = ?, winning_trades = ?, 
                losing_trades = ?, win_rate = ?, average_trade = ?,
                last_updated = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (total_pnl, total_trades, winning_trades, losing_trades, 
              win_rate, average_trade, user_id))
        
        conn.commit()
        conn.close()
