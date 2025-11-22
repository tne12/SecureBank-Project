"""
RBAC & Authentication Service
Handles: User auth, JWT, password management, RBAC permission checking, rate limiting
"""
from flask import Flask, request, jsonify
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import jwt
import os
import re
import redis
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
import requests   


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
bcrypt = Bcrypt(app)
CORS(app)

# Warn if using default SECRET_KEY (but don't exit so you can develop)
if app.config['SECRET_KEY'] == 'your-secret-key-change-in-production':
    print("=" * 60)
    print("WARNING: Using default SECRET_KEY.")
    print("Generate a secure key with: python -c \"import secrets; print(secrets.token_hex(32))\"")
    print("Set it in your environment as: SECRET_KEY=your-generated-key")
    print("=" * 60)

# Redis for rate limiting
try:
    redis_client = redis.Redis(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', 6379)),
        db=0,
        decode_responses=True
    )
    redis_client.ping()
    print("✓ Redis connected for rate limiting")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
    print("  Rate limiting will be disabled")
    redis_client = None

MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_MINUTES = 15

AUDIT_LOG_URL = os.getenv(
    'AUDIT_LOG_URL',
    'http://localhost:5003/api/audit/log'
)

# RBAC Permission Matrix
PERMISSION_MATRIX = {
    'customer': {
        'register_login': True,
        'manage_own_profile': True,
        'view_own_accounts': True,
        'view_all_accounts': False,
        'create_accounts': True,
        'internal_transfers': True,
        'external_transfers': True,
        'view_own_transactions': True,
        'view_all_transactions': False,
        'freeze_unfreeze_accounts': False,
        'manage_users_roles': False,
        'manage_tickets': False,
        'view_audit_logs': False,
    },
    'support_agent': {
        'register_login': True,
        'manage_own_profile': True,
        'view_own_accounts': True,
        'view_all_accounts': True,
        'create_accounts': False,
        'internal_transfers': False,
        'external_transfers': False,
        'view_own_transactions': True,
        'view_all_transactions': True,
        'freeze_unfreeze_accounts': False,
        'manage_users_roles': False,
        'manage_tickets': True,
        'view_audit_logs': False,
    },
    'auditor': {
        'register_login': True,
        'manage_own_profile': False,
        'view_own_accounts': True,
        'view_all_accounts': True,
        'create_accounts': False,
        'internal_transfers': False,
        'external_transfers': False,
        'view_own_transactions': True,
        'view_all_transactions': True,
        'freeze_unfreeze_accounts': False,
        'manage_users_roles': False,
        'manage_tickets': False,
        'view_audit_logs': True,
    },
    'admin': {
        'register_login': True,
        'manage_own_profile': True,
        'view_own_accounts': True,
        'view_all_accounts': True,
        'create_accounts': True,
        'internal_transfers': True,
        'external_transfers': True,
        'view_own_transactions': True,
        'view_all_transactions': True,
        'freeze_unfreeze_accounts': True,
        'manage_users_roles': True,
        'manage_tickets': True,
        'view_audit_logs': True,
    }
}

def create_audit_log(
    user_id=None,
    action=None,
    resource_type=None,
    resource_id=None,
    details=None,
    severity="info",
):
    """
    Send audit log entry to Web App service.
    Non-blocking: failures are ignored so auth never breaks because of logging.
    """
    if not action:
        return

    payload = {
        "user_id": user_id,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "details": details,
        "severity": severity,
    }

    try:
        requests.post(AUDIT_LOG_URL, json=payload, timeout=3)
    except Exception:
        pass

# Utility functions
def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def sanitize_input(text):
    """Sanitize user input to prevent XSS"""
    if not text:
        return text
    dangerous_chars = ['<', '>', '"', "'", '&']
    for char in dangerous_chars:
        text = text.replace(char, '')
    return text.strip()


def check_rate_limit(email, ip_address):
    """Hard rate limiting: 5 attempts per 15 minutes per (IP+email)"""
    if not redis_client:
        return True, 0

    try:
        key = f"login_attempts:{ip_address}:{email}"
        attempts = redis_client.get(key)

        if attempts is None:
            redis_client.setex(key, LOGIN_LOCKOUT_MINUTES * 60, 1)
            return True, 1

        attempts = int(attempts)
        if attempts >= MAX_LOGIN_ATTEMPTS:
            ttl = redis_client.ttl(key)
            return False, ttl

        redis_client.incr(key)
        return True, attempts + 1
    except:
        return True, 0


def reset_rate_limit(email, ip_address):
    """Reset rate limit after successful login"""
    if redis_client:
        try:
            key = f"login_attempts:{ip_address}:{email}"
            redis_client.delete(key)
        except:
            pass


# Database connection (SQLite)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "banking_system.db")


def get_db_connection():
    """Get database connection to SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


# API Routes

@app.route('/')
def root():
    return jsonify({'service': 'rbac-auth-service', 'status': 'running'}), 200


@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user (customer only)"""
    try:
        data = request.get_json()

        required_fields = ['full_name', 'email', 'phone', 'password']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'{field} is required'}), 400

        full_name = sanitize_input(data['full_name'])
        email = sanitize_input(data['email'].lower())
        phone = sanitize_input(data['phone'])
        password = data['password']

        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400

        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if user already exists
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'User with this email already exists'}), 409

        # Insert new customer (SQLite syntax: ? placeholders, no RETURNING)
        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, role, is_first_login)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (full_name, email, phone, password_hash, 'customer', 0))

        user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        create_audit_log(
            user_id=user_id,
            action="user_registered",
            resource_type="user",
            resource_id=user_id,
            details=f"New customer registered with email {email}",
            severity="info",
        )

        return jsonify({
            'message': 'User registered successfully',
            'user_id': user_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login user with rate limiting."""
    try:
        data = request.get_json()

        if 'email' not in data or 'password' not in data:
            return jsonify({'error': 'Email and password are required'}), 400

        email = sanitize_input(data['email'].lower())
        password = data['password']
        ip_address = request.remote_addr

        # Check rate limiting
        allowed, attempts_or_ttl = check_rate_limit(email, ip_address)
        if not allowed:
            minutes_left = max(attempts_or_ttl // 60, 0)

            create_audit_log(
                user_id=None,
                action="login_rate_limited",
                resource_type="auth",
                resource_id=None,
                details=f"Rate limit triggered for email={email} from IP={ip_address}. "
                        f"Lockout ~{minutes_left} minutes remaining.",
                severity="warning",
            )

            return jsonify({
                'error': f'Too many login attempts. Account locked for {minutes_left} more minutes.'
            }), 429

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, full_name, email, password_hash, role, is_first_login
            FROM users WHERE email = ?
        """, (email,))

        user = cursor.fetchone()

        if not user or not bcrypt.check_password_hash(user['password_hash'], password):
            # --- Audit: login failed ---
            create_audit_log(
                user_id=user['id'] if user else None,
                action="login_failed",
                resource_type="auth",
                resource_id=None,
                details=f"Failed login for email={email} from IP={ip_address}",
                severity="warning",
            )

            cursor.close()
            conn.close()
            return jsonify({'error': 'Invalid credentials'}), 401


        reset_rate_limit(email, ip_address)
        
        cursor.close()
        conn.close()

        # --- Audit: login success ---
        create_audit_log(
            user_id=user['id'],
            action="login_success",
            resource_type="auth",
            resource_id=None,
            details=f"User {user['email']} logged in successfully from IP={ip_address}",
            severity="info",
        )

        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'role': user['role'],
            'exp': datetime.utcnow() + timedelta(hours=8)
        }, app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            'token': token,
            'user': {
                'id': user['id'],
                'full_name': user['full_name'],
                'email': user['email'],
                'role': user['role'],
                'is_first_login': user['is_first_login']
            }
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/validate', methods=['POST'])
def validate_token():
    """Validate JWT token"""
    try:
        token = request.headers.get('Authorization')

        if not token:
            return jsonify({'valid': False, 'error': 'Token is missing'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])

        return jsonify({
            'valid': True,
            'user': data
        }), 200

    except jwt.ExpiredSignatureError:
        return jsonify({'valid': False, 'error': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'valid': False, 'error': 'Invalid token'}), 401

@app.route('/api/auth/change-password', methods=['POST'])
def change_password():
    """Change password for the currently logged-in user (first login flow)."""
    try:
        # 1) Get and decode JWT from Authorization header
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Missing token'}), 401

        if token.startswith('Bearer '):
            token = token[7:]

        try:
            payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        # IMPORTANT: the login route sets "user_id", not "id"
        user_id = payload.get('user_id')
        if not user_id:
            return jsonify({'error': 'Invalid token payload'}), 400

        # 2) Read current & new password from body
        data = request.get_json() or {}
        current_password = data.get('current_password')
        new_password = data.get('new_password')

        if not current_password or not new_password:
            return jsonify({'error': 'Current and new password are required'}), 400

        # 3) Check password policy for the new password
        is_valid, message = validate_password(new_password)
        if not is_valid:
            # --- Audit: password change failed due to weak new password ---
            create_audit_log(
                user_id=user_id,
                action="password_change_failed",
                resource_type="user",
                resource_id=user_id,
                details=f"Password change failed: new password did not meet security policy ({message})",
                severity="warning",
            )
            return jsonify({'error': message}), 400

        # 4) Load user and verify current password
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()

        if not row:
            cursor.close()
            conn.close()
            return jsonify({'error': 'User not found'}), 404

        if not bcrypt.check_password_hash(row['password_hash'], current_password):
            cursor.close()
            conn.close()
            # --- Audit: failed password change attempt ---
            create_audit_log(
                user_id=user_id,
                action="password_change_failed",
                resource_type="user",
                resource_id=user_id,
                details="Password change failed: incorrect CURRENT password entered",
                severity="warning",  
            )
            return jsonify({'error': 'Current password is incorrect'}), 400

        # 5) Hash new password and update DB, also clear first-login flag
        new_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
        cursor.execute(
            "UPDATE users SET password_hash = ?, is_first_login = 0 WHERE id = ?",
            (new_hash, user_id),
        )
        conn.commit()
        cursor.close()
        conn.close()

        # --- Audit: password changed ---
        create_audit_log(
            user_id=user_id,
            action="password_changed",
            resource_type="user",
            resource_id=user_id,
            details="User changed password via /api/auth/change-password",
            severity="info",
        )

        return jsonify({'message': 'Password changed successfully'}), 200

    except Exception as e:
        # Helpful while you’re developing
        return jsonify({'error': str(e)}), 500



@app.route('/api/rbac/check', methods=['POST'])
def check_permission():
    """Check RBAC permission"""
    try:
        data = request.get_json()

        if 'role' not in data or 'action' not in data:
            return jsonify({'error': 'Role and action are required'}), 400

        role = data['role']
        action = data['action']

        if role not in PERMISSION_MATRIX:
            return jsonify({'allowed': False, 'reason': 'Invalid role'}), 200

        if action not in PERMISSION_MATRIX[role]:
            return jsonify({'allowed': False, 'reason': 'Invalid action'}), 200

        allowed = PERMISSION_MATRIX[role][action]
        return jsonify({'allowed': allowed, 'role': role, 'action': action}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rbac/permissions/<role>', methods=['GET'])
def get_role_permissions(role):
    """Get all permissions for a role"""
    if role not in PERMISSION_MATRIX:
        return jsonify({'error': 'Invalid role'}), 404

    return jsonify({
        'role': role,
        'permissions': PERMISSION_MATRIX[role]
    }), 200


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'rbac-auth-service'}), 200


if __name__ == '__main__':
    print("=" * 60)
    print("Starting RBAC & Authentication Service on port 5001")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5001, debug=False)
