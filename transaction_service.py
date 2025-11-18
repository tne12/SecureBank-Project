"""
Transaction Service (with Database)
Handles: Accounts, transactions, balance management, database operations
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import random
import string
import redis
import requests
import sqlite3

app = Flask(__name__)
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


# Redis for idempotency (optional)
try:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=2,
        decode_responses=True,
    )
    redis_client.ping()
    print("✓ Redis connected for idempotency keys")
except Exception as e:
    print(f"✗ Redis connection failed: {e}")
    redis_client = None

# Service URLs
RBAC_AUTH_URL = os.getenv("RBAC_AUTH_URL", "http://localhost:5001")
WEB_APP_URL = os.getenv("WEB_APP_URL", "http://localhost:5003")

SUSPICIOUS_AMOUNT_THRESHOLD = 10000.00
MAX_RAPID_TRANSFERS = 5
RAPID_TRANSFER_WINDOW_MINUTES = 10


def generate_account_number():
    """Generate a random account number"""
    return "".join(random.choices(string.digits, k=12))


def generate_ticket_number():
    """Generate a random ticket number"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


def validate_token_and_get_user(request):
    """Validate JWT token via RBAC service and return user info or None"""
    token = request.headers.get("Authorization")
    if not token:
        return None

    if token.startswith("Bearer "):
        token = token[7:]

    try:
        response = requests.post(
            f"{RBAC_AUTH_URL}/api/auth/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("valid"):
                return data.get("user")
    except Exception:
        pass

    return None


def check_rbac_permission(role, action):
    """Check permission via RBAC service"""
    try:
        response = requests.post(
            f"{RBAC_AUTH_URL}/api/rbac/check",
            json={"role": role, "action": action},
            timeout=5,
        )
        if response.status_code == 200:
            result = response.json()
            return result.get("allowed", False)
    except Exception:
        pass
    return False


def create_audit_log(
    user_id,
    action,
    resource_type=None,
    resource_id=None,
    details=None,
    severity="info",
):
    """Send audit log to Web App service"""
    try:
        payload = {
            "user_id": user_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "severity": severity,
        }
        requests.post(f"{WEB_APP_URL}/api/audit/log", json=payload, timeout=3)
    except Exception:
        # Don't crash on audit failures
        pass


def is_suspicious_transaction(user_id, amount, sender_account_id):
    """Detect suspicious pattern: many transfers in short window + big amount"""
    if amount >= SUSPICIOUS_AMOUNT_THRESHOLD:
        return True

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM transactions t
            JOIN accounts a ON t.sender_account_id = a.id
            WHERE a.user_id = ?
              AND t.created_at > datetime('now', '-' || ? || ' minutes')
        """,
            (user_id, RAPID_TRANSFER_WINDOW_MINUTES),
        )

        recent_count = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        if recent_count >= MAX_RAPID_TRANSFERS:
            return True
    except Exception:
        pass

    return False


def get_idempotency_key(request):
    """Fetch idempotency key from headers"""
    return request.headers.get("Idempotency-Key")


def check_idempotency(key):
    """Check if the idempotency key is already used"""
    if not redis_client or not key:
        return None
    try:
        return redis_client.get(f"idempotency:{key}")
    except Exception:
        return None


def store_idempotency(key, transaction_id):
    """Store idempotency key with transaction ID"""
    if not redis_client or not key:
        return
    try:
        redis_client.setex(f"idempotency:{key}", 3600, transaction_id)
    except Exception:
        pass


@app.route("/")
def root():
    return jsonify({"service": "transaction-service", "status": "running"}), 200


# ---------- ACCOUNTS HELPERS & ENDPOINTS ----------


def fetch_accounts_for_user(current_user):
    """
    Return a list[dict] of accounts visible to current_user.
    This is a pure helper that only talks to the DB.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Staff roles can see all accounts
        if current_user["role"] in ["support_agent", "auditor", "admin"]:
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.account_number,
                    a.account_type,
                    a.balance,
                    a.status,
                    u.full_name AS owner_name,
                    u.email     AS owner_email
                FROM accounts a
                JOIN users u ON a.user_id = u.id
                ORDER BY a.id DESC
                """
            )
        else:
            # Regular customer: only see their own accounts
            cursor.execute(
                """
                SELECT
                    a.id,
                    a.account_number,
                    a.account_type,
                    a.balance,
                    a.status
                FROM accounts a
                WHERE a.user_id = ?
                ORDER BY a.id DESC
                """,
                (current_user["user_id"],),
            )


        rows = cursor.fetchall()
        accounts = [dict(row) for row in rows]

        # Make sure every account has recent_transactions list
        for acc in accounts:
            if "recent_transactions" not in acc:
                acc["recent_transactions"] = []

        return accounts


    finally:
        cursor.close()
        conn.close()


def create_account_core(current_user, data):
    """Core logic for creating an account. Returns the new account row as dict."""
    account_type = data.get("account_type", "checking")
    opening_balance = float(data.get("opening_balance", 0.0))
    target_user_id = data.get("user_id") or current_user["user_id"]

    if account_type not in ["checking", "savings"]:
        raise ValueError("Invalid account type")

    account_number = generate_account_number()

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id FROM users WHERE id = ?", (target_user_id,))
        if not cursor.fetchone():
            raise ValueError("Target user does not exist")

        cursor.execute(
            """
            INSERT INTO accounts (account_number, user_id, account_type, balance, status)
            VALUES (?, ?, ?, ?, ?)
        """,
            (account_number, target_user_id, account_type, opening_balance, "active"),
        )

        account_id = cursor.lastrowid
        conn.commit()

        create_audit_log(
            user_id=current_user["user_id"],
            action="create_account",
            resource_type="account",
            resource_id=account_id,
            details=f"Account {account_number} created for user {target_user_id}",
        )

        return {
            "id": account_id,
            "account_number": account_number,
            "account_type": account_type,
            "balance": opening_balance,
            "status": "active",
        }
    finally:
        cursor.close()
        conn.close()


@app.route("/api/accounts/create", methods=["POST"])
def create_account_legacy():
    """
    Legacy endpoint used by the frontend: POST /api/accounts/create
    Just forwards to create_account().
    """
    return create_account()


@app.route("/api/accounts", methods=["POST"])
def create_account():
    """Create a new account (customer or admin) and return updated list."""
    current_user = validate_token_and_get_user(request)
    if not current_user:
        return jsonify([]), 401

    if not check_rbac_permission(current_user["role"], "create_accounts"):
        return jsonify([]), 403

    try:
        data = request.get_json() or {}
        create_account_core(current_user, data)

        # After creating, return the updated list of accounts as an array
        accounts = fetch_accounts_for_user(current_user)
        return jsonify(accounts), 201

    except Exception as e:
        print("Error in POST /api/accounts:", e)
        return jsonify([]), 500



@app.route("/api/accounts", methods=["GET"])
def get_accounts():
    """
    Generic accounts endpoint.
    Returns a plain JSON array: [ {...}, {...} ]
    """
    current_user = validate_token_and_get_user(request)
    if not current_user:
        # Frontend expects an array, even on error
        return jsonify([]), 401

    try:
        accounts = fetch_accounts_for_user(current_user)
        # Return just the list
        return jsonify(accounts), 200
    except Exception as e:
        print("Error in /api/accounts:", e)
        # On error, still return an empty array so .length / .map are safe
        return jsonify([]), 500


@app.route("/api/accounts/my-accounts", methods=["GET"])
def get_my_accounts():
    """
    Endpoint used by the My Accounts tab.
    Also returns a plain JSON array.
    """
    current_user = validate_token_and_get_user(request)
    if not current_user:
        return jsonify([]), 401

    try:
        accounts = fetch_accounts_for_user(current_user)
        return jsonify(accounts), 200
    except Exception as e:
        print("Error in /api/accounts/my-accounts:", e)
        return jsonify([]), 500


@app.route("/api/accounts/<int:account_id>/status", methods=["PATCH"])
def update_account_status(account_id):
    """Admin can freeze/unfreeze/close account"""
    current_user = validate_token_and_get_user(request)
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    if not check_rbac_permission(current_user["role"], "freeze_unfreeze_accounts"):
        return jsonify({"error": "Access denied. Admin only."}), 403

    try:
        data = request.get_json() or {}

        if "status" not in data or data["status"] not in ["active", "frozen", "closed"]:
            return jsonify({"error": "Valid status required"}), 400

        new_status = data["status"]
        reason = data.get("reason", "Status changed by admin")

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id, account_number, status FROM accounts WHERE id = ?",
            (account_id,),
        )
        account = cursor.fetchone()
        if not account:
            cursor.close()
            conn.close()
            return jsonify({"error": "Account not found"}), 404

        cursor.execute(
            """
            UPDATE accounts
               SET status = ?, updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
        """,
            (new_status, account_id),
        )

        conn.commit()
        cursor.close()
        conn.close()

        create_audit_log(
            user_id=current_user["user_id"],
            action="update_account_status",
            resource_type="account",
            resource_id=account_id,
            details=f"Status changed to {new_status}. Reason: {reason}",
        )

        return jsonify({"message": "Account status updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---------- TRANSFERS & TRANSACTIONS ----------


def perform_transfer(
    sender_id, receiver_id, amount, description, transaction_type, idempotency_key=None
):
    """Core transfer logic used by internal/external transfer endpoints"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT id, account_number, balance, status, user_id
            FROM accounts
            WHERE id IN (?, ?)
        """,
            (sender_id, receiver_id),
        )

        accounts = cursor.fetchall()
        if len(accounts) != 2:
            raise ValueError("One or both accounts not found")

        sender = None
        receiver = None
        for acc in accounts:
            if acc["id"] == sender_id:
                sender = acc
            elif acc["id"] == receiver_id:
                receiver = acc

        if not sender or not receiver:
            raise ValueError("Could not map sender/receiver accounts")

        if sender["status"] != "active" or receiver["status"] != "active":
            raise ValueError("Both accounts must be active for transfer")

        if sender["balance"] < amount:
            raise ValueError("Insufficient balance")

        cursor.execute(
            """
            UPDATE accounts
               SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
        """,
            (amount, sender_id),
        )

        cursor.execute(
            """
            UPDATE accounts
               SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP
             WHERE id = ?
        """,
            (amount, receiver_id),
        )

        transaction_id = "".join(
            random.choices(string.ascii_uppercase + string.digits, k=16)
        )

        cursor.execute(
            """
            INSERT INTO transactions (
                transaction_id,
                idempotency_key,
                sender_account_id,
                receiver_account_id,
                amount,
                transaction_type,
                description,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                transaction_id,
                idempotency_key,
                sender_id,
                receiver_id,
                amount,
                transaction_type,
                description,
                "completed",
            ),
        )

        conn.commit()

        return {
            "transaction_id": transaction_id,
            "sender_account_id": sender_id,
            "receiver_account_id": receiver_id,
            "amount": amount,
            "transaction_type": transaction_type,
            "description": description,
            "status": "completed",
        }

    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()


@app.route("/api/transfers/internal", methods=["POST"])
def internal_transfer():
    """Transfer between own accounts"""
    current_user = validate_token_and_get_user(request)
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    if not check_rbac_permission(current_user["role"], "internal_transfers"):
        return jsonify({"error": "Access denied"}), 403

    try:
        data = request.get_json() or {}
        from_account_id = int(data.get("from_account_id"))
        to_account_id = int(data.get("to_account_id"))
        amount = float(data.get("amount", 0))
        description = data.get("description", "Internal transfer")

        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id FROM accounts
            WHERE id = ? AND user_id = ?
        """,
            (from_account_id, current_user["user_id"]),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Source account not owned by user"}), 403

        cursor.execute(
            """
            SELECT id FROM accounts
            WHERE id = ? AND user_id = ?
        """,
            (to_account_id, current_user["user_id"]),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Destination account not owned by user"}), 403

        cursor.close()
        conn.close()

        idempotency_key = get_idempotency_key(request)
        if idempotency_key:
            existing = check_idempotency(idempotency_key)
            if existing:
                return jsonify(
                    {
                        "message": "Duplicate request. Returning original transaction.",
                        "transaction_id": existing,
                    }
                ), 200

        result = perform_transfer(
            sender_id=from_account_id,
            receiver_id=to_account_id,
            amount=amount,
            description=description,
            transaction_type="internal_transfer",
            idempotency_key=idempotency_key,
        )

        if is_suspicious_transaction(
            current_user["user_id"], amount, from_account_id
        ):
            create_audit_log(
                user_id=current_user["user_id"],
                action="suspicious_transfer_internal",
                resource_type="transaction",
                resource_id=None,
                details=f"Suspicious internal transfer of {amount} from account {from_account_id}",
                severity="warning",
            )

        if idempotency_key:
            store_idempotency(idempotency_key, result["transaction_id"])

        create_audit_log(
            user_id=current_user["user_id"],
            action="internal_transfer",
            resource_type="transaction",
            resource_id=None,
            details=f"Internal transfer of {amount} from {from_account_id} to {to_account_id}",
        )

        return jsonify({"message": "Transfer completed", "transaction": result}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/transfers/external", methods=["POST"])
def external_transfer():
    """Transfer to another user's account"""
    current_user = validate_token_and_get_user(request)
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    if not check_rbac_permission(current_user["role"], "external_transfers"):
        return jsonify({"error": "Access denied"}), 403

    try:
        data = request.get_json() or {}
        from_account_id = int(data.get("from_account_id"))
        target_account_number = str(data.get("to_account_number") or "").strip()

        amount = float(data.get("amount", 0))
        description = data.get("description", "External transfer")

        if amount <= 0:
            return jsonify({"error": "Amount must be positive"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id FROM accounts
            WHERE id = ? AND user_id = ?
        """,
            (from_account_id, current_user["user_id"]),
        )
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return jsonify({"error": "Source account not owned by user"}), 403

        cursor.execute(
            """
            SELECT id FROM accounts
            WHERE account_number = ?
        """,
            (target_account_number,),
        )
        target_row = cursor.fetchone()
        if not target_row:
            cursor.close()
            conn.close()
            return jsonify({"error": "Target account not found"}), 404

        to_account_id = target_row["id"]
        cursor.close()
        conn.close()

        idempotency_key = get_idempotency_key(request)
        if idempotency_key:
            existing = check_idempotency(idempotency_key)
            if existing:
                return jsonify(
                    {
                        "message": "Duplicate request. Returning original transaction.",
                        "transaction_id": existing,
                    }
                ), 200

        result = perform_transfer(
            sender_id=from_account_id,
            receiver_id=to_account_id,
            amount=amount,
            description=description,
            transaction_type="external_transfer",
            idempotency_key=idempotency_key,
        )

        if is_suspicious_transaction(
            current_user["user_id"], amount, from_account_id
        ):
            create_audit_log(
                user_id=current_user["user_id"],
                action="suspicious_transfer_external",
                resource_type="transaction",
                resource_id=None,
                details=f"Suspicious external transfer of {amount} from account {from_account_id}",
                severity="critical",
            )

        if idempotency_key:
            store_idempotency(idempotency_key, result["transaction_id"])

        create_audit_log(
            user_id=current_user["user_id"],
            action="external_transfer",
            resource_type="transaction",
            resource_id=None,
            details=f"External transfer of {amount} from {from_account_id} to {to_account_id}",
        )

        return jsonify({"message": "Transfer completed", "transaction": result}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """Get transactions for current user (or all for support/auditor/admin) with filters"""
    current_user = validate_token_and_get_user(request)
    if not current_user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT 
                t.id,
                t.transaction_id,
                t.sender_account_id,
                t.receiver_account_id,
                t.amount,
                t.transaction_type,
                t.description,
                t.status,
                t.created_at,
                sa.account_number AS sender_account_number,
                ra.account_number AS receiver_account_number,
                su.full_name AS sender_user,
                ru.full_name AS receiver_user
            FROM transactions t
            LEFT JOIN accounts sa ON t.sender_account_id = sa.id
            LEFT JOIN users su ON sa.user_id = su.id
            LEFT JOIN accounts ra ON t.receiver_account_id = ra.id
            LEFT JOIN users ru ON ra.user_id = ru.id
            WHERE 1=1
        """

        params = []

        if current_user["role"] not in ["support_agent", "auditor", "admin"]:
            query += " AND (sa.user_id = ? OR ra.user_id = ?)"
            params.extend([current_user["user_id"], current_user["user_id"]])

        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        transaction_type = request.args.get("type")
        min_amount = request.args.get("min_amount")
        max_amount = request.args.get("max_amount")

        if start_date:
            query += " AND t.created_at >= ?"
            params.append(start_date)

        if end_date:
            query += " AND t.created_at <= ?"
            params.append(end_date)

        if transaction_type:
            query += " AND t.transaction_type = ?"
            params.append(transaction_type)

        if min_amount:
            query += " AND t.amount >= ?"
            params.append(float(min_amount))

        if max_amount:
            query += " AND t.amount <= ?"
            params.append(float(max_amount))

        query += " ORDER BY t.created_at DESC LIMIT ?"
        params.append(int(request.args.get("limit", 100)))

        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()

        transactions = [dict(row) for row in rows]

        return jsonify({"transactions": transactions}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "transaction-service"}), 200


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Transaction Service (with Database) on port 5002")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5002, debug=False)
