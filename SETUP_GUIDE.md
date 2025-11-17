# Complete Setup Guide

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis 6+
- pip (Python package manager)

---

## Step 1: Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

**Required packages**:
- Flask (web framework)
- Flask-CORS (cross-origin resource sharing)
- Flask-Bcrypt (password hashing)
- psycopg2-binary (PostgreSQL adapter)
- PyJWT (JSON Web Tokens)
- redis (Redis client)
- python-dotenv (environment variables)
- pydantic (input validation)
- requests (inter-service communication)
- bleach (XSS prevention)

---

## Step 2: Setup PostgreSQL

### Option A: Local PostgreSQL

1. Install PostgreSQL:
   \`\`\`bash
   # Ubuntu/Debian
   sudo apt-get install postgresql postgresql-contrib
   
   # macOS (with Homebrew)
   brew install postgresql
   \`\`\`

2. Start PostgreSQL:
   \`\`\`bash
   # Ubuntu/Debian
   sudo systemctl start postgresql
   
   # macOS
   brew services start postgresql
   \`\`\`

3. Create database user (optional):
   \`\`\`bash
   sudo -u postgres psql
   CREATE USER banking_user WITH PASSWORD 'your_password';
   ALTER USER banking_user CREATEDB;
   \q
   \`\`\`

### Option B: Docker PostgreSQL

\`\`\`bash
docker run --name banking-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  -d postgres:14
\`\`\`

---

## Step 3: Setup Redis

### Option A: Local Redis

1. Install Redis:
   \`\`\`bash
   # Ubuntu/Debian
   sudo apt-get install redis-server
   
   # macOS (with Homebrew)
   brew install redis
   \`\`\`

2. Start Redis:
   \`\`\`bash
   # Ubuntu/Debian
   sudo systemctl start redis
   
   # macOS
   brew services start redis
   \`\`\`

### Option B: Docker Redis

\`\`\`bash
docker run --name banking-redis \
  -p 6379:6379 \
  -d redis:7
\`\`\`

---

## Step 4: Configure Environment Variables

1. Copy the example environment file:
   \`\`\`bash
   cp .env.example .env
   \`\`\`

2. Generate secure keys:
   \`\`\`bash
   # Generate SECRET_KEY
   python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(32))"
   
   # Generate INTERNAL_AUDIT_TOKEN
   python -c "import secrets; print('INTERNAL_AUDIT_TOKEN=' + secrets.token_urlsafe(32))"
   \`\`\`

3. Edit `.env` file with your values:
   \`\`\`bash
   # Database Configuration
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=banking_system
   DB_USER=postgres
   DB_PASSWORD=postgres
   
   # Redis Configuration
   REDIS_HOST=localhost
   REDIS_PORT=6379
   
   # Security (PASTE YOUR GENERATED KEYS HERE)
   SECRET_KEY=<your-generated-secret-key>
   INTERNAL_AUDIT_TOKEN=<your-generated-audit-token>
   
   # Service URLs (keep default for local development)
   AUTH_SERVICE_URL=http://localhost:5001
   RBAC_SERVICE_URL=http://localhost:5006
   ACCOUNT_SERVICE_URL=http://localhost:5002
   TRANSACTION_SERVICE_URL=http://localhost:5003
   ADMIN_SERVICE_URL=http://localhost:5004
   SUPPORT_SERVICE_URL=http://localhost:5005
   AUDIT_SERVICE_URL=http://localhost:5007
   
   # JWT Token Configuration
   ACCESS_TOKEN_TTL_SECONDS=900
   REFRESH_TOKEN_TTL_SECONDS=604800
   
   # Rate Limiting
   RATE_LIMIT_LOGIN_PER_MIN=5
   RATE_LIMIT_TRANSACTION_PER_MIN=20
   
   # Suspicious Activity Thresholds
   SUSPICIOUS_AMOUNT_THRESHOLD=10000.00
   LARGE_TRANSFER_THRESHOLD=5000.00
   MAX_TRANSFERS_PER_HOUR=10
   MAX_RAPID_TRANSFERS_IN_5_MIN=3
   \`\`\`

---

## Step 5: Initialize Database

Run the database initialization script:

\`\`\`bash
python database/init_db.py
\`\`\`

**What this does**:
- Creates `banking_system` database
- Creates all tables (users, accounts, transactions, support_tickets, audit_logs)
- Creates indexes for performance
- Seeds default admin user

**Default Admin Credentials**:
- Email: `admin@bank.com`
- Password: `Admin@123`
- ⚠️ **You MUST change these on first login!**

---

## Step 6: Start All Services

Run the services launcher:

\`\`\`bash
python run_services.py
\`\`\`

This will start all 8 microservices:
- Gateway (http://localhost:5000)
- Auth Service (http://localhost:5001)
- Account Service (http://localhost:5002)
- Transaction Service (http://localhost:5003)
- Admin Service (http://localhost:5004)
- Support Service (http://localhost:5005)
- RBAC Service (http://localhost:5006)
- Audit Service (http://localhost:5007)

**Note**: The script validates your SECRET_KEY on startup. If using the default key, it will warn you and ask for confirmation (only continue for development, never production).

---

## Step 7: Test the Application

### Test Admin First Login

\`\`\`bash
# 1. Login as admin
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bank.com",
    "password": "Admin@123"
  }'

# Save the access_token from response

# 2. Try to access admin endpoint (should be blocked)
curl -X GET http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer <your-access-token>"

# Response: 403 "You must change your password before accessing admin functions"

# 3. Change password
curl -X POST http://localhost:5000/api/admin/first-login \
  -H "Authorization: Bearer <your-access-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "new_email": "admin@bank.com",
    "new_password": "NewSecurePass@123",
    "new_full_name": "Bank Administrator"
  }'

# 4. Login with new credentials
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bank.com",
    "password": "NewSecurePass@123"
  }'

# 5. Now you can access admin endpoints
\`\`\`

### Test Customer Registration and Transfer

\`\`\`bash
# 1. Register a customer
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "password": "SecurePass@123"
  }'

# 2. Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass@123"
  }'

# 3. Create checking account
curl -X POST http://localhost:5000/api/accounts/create \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "checking",
    "opening_balance": 1000.00
  }'

# 4. Create savings account
curl -X POST http://localhost:5000/api/accounts/create \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "savings",
    "opening_balance": 5000.00
  }'

# 5. Internal transfer between own accounts
curl -X POST http://localhost:5000/api/transactions/internal-transfer \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 100.00,
    "description": "Savings deposit"
  }'

# 6. View transaction history
curl -X GET "http://localhost:5000/api/transactions/history?start_date=2024-01-01" \
  -H "Authorization: Bearer <customer-token>"
\`\`\`

---

## Step 8: Access Frontend (Optional)

If you build a frontend, it can connect to the gateway at:
\`\`\`
http://localhost:5000
\`\`\`

All API endpoints are available through the gateway, which handles:
- JWT verification
- Rate limiting
- Request routing to appropriate microservices
- Error handling

---

## Troubleshooting

### Issue: "Database connection failed"

**Solution**: Check PostgreSQL is running and credentials in `.env` are correct
\`\`\`bash
# Test connection
psql -h localhost -U postgres -d banking_system
\`\`\`

### Issue: "Redis connection failed"

**Solution**: Check Redis is running
\`\`\`bash
# Test connection
redis-cli ping
# Should respond: PONG
\`\`\`

### Issue: "Import error: No module named 'flask'"

**Solution**: Install dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

### Issue: "Port already in use"

**Solution**: Kill the process using the port or change port in service files
\`\`\`bash
# Find process
lsof -i :5000

# Kill process
kill -9 <PID>
\`\`\`

### Issue: "SECRET_KEY warning on startup"

**Solution**: Generate and set a secure SECRET_KEY in `.env`
\`\`\`bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
\`\`\`

---

## Production Deployment

### Docker Compose (Recommended)

\`\`\`bash
# Build and start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
\`\`\`

### Environment Variables for Production

**CRITICAL**: Update these before deploying:
- ✅ Set unique `SECRET_KEY` (32+ bytes)
- ✅ Set unique `INTERNAL_AUDIT_TOKEN` (32+ bytes)
- ✅ Use strong database password
- ✅ Enable SSL for PostgreSQL
- ✅ Use Redis password authentication
- ✅ Set appropriate rate limits
- ✅ Configure CORS allowed origins
- ✅ Use HTTPS for all service URLs
- ✅ Enable database backups
- ✅ Set up monitoring and alerting

---

## Testing Security Features

### Test Rate Limiting

\`\`\`bash
# Send 6 login requests quickly (should fail on 6th)
for i in {1..6}; do
  curl -X POST http://localhost:5000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"wrong"}'
  echo ""
done
\`\`\`

### Test Frozen Account

\`\`\`bash
# 1. Admin freezes account
curl -X PUT http://localhost:5000/api/accounts/1/status \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"status":"frozen","reason":"Suspicious activity"}'

# 2. Customer tries to transfer (should fail with 403)
curl -X POST http://localhost:5000/api/transactions/internal-transfer \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 100.00
  }'
\`\`\`

### Test Suspicious Activity Detection

\`\`\`bash
# Transfer large amount (>$10,000) to trigger alert
curl -X POST http://localhost:5000/api/transactions/external-transfer \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_number": "ACC1234567890",
    "amount": 15000.00,
    "description": "Large payment"
  }'

# Check audit logs for SUSPICIOUS_TRANSACTION event
curl -X GET "http://localhost:5000/api/admin/audit-logs?action=SUSPICIOUS_TRANSACTION" \
  -H "Authorization: Bearer <admin-token>"
\`\`\`

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review API documentation in `API_DOCUMENTATION.md`
3. Review security features in `SECURITY_FEATURES.md`
4. Check audit logs for error details
