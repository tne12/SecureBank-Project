# Secure Online Banking System

A production-ready, secure online banking system built with Flask, featuring comprehensive security measures and role-based access control.

## 🏗️ Architecture

**3-Service Microservices Design** (as per project requirements):

1. **RBAC/Auth Service** (Port 5001) - Authentication, JWT, RBAC, rate limiting
2. **Transaction Service** (Port 5002) - Accounts, transfers, database operations
3. **Web App** (Port 5003) - Frontend, admin panel, support, audit logs

## ✨ Features

### Core Banking
- ✅ User registration and authentication
- ✅ Multiple account types (checking/savings)
- ✅ Internal transfers (between own accounts)
- ✅ External transfers (to other users)
- ✅ Transaction history with filters
- ✅ Account status management (active/frozen/closed)

### Security
- ✅ JWT authentication with 8-hour expiration
- ✅ Bcrypt password hashing (12 rounds)
- ✅ Hard rate limiting (5 attempts per 15 min)
- ✅ RBAC permission matrix enforcement
- ✅ SQL injection prevention (parameterized queries)
- ✅ XSS prevention (input sanitization)
- ✅ Transaction atomicity with row-level locking
- ✅ Idempotency keys (prevent duplicate transactions)
- ✅ Suspicious activity detection
- ✅ Comprehensive audit logging with hash chaining

### User Roles
- **Customer** - Create accounts, make transfers, view own data
- **Support Agent** - View all data, manage support tickets
- **Auditor** - Read-only access to all data and audit logs
- **Admin** - Full system access, user management, account freezing

### Admin Features
- ✅ User management (create, update, delete)
- ✅ Role assignment
- ✅ Account freeze/unfreeze
- ✅ Audit log viewing
- ✅ First-login password change enforcement

### Support System
- ✅ Customer ticket creation
- ✅ Support agent ticket management
- ✅ Ticket status tracking (open/in_progress/resolved)
- ✅ Ticket notes and communication

### Audit & Compliance
- ✅ All actions logged with IP and user agent
- ✅ Failed login attempt tracking
- ✅ Suspicious transaction flagging
- ✅ Account status change logging
- ✅ Admin operation tracking
- ✅ Hash chain for tamper detection

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- Redis 6+

### Installation

\`\`\`bash
# 1. Clone repository
git clone <repository-url>
cd banking-system

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env

# Generate secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"
# Add to .env file

# 4. Initialize database
python database/init_db.py

# 5. Start all services
python run_all_services.py
\`\`\`

### Default Admin Credentials
\`\`\`
Email: admin@bank.com
Password: Admin@123
⚠️ MUST change on first login!
\`\`\`

## 📚 Documentation

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Detailed 3-service architecture
- **[SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md)** - Complete setup and testing
- **[SECURITY_FEATURES.md](SECURITY_FEATURES.md)** - Security implementation details
- **[API_DOCUMENTATION.md](API_DOCUMENTATION.md)** - API endpoints reference

## 🔒 Security Measures

### 1. Authentication & Authorization
- JWT tokens with expiration
- Bcrypt password hashing (12 rounds)
- Strong password requirements
- RBAC permission matrix

### 2. Injection Prevention
- Parameterized SQL queries
- Input sanitization
- No string concatenation in queries

### 3. Rate Limiting
- 5 login attempts per 15 minutes
- Redis-based distributed rate limiting
- Per-IP and per-email tracking

### 4. Transaction Security
- Row-level locking (SELECT FOR UPDATE)
- Idempotency keys (24-hour cache)
- Atomic transactions with rollback
- Frozen account enforcement (sender AND receiver)
- Suspicious activity detection

### 5. Audit & Monitoring
- Comprehensive action logging
- Hash chain for tamper detection
- IP address tracking
- User agent tracking
- Severity levels (info, warning, critical)

### 6. Cryptography
- Bcrypt for passwords
- JWT for sessions
- SHA256 for audit hashing
- Secure random generation

## 📊 RBAC Permission Matrix

| Feature | Customer | Support Agent | Auditor | Admin |
|---------|----------|---------------|---------|-------|
| Register/Login | ✓ | ✓ | ✓ | ✓ |
| Create accounts | ✓ | ✗ | ✗ | ✓ |
| Transfers | ✓ | ✗ | ✗ | ✓ |
| View all accounts | ✗ | ✓ | ✓ | ✓ |
| Freeze accounts | ✗ | ✗ | ✗ | ✓ |
| Manage users | ✗ | ✗ | ✗ | ✓ |
| Support tickets | ✗ | ✓ | ✗ | ✓ |
| Audit logs | ✗ | ✗ | ✓ | ✓ |

## 🧪 Testing

### Register Customer
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

### Create Account
\`\`\`bash
curl -X POST http://localhost:5002/api/accounts/create \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "checking",
    "opening_balance": 5000.00
  }'
\`\`\`

### Transfer Money
\`\`\`bash
curl -X POST http://localhost:5002/api/transactions/internal-transfer \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: unique-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 500.00
  }'
\`\`\`

## 📋 API Endpoints

### RBAC/Auth Service (5001)
- `POST /api/auth/register` - Register customer
- `POST /api/auth/login` - Login with rate limiting
- `POST /api/auth/validate` - Validate JWT token
- `POST /api/rbac/check` - Check permission
- `GET /api/rbac/permissions/<role>` - Get role permissions

### Transaction Service (5002)
- `POST /api/accounts/create` - Create account
- `GET /api/accounts/my-accounts` - Get user accounts with recent transactions
- `GET /api/accounts/all` - Get all accounts (admin/support/auditor)
- `PATCH /api/accounts/<id>/status` - Update account status (admin only)
- `POST /api/transactions/internal-transfer` - Internal transfer (atomic)
- `POST /api/transactions/external-transfer` - External transfer (atomic)
- `GET /api/transactions/history` - Transaction history with filters

### Web App (5003)
- `POST /api/admin/first-login` - Admin first-login password change (REQUIRED)
- `GET /api/admin/users` - Get all users
- `POST /api/admin/users` - Create user
- `PATCH /api/admin/users/<id>/role` - Change user role
- `GET /api/audit/logs` - Get audit logs with filters
- `POST /api/support/tickets` - Create support ticket
- `GET /api/support/tickets` - Get tickets (role-based)
- `PUT /api/support/tickets/<id>/status` - Update ticket status

## 🛠️ Technology Stack

- **Backend**: Python Flask 3.0
- **Database**: PostgreSQL 12+
- **Cache**: Redis 6+
- **Authentication**: JWT (PyJWT)
- **Password Hashing**: Bcrypt
- **HTTP Client**: Requests library

## 📦 Project Structure

\`\`\`
banking-system/
├── database/
│   └── init_db.py              # Database setup with default admin
├── rbac_auth_service.py        # Service 1: Auth + RBAC
├── transaction_service.py      # Service 2: Transactions + Database
├── web_app.py                  # Service 3: Admin + Support + Audit
├── run_all_services.py         # Start all 3 services
├── requirements.txt            # Python dependencies
├── .env.example                # Environment template
├── ARCHITECTURE.md             # System design documentation
├── SETUP_INSTRUCTIONS.md       # Setup and testing guide
└── README.md                   # This file
\`\`\`

## 📝 Project Requirements Satisfied

✅ 3-service microservices architecture  
✅ Flask backend  
✅ No Docker (runs natively)  
✅ Role-Based Access Control (4 roles)  
✅ User registration and authentication  
✅ Account creation and management  
✅ Internal and external transfers  
✅ Transaction history with filters  
✅ Support ticket system  
✅ Admin panel with user management  
✅ Audit logging system  
✅ Account status management  
✅ All security measures implemented:
  - Injection prevention
  - SSRF prevention
  - Authentication & authorization
  - RBAC enforcement
  - Cryptography (Bcrypt, JWT, SHA256)
  - Rate limiting
  - Audit logging
  - Input validation

## 🤝 Team Contributions

This project was developed for EECE503M - Software Security at the American University of Beirut. Individual contributions are documented in the project report.

## 🔐 Security Testing Scenarios

1. **Rate Limiting**: Try 6 failed login attempts
2. **RBAC**: Try accessing admin endpoints as customer
3. **Frozen Accounts**: Freeze account, attempt transfer (blocked)
4. **Idempotency**: Send same transfer twice with same key
5. **Suspicious Activity**: Transfer $15,000 (flagged)
6. **First-Login**: Admin must change password before accessing functions
7. **Audit Integrity**: Verify hash chain with verification endpoint

## 📄 License

Academic project - American University of Beirut EECE503M

## 🔐 Production Deployment Notes

### Before Going Live:

1. **Change all default credentials**
   - Generate strong SECRET_KEY
   - Change default admin password
   - Use production database credentials

2. **Enable HTTPS**
   - Get SSL/TLS certificates
   - Configure reverse proxy (nginx)

3. **Secure services**
   - Use environment-specific configs
   - Enable Redis authentication
   - Set up firewall rules

4. **Monitoring**
   - Log aggregation (ELK stack)
   - Performance monitoring
   - Error tracking

5. **Regular maintenance**
   - Database backups
   - Security updates
   - Audit log archiving

For detailed deployment instructions, see [SETUP_INSTRUCTIONS.md](SETUP_INSTRUCTIONS.md).
