import sqlite3
from flask_bcrypt import Bcrypt
from flask import Flask

app = Flask(__name__)
bcrypt = Bcrypt(app)

conn = sqlite3.connect("database/banking_system.db")
conn.row_factory = sqlite3.Row

new_password = "Admin@123"
hashed = bcrypt.generate_password_hash(new_password).decode("utf-8")

conn.execute(
    "UPDATE users SET password_hash = ? WHERE email = 'admin@bank.com'",
    (hashed,)
)
conn.commit()

print("Admin password reset to Admin@123")
