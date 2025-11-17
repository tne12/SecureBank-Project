# Setup Instructions - Secure Online Banking System

## Quick Start Guide

### Step 1: Install Dependencies

#### PostgreSQL
\`\`\`bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# macOS
brew install postgresql
brew services start postgresql

# Windows
# Download from: https://www.postgresql.org/download/windows/
\`\`\`

#### Redis
\`\`\`bash
# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis-server

# macOS
brew install redis
brew services start redis

# Windows
# Download from: https://github.com/microsoftarchive/redis/releases
\`\`\`

#### Python Dependencies
\`\`\`bash
pip install -r requirements.txt
\`\`\`

---

### Step 2: Configure Environment

\`\`\`bash
# Copy the example environment file
cp .env.example .env
\`\`\`

**Edit `.env` file**:
\`\`\`bash
# Generate a secure SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# Replace in .env:
SECRET_KEY=<your-generated-key-here>
\`\`\`

**Configure Database** (if not using defaults):
\`\`\`env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your-postgres-password
\`\`\`

---

### Step 3: Initialize Database

\`\`\`bash
# Run database initialization script
python database/init_db.py
\`\`\`

**Expected Output**:
\`\`\`
Database 'banking_system' created successfully
All tables created successfully
============================================================
Default admin created successfully
Email: admin@bank.com
Password: Admin@123
IMPORTANT: You MUST change password on first login
============================================================
\`\`\`

---

### Step 4: Start All Services

\`\`\`bash
# Run all 3 services at once
python run_all_services.py
\`\`\`

**Expected Output**:
\`\`\`
============================================================
Starting Secure Online Banking System
3-Service Architecture
============================================================

[1/3] Starting RBAC & Authentication Service...
✓ Redis connected for rate limiting
✓ RBAC & Authentication Service started on port 5001

[2/3] Starting Transaction Service (with Database)...
✓ Redis connected for idempotency keys
✓ Transaction Service started on port 5002

[3/3] Starting Web App Service...
✓ Web App Service started on port 5003

============================================================
✓ All services started successfully!
============================================================

📋 Service URLs:
  • RBAC/Auth Service:  http://localhost:5001
  • Transaction Service: http://localhost:5002
  • Web App:            http://localhost:5003

🔐 Default Admin Credentials:
  Email: admin@bank.com
  Password: Admin@123
  ⚠️  You MUST change password on first login!

⏹  Press Ctrl+C to stop all services
============================================================
\`\`\`

---

### Step 5: First Admin Login

The default admin **MUST** change password before accessing any admin functions.

#### Using curl:
\`\`\`bash
# 1. Login with default credentials
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@bank.com",
    "password": "Admin@123"
  }'

# Response includes token and is_first_login: true
# Copy the token from response

# 2. Change password (REQUIRED on first login)
curl -X POST http://localhost:5003/api/admin/first-login \
  -H "Authorization: Bearer <token-from-login>" \
  -H "Content-Type: application/json" \
  -d '{
    "new_email": "admin@yourbank.com",
    "new_password": "NewSecurePassword123!",
    "new_full_name": "Bank Administrator"
  }'

# 3. Login with new credentials
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@yourbank.com",
    "password": "NewSecurePassword123!"
  }'
\`\`\`

---

## Testing the System

### 1. Register a New Customer

\`\`\`bash
curl -X POST http://localhost:5001/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Alice Johnson",
    "email": "alice@example.com",
    "phone": "+1234567890",
    "password": "SecurePass123!"
  }'
\`\`\`

### 2. Login as Customer

\`\`\`bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "SecurePass123!"
  }'
\`\`\`

Save the token from the response.

### 3. Create a Bank Account

\`\`\`bash
curl -X POST http://localhost:5002/api/accounts/create \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "checking",
    "opening_balance": 5000.00
  }'
\`\`\`

### 4. View Your Accounts

\`\`\`bash
curl -X GET http://localhost:5002/api/accounts/my-accounts \
  -H "Authorization: Bearer <customer-token>"
\`\`\`

### 5. Create Second Account

\`\`\`bash
curl -X POST http://localhost:5002/api/accounts/create \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "account_type": "savings",
    "opening_balance": 10000.00
  }'
\`\`\`

### 6. Internal Transfer (Between Own Accounts)

\`\`\`bash
curl -X POST http://localhost:5002/api/transactions/internal-transfer \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 500.00,
    "description": "Transfer to savings"
  }'
\`\`\`

### 7. External Transfer (To Another User)

First, register another user and create an account. Then:

\`\`\`bash
curl -X POST http://localhost:5002/api/transactions/external-transfer \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_number": "1234567890123456",
    "amount": 250.00,
    "description": "Payment to Bob"
  }'
\`\`\`

### 8. View Transaction History

\`\`\`bash
curl -X GET "http://localhost:5002/api/transactions/history?account_id=1" \
  -H "Authorization: Bearer <customer-token>"
\`\`\`

### 9. Create Support Ticket (Customer)

\`\`\`bash
curl -X POST http://localhost:5003/api/support/tickets \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "subject": "Unable to transfer large amount",
    "description": "I am trying to transfer $15,000 but it keeps failing"
  }'
\`\`\`

### 10. View Audit Logs (Admin)

\`\`\`bash
curl -X GET "http://localhost:5003/api/audit/logs?limit=50" \
  -H "Authorization: Bearer <admin-token>"
\`\`\`

---

## Troubleshooting

### Service Won't Start

**Error**: `SECRET_KEY is default value`
\`\`\`bash
# Solution: Generate and set a secure key
python -c "import secrets; print(secrets.token_hex(32))"
# Add to .env file
\`\`\`

**Error**: `Redis connection failed`
\`\`\`bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# Start Redis if not running
sudo systemctl start redis-server  # Linux
brew services start redis          # macOS
\`\`\`

**Error**: `PostgreSQL connection failed`
\`\`\`bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list                # macOS

# Check connection
psql -U postgres -h localhost
\`\`\`

### Database Issues

**Error**: `database "banking_system" does not exist`
\`\`\`bash
# Run initialization script
python database/init_db.py
\`\`\`

**Error**: `relation "users" does not exist`
\`\`\`bash
# Drop and recreate database
psql -U postgres -h localhost
DROP DATABASE banking_system;
\q

# Re-run initialization
python database/init_db.py
\`\`\`

### Port Already in Use

\`\`\`bash
# Find process using port 5001, 5002, or 5003
lsof -i :5001
lsof -i :5002
lsof -i :5003

# Kill the process
kill -9 <PID>
\`\`\`

### Token Validation Fails

**Error**: `Token has expired`
- JWT tokens expire after 8 hours
- Login again to get a new token

**Error**: `Invalid token`
- Ensure you're using the correct token format: `Bearer <token>`
- Check that SECRET_KEY is the same across all services

---

## Security Testing

### Test Rate Limiting

\`\`\`bash
# Try to login 6 times with wrong password
for i in {1..6}; do
  curl -X POST http://localhost:5001/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email": "test@example.com", "password": "wrong"}'
  echo "\nAttempt $i"
done

# Should be locked out after 5 attempts
\`\`\`

### Test RBAC

\`\`\`bash
# Try to freeze account as customer (should fail)
curl -X PATCH http://localhost:5002/api/accounts/1/status \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "frozen"}'

# Should return: {"error": "Access denied. Admin only."}
\`\`\`

### Test Frozen Account

\`\`\`bash
# As admin, freeze an account
curl -X PATCH http://localhost:5002/api/accounts/1/status \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "frozen", "reason": "Suspicious activity"}'

# Try to transfer from frozen account (should fail)
curl -X POST http://localhost:5002/api/transactions/internal-transfer \
  -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 100.00
  }'

# Should return error about account being frozen
\`\`\`

### Test Idempotency

\`\`\`bash
# Send same transfer twice with idempotency key
curl -X POST http://localhost:5002/api/transactions/internal-transfer \
  -H "Authorization: Bearer <customer-token>" \
  -H "Idempotency-Key: unique-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "from_account_id": 1,
    "to_account_id": 2,
    "amount": 100.00
  }'

# Send exact same request again
# Should return cached result, no duplicate transaction
\`\`\`

---

## Production Deployment

### Before Going Live:

1. **Change all default credentials**
   - Admin password
   - Database password
   - SECRET_KEY

2. **Enable HTTPS**
   - Get SSL/TLS certificates
   - Configure reverse proxy (nginx/Apache)

3. **Use production database**
   - Separate DB server
   - Regular backups
   - Replication for HA

4. **Secure Redis**
   - Enable authentication
   - Bind to localhost or private network

5. **Set up monitoring**
   - Log aggregation (ELK stack)
   - Performance monitoring (Prometheus/Grafana)
   - Error tracking (Sentry)

6. **Configure firewall**
   - Only expose necessary ports
   - Use VPC for inter-service communication

7. **Environment-specific configs**
   - Use separate .env files for dev/staging/prod
   - Never commit .env files to git

---

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review audit logs for security events
3. Check service logs for errors
4. Verify all environment variables are set correctly
