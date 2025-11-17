"""
Web App Service
Handles: Admin panel, support tickets, audit logs, frontend serving
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_bcrypt import Bcrypt
from flask_cors import CORS
import os
import random
import string
import requests
import hashlib
import sqlite3

app = Flask(__name__, static_folder='static', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
bcrypt = Bcrypt(app)
CORS(app)

# SQLite database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database", "banking_system.db")

def get_db_connection():
    """Get database connection to SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Service URLs
RBAC_AUTH_URL = os.getenv('RBAC_AUTH_URL', 'http://localhost:5001')
TRANSACTION_URL = os.getenv('TRANSACTION_URL', 'http://localhost:5002')


def verify_token(token):
    """Verify token via RBAC service"""
    try:
        response = requests.post(
            f"{RBAC_AUTH_URL}/api/auth/validate",
            headers={'Authorization': f'Bearer {token}'},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('valid'):
                return data.get('user')
    except Exception:
        pass
    return None


def check_rbac_permission(role, action):
    """Check permission via RBAC service"""
    try:
        response = requests.post(
            f"{RBAC_AUTH_URL}/api/rbac/check",
            json={'role': role, 'action': action},
            timeout=5
        )
        if response.status_code == 200:
            result = response.json()
            return result.get('allowed', False)
    except Exception:
        pass
    return False


def hash_log_entry(entry_string):
    """Generate SHA-256 hash for log entry"""
    return hashlib.sha256(entry_string.encode('utf-8')).hexdigest()

@app.route('/')
def home():
    return send_from_directory('static', 'index.html')


@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)


@app.route('/api/audit/log', methods=['POST'])
def create_audit_log():
    """Create audit log entry"""
    try:
        data = request.get_json()

        user_id = data.get('user_id')
        action = data.get('action')
        resource_type = data.get('resource_type')
        resource_id = data.get('resource_id')
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', 'unknown')
        details = data.get('details')
        severity = data.get('severity', 'info')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audit_logs (
                user_id, action, resource_type, resource_id,
                ip_address, user_agent, details, severity, log_hash
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, action, resource_type, resource_id,
              ip_address, user_agent, details, severity, ""))

        log_id = cursor.lastrowid

        entry_string = f"{log_id}:{user_id}:{action}:{resource_type}:{resource_id}:{ip_address}:{user_agent}:{details}:{severity}"
        log_hash = hash_log_entry(entry_string)

        cursor.execute(
            "UPDATE audit_logs SET log_hash = ? WHERE id = ?",
            (log_hash, log_id)
        )

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Audit log created', 'log_id': log_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/audit/logs', methods=['GET'])
def get_audit_logs():
    """Get audit logs (auditor & admin) with filters"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    if not check_rbac_permission(current_user['role'], 'view_audit_logs'):
        return jsonify({'error': 'Access denied'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                al.id,
                al.user_id,
                u.full_name AS user_name,
                al.action,
                al.resource_type,
                al.resource_id,
                al.ip_address,
                al.user_agent,
                al.details,
                al.severity,
                al.log_hash,
                al.created_at
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            WHERE 1=1
        """
        params = []

        user_id = request.args.get('user_id')
        action = request.args.get('action')
        severity = request.args.get('severity')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        if user_id:
            query += " AND al.user_id = ?"
            params.append(int(user_id))

        if action:
            query += " AND al.action = ?"
            params.append(action)

        if severity:
            query += " AND al.severity = ?"
            params.append(severity)

        if start_date:
            query += " AND al.created_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND al.created_at <= ?"
            params.append(end_date)

        query += " ORDER BY al.created_at DESC LIMIT ?"
        params.append(int(request.args.get('limit', 200)))

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        logs = [dict(row) for row in rows]

        return jsonify({'logs': logs}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get current user profile"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT is_first_login FROM users WHERE id = ?",
            (current_user['user_id'],)
        )
        row = cursor.fetchone()
        is_first_login = row['is_first_login'] if row else False

        cursor.close()
        conn.close()

        return jsonify({
            'user': current_user,
            'is_first_login': is_first_login
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/profile', methods=['PATCH'])
def update_profile():
    """Update current user profile (email / password / full name)"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        new_email = data.get('email')
        new_password = data.get('password')
        full_name = data.get('full_name')

        update_fields = ['password_hash = ?', 'email = ?', 'is_first_login = FALSE', 'updated_at = CURRENT_TIMESTAMP']
        params = []

        if new_password:
            password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
            params.append(password_hash)
        else:
            return jsonify({'error': 'Password is required'}), 400

        if new_email:
            params.append(new_email)
        else:
            return jsonify({'error': 'Email is required'}), 400

        if full_name:
            update_fields.append('full_name = ?')
            params.append(full_name)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM users WHERE email = ? AND id != ?",
            (new_email, current_user['user_id'])
        )
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'Email already in use'}), 409

        params.append(current_user['user_id'])

        query = f"""
            UPDATE users
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        cursor.execute(query, tuple(params))
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Profile updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users', methods=['GET'])
def admin_get_users():
    """Admin: list users"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    if not check_rbac_permission(current_user['role'], 'manage_users_roles'):
        return jsonify({'error': 'Access denied'}), 403

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, full_name, email, phone, role, created_at FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        users = [dict(row) for row in rows]

        return jsonify({'users': users}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users', methods=['POST'])
def admin_create_user():
    """Admin: create user with any role"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    if not check_rbac_permission(current_user['role'], 'manage_users_roles'):
        return jsonify({'error': 'Access denied'}), 403

    try:
        data = request.get_json()
        full_name = data.get('full_name')
        email = data.get('email')
        phone = data.get('phone')
        role = data.get('role', 'customer')
        password = data.get('password', 'Temp@123')

        if role not in ['customer', 'support_agent', 'auditor', 'admin']:
            return jsonify({'error': 'Invalid role'}), 400

        password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({'error': 'User with this email already exists'}), 409

        cursor.execute("""
            INSERT INTO users (full_name, email, phone, password_hash, role, is_first_login)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (full_name, email, phone, password_hash, role, 1))

        user_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'message': 'User created successfully',
            'user_id': user_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/users/<int:user_id>/role', methods=['PATCH'])
def admin_update_user_role(user_id):
    """Admin: change user role"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    if not check_rbac_permission(current_user['role'], 'manage_users_roles'):
        return jsonify({'error': 'Access denied'}), 403

    try:
        data = request.get_json()
        new_role = data.get('role')

        if new_role not in ['customer', 'support_agent', 'auditor', 'admin']:
            return jsonify({'error': 'Invalid role'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_role, user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'User role updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/support/tickets', methods=['POST'])
def create_ticket():
    """Customer: open support ticket"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        data = request.get_json()
        subject = data.get('subject')
        description = data.get('description')

        ticket_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO support_tickets (ticket_number, user_id, subject, description, status)
            VALUES (?, ?, ?, ?, ?)
        """, (ticket_number, current_user['user_id'], subject, description, 'open'))

        ticket_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({
            'message': 'Ticket created successfully',
            'ticket_id': ticket_id,
            'ticket_number': ticket_number
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/support/tickets', methods=['GET'])
def list_tickets():
    """List tickets. Customers see their own; support/admin see all."""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if current_user['role'] in ['support_agent', 'admin']:
            cursor.execute("""
                SELECT 
                    t.id,
                    t.ticket_number,
                    t.user_id,
                    u.full_name AS customer_name,
                    t.subject,
                    t.description,
                    t.status,
                    t.assigned_to,
                    t.created_at,
                    t.updated_at
                FROM support_tickets t
                LEFT JOIN users u ON t.user_id = u.id
                ORDER BY t.created_at DESC
            """)
        else:
            cursor.execute("""
                SELECT 
                    t.id,
                    t.ticket_number,
                    t.user_id,
                    u.full_name AS customer_name,
                    t.subject,
                    t.description,
                    t.status,
                    t.assigned_to,
                    t.created_at,
                    t.updated_at
                FROM support_tickets t
                LEFT JOIN users u ON t.user_id = u.id
                WHERE t.user_id = ?
                ORDER BY t.created_at DESC
            """, (current_user['user_id'],))

        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        tickets = [dict(row) for row in rows]

        return jsonify({'tickets': tickets}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/support/tickets/<int:ticket_id>', methods=['PATCH'])
def update_ticket(ticket_id):
    """Support agent/admin: update ticket status and assign"""
    token = request.headers.get('Authorization')
    if not token:
        return jsonify({'error': 'Unauthorized'}), 401

    if token.startswith('Bearer '):
        token = token[7:]

    current_user = verify_token(token)
    if not current_user:
        return jsonify({'error': 'Unauthorized'}), 401

    if not check_rbac_permission(current_user['role'], 'manage_tickets'):
        return jsonify({'error': 'Access denied'}), 403

    try:
        data = request.get_json()
        new_status = data.get('status')
        note_text = data.get('note')
        assigned_to = data.get('assigned_to', current_user['user_id'])

        if new_status not in ['open', 'in_progress', 'resolved']:
            return jsonify({'error': 'Invalid status'}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM support_tickets WHERE ticket_number = ?",
            (data.get('ticket_number'),)
        )

        cursor.execute("""
            UPDATE support_tickets
            SET status = ?, assigned_to = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, assigned_to, ticket_id))

        if note_text:
            cursor.execute("""
                INSERT INTO ticket_notes (ticket_id, user_id, note)
                VALUES (?, ?, ?)
            """, (ticket_id, current_user['user_id'], note_text))

        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'message': 'Ticket updated successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'service': 'web-app-service'}), 200


if __name__ == '__main__':
    print("=" * 60)
    print("Starting Web App Service on port 5003")
    print("=" * 60)
    app.run(host='0.0.0.0', port=5003, debug=False)
