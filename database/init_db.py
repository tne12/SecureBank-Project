import os
import sqlite3


# SQLite database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "banking_system.db")


def create_database():
    """
    For SQLite, the database is just a file.
    If it does not exist, sqlite3.connect will create it.
    """
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        conn.close()
        print(f"SQLite database created at: {DB_PATH}")
    else:
        print(f"SQLite database already exists at: {DB_PATH}")


def get_db_connection():
    """Get a connection to the SQLite banking database"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_tables():
    """Initialize all database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name VARCHAR(255) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(20) NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL CHECK (role IN ('customer', 'support_agent', 'auditor', 'admin')),
                is_first_login BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Accounts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number VARCHAR(20) UNIQUE NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('checking', 'savings')),
                balance DECIMAL(15, 2) DEFAULT 0.00,
                status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'frozen', 'closed')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Transactions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                transaction_id VARCHAR(50) UNIQUE NOT NULL,
                idempotency_key VARCHAR(100) UNIQUE,
                sender_account_id INTEGER REFERENCES accounts(id),
                receiver_account_id INTEGER REFERENCES accounts(id),
                amount DECIMAL(15, 2) NOT NULL,
                transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('internal_transfer', 'external_transfer', 'deposit', 'withdrawal')),
                description TEXT,
                status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('completed', 'failed', 'pending')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Support tickets table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_number VARCHAR(20) UNIQUE NOT NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                subject VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                status VARCHAR(20) DEFAULT 'open' CHECK (status IN ('open', 'in_progress', 'resolved')),
                assigned_to INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Ticket notes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ticket_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER REFERENCES support_tickets(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id),
                note TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Audit logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER REFERENCES users(id),
                action VARCHAR(100) NOT NULL,
                resource_type VARCHAR(50),
                resource_id INTEGER,
                ip_address VARCHAR(45),
                user_agent TEXT,
                details TEXT,
                severity VARCHAR(20) DEFAULT 'info' CHECK (severity IN ('info', 'warning', 'critical')),
                log_hash VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user_id ON accounts(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_number ON accounts(account_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_sender ON transactions(sender_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_receiver ON transactions(receiver_account_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_transactions_idempotency ON transactions(idempotency_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_user ON audit_logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_action ON audit_logs(action)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_date ON audit_logs(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_severity ON audit_logs(severity)")

        conn.commit()
        print("All tables created successfully")

    except Exception as e:
        conn.rollback()
        print(f"Error creating tables: {e}")
        raise
    finally:
        cursor.close()
        conn.close()


def seed_default_admin():
    """Create default admin user (SQLite + bcrypt, SQLite-style placeholders)."""
    from flask_bcrypt import Bcrypt
    bcrypt = Bcrypt()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if an admin already exists
        cursor.execute("SELECT id FROM users WHERE role = ?", ('admin',))
        admin_exists = cursor.fetchone()

        if not admin_exists:
            password_hash = bcrypt.generate_password_hash('Admin@123').decode('utf-8')

            cursor.execute(
                """
                INSERT INTO users (full_name, email, phone, password_hash, role, is_first_login)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    'System Administrator',
                    'admin@bank.com',
                    '+1234567890',
                    password_hash,
                    'admin',
                    1  # TRUE in SQLite as integer
                )
            )

            conn.commit()
            print("=" * 60)
            print("Default admin created successfully")
            print("Email: admin@bank.com")
            print("Password: Admin@123")
            print("IMPORTANT: You MUST change password on first login")
            print("=" * 60)
        else:
            print("Admin user already exists")

    except Exception as e:
        conn.rollback()
        print(f"Error creating admin: {e}")
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    create_database()
    init_tables()
    seed_default_admin()
