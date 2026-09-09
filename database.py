import sqlite3
from datetime import datetime, timedelta
from config import ADMIN_ID

DB_NAME = 'subscriptions.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            subscription_end DATE,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            payment_id TEXT UNIQUE,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, is_admin) 
        VALUES (?, 1)
    ''', (ADMIN_ID,))
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
    ''', (user_id, username))
    conn.commit()
    conn.close()

def has_subscription(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT subscription_end FROM users 
        WHERE user_id = ? AND subscription_end > DATE('now')
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    try:
        from storage import clear_cache
        clear_cache(user_id)
    except:
        pass
    
    return result is not None

def activate_subscription(user_id, days=30):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users 
        SET subscription_end = DATE('now', '+' || ? || ' days')
        WHERE user_id = ?
    ''', (days, user_id))
    conn.commit()
    conn.close()
    
    try:
        from storage import clear_cache
        clear_cache(user_id)
    except:
        pass
    
    print(f"✅ Подписка активирована для {user_id} на {days} дней")
    return True

def is_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT is_admin FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == 1

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, username, subscription_end FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def get_active_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id FROM users 
        WHERE subscription_end > DATE('now')
    ''')
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

def get_expiring_soon(days=3):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT user_id, username, subscription_end FROM users 
        WHERE subscription_end BETWEEN DATE('now') AND DATE('now', '+' || ? || ' days')
    ''', (days,))
    users = cursor.fetchall()
    conn.close()
    return users

init_db()