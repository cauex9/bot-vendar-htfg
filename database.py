import sqlite3
import json
from config import DB_PATH

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            points REAL DEFAULT 0.0,
            referred_by INTEGER,
            notifications_enabled INTEGER DEFAULT 1, -- 1 for ON, 0 for OFF
            FOREIGN KEY (referred_by) REFERENCES users (user_id)
        )
    ''')

    # Create Categories table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # Create Products table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category_id INTEGER,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            stock TEXT, -- JSON array of items or count
            FOREIGN KEY (category_id) REFERENCES categories (id)
        )
    ''')

    # Create Sales table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            amount REAL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Add missing columns to users table if they don't exist
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN points REAL DEFAULT 0.0")
    except sqlite3.OperationalError: pass # Already exists
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN referred_by INTEGER")
    except sqlite3.OperationalError: pass
    
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN notifications_enabled INTEGER DEFAULT 1")
    except sqlite3.OperationalError: pass

    conn.commit()
    conn.close()

def add_user(user_id: int, username: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO users (user_id, username)
        VALUES (?, ?)
    ''', (user_id, username))
    conn.commit()
    conn.close()

def get_user(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_categories():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name FROM categories')
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_products_by_category(category_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price FROM products WHERE category_id = ?', (category_id,))
    products = cursor.fetchall()
    conn.close()
    return products

def get_product(product_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    conn.close()
    return product

def get_sales_history(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.name, s.amount, s.date 
        FROM sales s 
        JOIN products p ON s.product_id = p.id 
        WHERE s.user_id = ? 
        ORDER BY s.date DESC
    ''', (user_id,))
    history = cursor.fetchall()
    conn.close()
    return history

def set_referral(user_id: int, referrer_id: int):
    if user_id == referrer_id: return
    conn = get_connection()
    cursor = conn.cursor()
    # Only set if not already referred
    cursor.execute('UPDATE users SET referred_by = ? WHERE user_id = ? AND referred_by IS NULL', (referrer_id, user_id))
    conn.commit()
    conn.close()

def add_balance(user_id: int, amount: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
    
    # Check for affiliate bonus
    cursor.execute('SELECT referred_by FROM users WHERE user_id = ?', (user_id,))
    res = cursor.fetchone()
    if res and res[0]:
        referrer_id = res[0]
        bonus = amount * 0.10
        cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (bonus, referrer_id))
        
    conn.commit()
    conn.close()

def toggle_notifications(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET notifications_enabled = 1 - notifications_enabled WHERE user_id = ?', (user_id,))
    cursor.execute('SELECT notifications_enabled FROM users WHERE user_id = ?', (user_id,))
    status = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return status

def deliver_product(user_id: int, product_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get product stock
    cursor.execute('SELECT name, price, stock FROM products WHERE id = ?', (product_id,))
    product = cursor.fetchone()
    if not product: 
        conn.close()
        return None
    
    name, price, stock_data = product
    
    try:
        # Check if stock_data is a JSON list
        stock = json.loads(stock_data)
        if isinstance(stock, list) and len(stock) > 0:
            item = stock.pop(0)
            new_stock_data = json.dumps(stock)
            
            # Update stock
            cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (new_stock_data, product_id))
            
            # Add to sales
            cursor.execute('INSERT INTO sales (user_id, product_id, amount) VALUES (?, ?, ?)', (user_id, product_id, price))
            
            # Update user total_spent
            cursor.execute('UPDATE users SET total_spent = total_spent + ?, points = points + ? WHERE user_id = ?', 
                           (price, price * 0.1, user_id)) # 10% points
            
            conn.commit()
            conn.close()
            return item
    except Exception as e:
        import logging
        logging.error(f"Delivery error: {e}")
    
    conn.close()
    return None

def add_stock(product_id: int, new_items: list):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT stock FROM products WHERE id = ?', (product_id,))
    res = cursor.fetchone()
    if res:
        try:
            current_stock = json.loads(res[0])
            if not isinstance(current_stock, list): current_stock = []
        except:
            current_stock = []
        
        current_stock.extend(new_items)
        cursor.execute('UPDATE products SET stock = ? WHERE id = ?', (json.dumps(current_stock), product_id))
        conn.commit()
    conn.close()
