import sqlite3
import bcrypt
import random
import json
import os
from datetime import datetime, timedelta

# --- Database Setup ---
DB_DIR = "db"
DB_NAME = "financial_advisor.db"
DB_PATH = os.path.join(DB_DIR, DB_NAME)

# Create db directory if it doesn't exist
os.makedirs(DB_DIR, exist_ok=True)

# Connect to the database (it will be created if it doesn't exist)
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

def create_tables():
    """Create all necessary tables if they don't exist."""
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        date_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )""")

    # User profiles table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_profiles (
        user_id INTEGER PRIMARY KEY,
        date_of_birth DATE,
        monthly_income REAL,
        monthly_expenses REAL,
        risk_appetite TEXT CHECK(risk_appetite IN ('Low', 'Medium', 'High')),
        investment_horizon_years INTEGER,
        financial_goals TEXT,  -- JSON string
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # Portfolios table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        target_allocation TEXT,  -- JSON string
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )""")

    # Recommendations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recommendations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        recommendation_json TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )""")

    # Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        portfolio_id INTEGER,
        asset_type TEXT NOT NULL,
        asset_id TEXT NOT NULL,
        transaction_type TEXT CHECK(transaction_type IN ('BUY', 'SELL', 'DIVIDEND', 'INTEREST')),
        units REAL NOT NULL,
        price_per_unit REAL NOT NULL,
        transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (portfolio_id) REFERENCES portfolios(id) ON DELETE SET NULL
    )""")

def insert_sample_data():
    """Insert sample data into the database."""
    # Sample users
    users = [
        ("Alice Johnson", "alice@example.com", "password123"),
        ("Bob Williams", "bob@example.com", "password456"),
        ("Charlie Brown", "charlie@example.com", "password789")
    ]
    
    risk_levels = ['Low', 'Medium', 'High']
    goals = [
        "Retirement planning",
        "Children's education",
        "Buying a house",
        "Wealth creation",
        "Tax saving"
    ]
    
    for name, email, password in users:
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone() is None:
            # Hash password
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            
            # Insert user
            cursor.execute(
                "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, hashed.decode('utf-8'))
            )
            user_id = cursor.lastrowid
            
            # Create user profile
            profile = {
                'date_of_birth': (datetime.now() - timedelta(days=random.randint(25, 60)*365)).strftime('%Y-%m-%d'),
                'monthly_income': random.randint(50000, 300000),
                'monthly_expenses': random.randint(20000, 100000),
                'risk_appetite': random.choice(risk_levels),
                'investment_horizon_years': random.randint(5, 30),
                'financial_goals': json.dumps(random.sample(goals, k=random.randint(1, 3)))
            }
            
            cursor.execute("""
                INSERT INTO user_profiles 
                (user_id, date_of_birth, monthly_income, monthly_expenses, 
                 risk_appetite, investment_horizon_years, financial_goals)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                profile['date_of_birth'],
                profile['monthly_income'],
                profile['monthly_expenses'],
                profile['risk_appetite'],
                profile['investment_horizon_years'],
                profile['financial_goals']
            ))
            
            print(f"Created user: {name} ({email})")
        else:
            print(f"User {email} already exists, skipping...")

def main():
    try:
        print("Setting up database...")
        create_tables()
        insert_sample_data()
        conn.commit()
        print("\n✅ Database setup completed successfully!")
        print(f"Database file: {os.path.abspath(DB_PATH)}")
    except Exception as e:
        print(f"\n❌ Error setting up database: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()