import sqlite3

connection = sqlite3.connect("food_waste.db")

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS food (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    category TEXT,
    quantity REAL,
    unit TEXT,
    purchase_date TEXT,
    expiry_date TEXT,
    storage TEXT
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS waste (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    food_name TEXT,
    quantity REAL,
    unit TEXT,
    reason TEXT,
    waste_date TEXT
)
""")

connection.commit()

connection.close()

print("Database created successfully!")
import sqlite3

connection = sqlite3.connect("food_waste.db")
cursor = connection.cursor()

try:
    cursor.execute(
        "ALTER TABLE food ADD COLUMN waste_recorded INTEGER DEFAULT 0"
    )
    connection.commit()
    print("Waste tracking column added successfully.")
except sqlite3.OperationalError:
    print("Waste tracking column already exists.")

connection.close()
# ============================================================
# MULTI-USER DATABASE SETUP
# ============================================================

import sqlite3

connection = sqlite3.connect("food_waste.db")
cursor = connection.cursor()

# Create users table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )
""")

connection.commit()
connection.close()

print("Multi-user database setup completed successfully.")
# ============================================================
# ADD USER OWNERSHIP TO FOOD AND WASTE
# ============================================================

import sqlite3

connection = sqlite3.connect("food_waste.db")
cursor = connection.cursor()

# Add user_id to food table
try:
    cursor.execute(
        "ALTER TABLE food ADD COLUMN user_id INTEGER"
    )
    print("user_id added to food table.")
except sqlite3.OperationalError:
    print("user_id already exists in food table.")

# Add user_id to waste table
try:
    cursor.execute(
        "ALTER TABLE waste ADD COLUMN user_id INTEGER"
    )
    print("user_id added to waste table.")
except sqlite3.OperationalError:
    print("user_id already exists in waste table.")

connection.commit()
connection.close()

print("Food and waste ownership setup completed.")
# ============================================================
# REMOVE PASSWORD REQUIREMENT
# ============================================================

import sqlite3

connection = sqlite3.connect("food_waste.db")
cursor = connection.cursor()

# Check whether the users table already has a password column.
# We keep the column for compatibility, but make it unused.
cursor.execute("PRAGMA table_info(users)")
columns = cursor.fetchall()

print("Users table structure checked.")

connection.commit()
connection.close()
# ============================================================
# CONVERT USERS TABLE TO USERNAME-ONLY
# ============================================================

import sqlite3

connection = sqlite3.connect("food_waste.db")
cursor = connection.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS users_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL
    )
""")

cursor.execute("""
    INSERT OR IGNORE INTO users_new (id, username)
    SELECT id, username
    FROM users
""")

cursor.execute("DROP TABLE users")

cursor.execute("""
    ALTER TABLE users_new
    RENAME TO users
""")

connection.commit()
connection.close()

print("Username-only users table created successfully.")
