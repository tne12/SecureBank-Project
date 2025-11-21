import sqlite3

conn = sqlite3.connect("database/banking_system.db")
conn.row_factory = sqlite3.Row

row = conn.execute(
    "SELECT id, email, password_hash FROM users WHERE email = 'admin@bank.com'"
).fetchone()

print(dict(row) if row else "Admin user not found.")
