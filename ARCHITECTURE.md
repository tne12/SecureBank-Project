# System Architecture - 3-Service Design

## Overview

The Online Banking System follows a **3-service microservices architecture** as specified by the project requirements. Each service has a specific responsibility and communicates via HTTP APIs.

\`\`\`
┌─────────────────────────────────────────────────────────────┐
│                     Client (Browser)                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │   Service 3: Web App (Port 5003)   │
        │   - Frontend UI                    │
        │   - Admin Panel                    │
        │   - Support Tickets                │
        │   - Audit Logs Display             │
        └──────────┬─────────────────┬───────┘
                   │                 │
         ┌─────────▼─────┐   ┌──────▼──────────┐
         │ Service 1:    │   │  Service 2:     │
         │ RBAC/Auth     │   │  Transaction    │
         │ (Port 5001)   │   │  (Port 5002)    │
         │               │   │                 │
         │ - JWT Auth    │   │ - Accounts      │
         │ - Login       │   │ - Transfers     │
         │ - Rate Limit  │   │ - Balance       │
         │ - RBAC Check  │   │ - Database      │
         └───────┬───────┘   └────────┬────────┘
                 │                    │
                 └──────────┬─────────┘
                            ▼
                 ┌──────────────────────┐
                 │   PostgreSQL DB      │
                 │   - Users            │
                 │   - Accounts         │
                 │   - Transactions     │
                 │   - Audit Logs       │
                 │   - Support Tickets  │
                 └──────────────────────┘
                            │
                 ┌──────────▼──────────┐
                 │   Redis Cache       │
                 │   - Rate Limiting   │
                 │   - Idempotency     │
                 └─────────────────────┘
\`\`\`

## Service Breakdown

### Service 1: RBAC/Auth Service (Port 5001)
**File**: `rbac_auth_service.py`

**Responsibilities**:
- User authentication (login/register)
- JWT token generation and validation
- Password validation and hashing
- Rate limiting (5 attempts per 15 min)
- RBAC permission checking
- Input sanitization

**Key Endpoints**:
- `POST /api/auth/register` - Register new customer
- `POST /api/auth/login` - Login with rate limiting
- `POST /api/auth/validate` - Validate JWT token
- `POST /api/rbac/check` - Check role permissions
- `GET /api/rbac/permissions/<role>` - Get role permissions

**Security Features**:
- Bcrypt password hashing
- JWT with 8-hour expiration
- Hard rate limiting with Redis
- Input sanitization (XSS prevention)
- Strong password requirements
- Email validation

---

### Service 2: Transaction Service (Port 5002)
**File**: `transaction_service.py`

**Responsibilities**:
- Account creation and management
- Internal transfers (between own accounts)
- External transfers (to other users)
- Transaction history with filters
- Account status management (freeze/unfreeze)
- Database operations (direct connection)
- Suspicious activity detection

**Key Endpoints**:
- `POST /api/accounts/create` - Create new account
- `GET /api/accounts/my-accounts` - Get user's accounts with recent transactions
- `GET /api/accounts/all` - Get all accounts (admin/support/auditor)
- `PATCH /api/accounts/<id>/status` - Update account status (admin only)
- `POST /api/transactions/internal-transfer` - Transfer between own accounts
- `POST /api/transactions/external-transfer` - Transfer to another user
- `GET /api/transactions/history` - Get transaction history with filters

**Security Features**:
- JWT verification via RBAC service
- SELECT FOR UPDATE row locking
- Idempotency keys (24-hour cache)
- Suspicious activity detection:
  - Large amounts (≥$10,000)
  - Rapid transfers (3+ in 5 minutes)
  - High volume (10+ per hour)
  - Large first-time transfers (≥$5,000 to new recipient)
- Frozen account enforcement (both sender AND receiver)
- Database transactions with ROLLBACK on error

---

### Service 3: Web App Service (Port 5003)
**File**: `web_app.py`

**Responsibilities**:
- Serve frontend HTML/CSS/JS
- Admin panel operations
- User management (CRUD)
- Role assignment
- Support ticket system
- Audit log storage and retrieval
- First-login password change

**Key Endpoints**:

**Admin**:
- `POST /api/admin/first-login` - Admin first-login password change (REQUIRED)
- `GET /api/admin/users` - Get all users
- `POST /api/admin/users` - Create new user
- `PATCH /api/admin/users/<id>/role` - Change user role

**Support**:
- `POST /api/support/tickets` - Create ticket (customer)
- `GET /api/support/tickets` - Get tickets (role-based view)
- `PUT /api/support/tickets/<id>/status` - Update ticket status (support/admin)

**Audit**:
- `POST /api/audit/log` - Write audit log (internal)
- `GET /api/audit/logs` - Get audit logs with filters (admin/auditor)

**Frontend**:
- `GET /` - Serve main application UI

**Security Features**:
- First-login enforcement for admin
- Audit log hash chaining (tamper detection)
- Role-based access control via RBAC service
- Comprehensive audit logging with IP and user agent

---

## Inter-Service Communication

Services communicate via **HTTP REST APIs**:

1. **Web App → RBAC/Auth**: Token validation, permission checks
2. **Web App → Transaction**: Forward account/transaction requests
3. **Transaction → RBAC/Auth**: Token validation, permission checks
4. **Transaction → Web App**: Audit logging
5. **All Services → Database**: Direct PostgreSQL connections

**Security**: All inter-service calls include JWT tokens in Authorization headers for verification.

---

## Database Schema

**Shared PostgreSQL database** (`banking_system`):

### Tables:
1. **users** - User accounts and credentials
2. **accounts** - Bank accounts (checking/savings)
3. **transactions** - All financial transactions
4. **support_tickets** - Customer support tickets
5. **ticket_notes** - Notes on support tickets
6. **audit_logs** - Security and audit trail

### Indexes:
- `users(email)` - Fast login lookups
- `accounts(account_number, user_id, status)` - Account queries
- `transactions(sender_account_id, receiver_account_id, created_at, idempotency_key)` - Transaction queries
- `audit_logs(user_id, action, created_at, severity)` - Audit searches

---

## RBAC Permission Matrix

| Feature/Action | Customer | Support Agent | Auditor | Admin |
|----------------|----------|---------------|---------|-------|
| Register/Login | ✓ | ✓ | ✓ | ✓ |
| Manage own profile | ✓ | ✓ | ✗ | ✓ |
| View own accounts | ✓ | ✓ | ✓ | ✓ |
| View all user accounts | ✗ | ✓ | ✓ | ✓ |
| Create accounts | ✓ | ✗ | ✗ | ✓ |
| Internal transfers | ✓ | ✗ | ✗ | ✓ |
| External transfers | ✓ | ✗ | ✗ | ✓ |
| View own transactions | ✓ | ✓ | ✓ | ✓ |
| View all transactions | ✗ | ✓ | ✓ | ✓ |
| Freeze/unfreeze accounts | ✗ | ✗ | ✗ | ✓ |
| Assign/change user roles | ✗ | ✗ | ✗ | ✓ |
| View audit/security logs | ✗ | ✗ | ✓ | ✓ |
| Manage support tickets | ✗ | ✓ | ✗ | ✓ |

---

## Security Measures Implemented

### 1. **Authentication & Authorization**
- JWT tokens with 8-hour expiration
- Bcrypt password hashing (12 rounds)
- Strong password requirements (8+ chars, uppercase, lowercase, digit, special char)
- RBAC permission matrix enforced at every endpoint

### 2. **Injection Prevention**
- Parameterized SQL queries (psycopg2)
- No string concatenation in queries
- Input sanitization (XSS prevention)

### 3. **Rate Limiting**
- 5 login attempts per 15 minutes per (IP + email)
- Redis-based distributed rate limiting
- Lockout with remaining time display

### 4. **Transaction Security**
- SELECT FOR UPDATE row-level locking
- Idempotency keys (prevent duplicate transactions)
- Atomic transactions with ROLLBACK on error
- Frozen account enforcement
- Suspicious activity detection

### 5. **Audit & Monitoring**
- Comprehensive logging of all actions
- Hash chain for tamper detection
- IP address and user agent tracking
- Severity levels (info, warning, critical)
- Suspicious transaction flagging

### 6. **Cryptography**
- Bcrypt for password hashing
- JWT for session management
- SHA256 for audit log hashing
- Secure random generation (secrets module)

### 7. **SSRF Prevention**
- Timeouts on all inter-service requests (5 seconds)
- No user-controlled URLs in requests
- Fixed service URLs in environment config

### 8. **Authorization**
- Hard RBAC checks before sensitive operations
- Admin first-login enforcement
- Role-based data access
- Audit logging of unauthorized attempts

---

## Running the System

### Prerequisites:
\`\`\`bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Install Redis
sudo apt-get install redis-server

# Install Python dependencies
pip install -r requirements.txt
\`\`\`

### Setup:
\`\`\`bash
# 1. Copy environment file
cp .env.example .env

# 2. Generate secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
# Add to .env: SECRET_KEY=<generated-key>

# 3. Initialize database
python database/init_db.py

# 4. Start all services
python run_all_services.py
\`\`\`

### Service URLs:
- **RBAC/Auth**: http://localhost:5001
- **Transaction**: http://localhost:5002
- **Web App**: http://localhost:5003

### Default Admin:
- **Email**: admin@bank.com
- **Password**: Admin@123
- **First Login**: MUST change password at `/api/admin/first-login`

---

## Testing the System

### 1. Register a Customer:
\`\`\`bash
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "password": "SecurePass123!"
  }'
\`\`\`

### 2. Login:
\`\`\`bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
\`\`\`

### 3. Create Account:
\`\`\`bash
curl -X POST http://localhost:5002/api/accounts/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "checking",
    "opening_balance": 1000.00
  }'
\`\`\`

### 4. Internal Transfer:
\`\`\`bash
curl -X POST http://localhost:5002/api/transactions/internal-transfer \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 100.00,
    "description": "Test transfer"
  }'
\`\`\`

---

## Deployment Notes

### Production Checklist:
- [ ] Change SECRET_KEY to strong random value
- [ ] Use production PostgreSQL instance
- [ ] Use production Redis instance
- [ ] Enable HTTPS/TLS
- [ ] Set up proper firewall rules
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerts
- [ ] Regular database backups
- [ ] Implement rate limiting at load balancer level
- [ ] Use environment-specific configs
