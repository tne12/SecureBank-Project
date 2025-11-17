# Online Banking System - API Documentation

## Base URL
\`\`\`
http://localhost:5000
\`\`\`

All requests go through the API Gateway which handles JWT verification, rate limiting, and service routing.

---

## Authentication Endpoints

### 1. Register New User
**POST** `/api/auth/register`

**Request Body:**
\`\`\`json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+1234567890",
  "password": "SecurePass@123"
}
\`\`\`

**Response:** `201 Created`
\`\`\`json
{
  "message": "User registered successfully",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": "john@example.com",
    "role": "customer"
  }
}
\`\`\`

**Password Requirements:**
- Minimum 8 characters
- At least 1 uppercase, 1 lowercase, 1 digit, 1 special character

---

### 2. Login
**POST** `/api/auth/login`

**Rate Limit:** 5 attempts per 15 minutes per IP

**Request Body:**
\`\`\`json
{
  "email": "john@example.com",
  "password": "SecurePass@123"
}
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "full_name": "John Doe",
    "email": "john@example.com",
    "role": "customer"
  }
}
\`\`\`

---

### 3. Refresh Token
**POST** `/api/auth/refresh`

**Headers:**
\`\`\`
Authorization: Bearer <refresh_token>
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "access_token": "new_access_token_here"
}
\`\`\`

---

## Account Management

### 4. Create New Account
**POST** `/api/accounts/create`

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "account_type": "checking",
  "initial_balance": 1000.00
}
\`\`\`

**Response:** `201 Created`
\`\`\`json
{
  "message": "Account created successfully",
  "account": {
    "id": 1,
    "account_number": "ACC1234567890",
    "account_type": "checking",
    "balance": 1000.00,
    "status": "active"
  }
}
\`\`\`

---

### 5. Get User Accounts
**GET** `/api/accounts/my-accounts`

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "accounts": [
    {
      "id": 1,
      "account_number": "ACC1234567890",
      "account_type": "checking",
      "balance": 1000.00,
      "status": "active",
      "recent_transactions": [...]
    }
  ]
}
\`\`\`

---

### 6. Get Account Details
**GET** `/api/accounts/<account_id>`

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "account": {
    "id": 1,
    "account_number": "ACC1234567890",
    "account_type": "checking",
    "balance": 1000.00,
    "status": "active",
    "created_at": "2025-01-10T12:00:00"
  }
}
\`\`\`

---

## Transaction Operations

### 7. Internal Transfer (Between Own Accounts)
**POST** `/api/transactions/internal-transfer`

**Rate Limit:** 20 requests per minute per user

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
Idempotency-Key: unique-key-123 (optional)
\`\`\`

**Request Body:**
\`\`\`json
{
  "from_account_id": 1,
  "to_account_id": 2,
  "amount": 500.00,
  "description": "Savings transfer"
}
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "message": "Transfer completed successfully",
  "transaction": {
    "id": 1,
    "transaction_id": "TXN123456789012",
    "amount": 500.00,
    "from_account": "ACC1234567890",
    "to_account": "ACC0987654321",
    "created_at": "2025-01-10T12:30:00"
  }
}
\`\`\`

---

### 8. External Transfer (To Another User)
**POST** `/api/transactions/external-transfer`

**Rate Limit:** 20 requests per minute per user

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
Idempotency-Key: unique-key-456 (optional)
\`\`\`

**Request Body:**
\`\`\`json
{
  "from_account_id": 1,
  "to_account_number": "ACC5555555555",
  "amount": 250.00,
  "description": "Payment to friend"
}
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "message": "Transfer completed successfully",
  "transaction": {
    "id": 2,
    "transaction_id": "TXN987654321098",
    "amount": 250.00,
    "from_account": "ACC1234567890",
    "to_account": "ACC5555555555",
    "created_at": "2025-01-10T13:00:00"
  }
}
\`\`\`

---

### 9. Get Transaction History
**GET** `/api/transactions/history`

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
\`\`\`

**Query Parameters:**
- `account_id` (optional): Filter by specific account
- `start_date` (optional): ISO 8601 format
- `end_date` (optional): ISO 8601 format
- `transaction_type` (optional): internal_transfer, external_transfer
- `min_amount` (optional): Minimum amount
- `max_amount` (optional): Maximum amount

**Example:**
\`\`\`
GET /api/transactions/history?account_id=1&start_date=2025-01-01&end_date=2025-01-31
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "transactions": [
    {
      "id": 1,
      "transaction_id": "TXN123456789012",
      "sender_account_id": 1,
      "receiver_account_id": 2,
      "amount": 500.00,
      "transaction_type": "internal_transfer",
      "description": "Savings transfer",
      "status": "completed",
      "created_at": "2025-01-10T12:30:00",
      "sender_account_number": "ACC1234567890",
      "receiver_account_number": "ACC0987654321"
    }
  ]
}
\`\`\`

---

## Admin Operations

### 10. Admin First Login (Mandatory Password Change)
**POST** `/api/admin/first-login`

**Headers:**
\`\`\`
Authorization: Bearer <admin_access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "new_email": "admin@secure.com",
  "new_password": "NewSecure@Pass123",
  "new_full_name": "System Admin" (optional)
}
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "message": "Admin credentials updated successfully. Please login again with new credentials.",
  "new_email": "admin@secure.com"
}
\`\`\`

---

### 11. Get All Users (Admin Only)
**GET** `/api/admin/users`

**Headers:**
\`\`\`
Authorization: Bearer <admin_access_token>
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "users": [
    {
      "id": 1,
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone": "+1234567890",
      "role": "customer",
      "created_at": "2025-01-10T10:00:00"
    }
  ]
}
\`\`\`

---

### 12. Create User (Admin Only)
**POST** `/api/admin/users`

**Headers:**
\`\`\`
Authorization: Bearer <admin_access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "full_name": "Jane Support",
  "email": "jane@bank.com",
  "phone": "+1234567891",
  "password": "Support@Pass123",
  "role": "support_agent"
}
\`\`\`

**Valid Roles:** `customer`, `support_agent`, `auditor`, `admin`

**Response:** `201 Created`
\`\`\`json
{
  "message": "User created successfully",
  "user": {
    "id": 2,
    "full_name": "Jane Support",
    "email": "jane@bank.com",
    "role": "support_agent",
    "created_at": "2025-01-10T14:00:00"
  }
}
\`\`\`

---

### 13. Change User Role (Admin Only)
**PATCH** `/api/admin/users/<user_id>/role`

**Headers:**
\`\`\`
Authorization: Bearer <admin_access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "role": "auditor"
}
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "message": "User role updated successfully",
  "old_role": "support_agent",
  "new_role": "auditor"
}
\`\`\`

---

### 14. Change Account Status (Admin Only)
**PUT** `/api/accounts/<account_id>/status`

**Headers:**
\`\`\`
Authorization: Bearer <admin_access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "status": "frozen",
  "reason": "Suspicious activity detected"
}
\`\`\`

**Valid Status:** `active`, `frozen`, `closed`

**Status Transitions:**
- active ↔ frozen (can toggle)
- active → closed (one-way)
- frozen → closed (one-way)
- closed → nothing (permanent)

**Response:** `200 OK`
\`\`\`json
{
  "message": "Account status updated successfully",
  "account_id": 1,
  "old_status": "active",
  "new_status": "frozen"
}
\`\`\`

---

## Support Ticket System

### 15. Create Support Ticket (Customer Only)
**POST** `/api/support/tickets`

**Headers:**
\`\`\`
Authorization: Bearer <customer_access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "subject": "Cannot access my account",
  "description": "I forgot my password and locked out"
}
\`\`\`

**Response:** `201 Created`
\`\`\`json
{
  "message": "Support ticket created successfully",
  "ticket": {
    "id": 1,
    "ticket_number": "TKT12345678",
    "subject": "Cannot access my account",
    "status": "open",
    "created_at": "2025-01-10T15:00:00"
  }
}
\`\`\`

---

### 16. Get Tickets
**GET** `/api/support/tickets`

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
\`\`\`

**Behavior:**
- **Customer:** Sees only their own tickets
- **Support Agent/Admin:** Sees all tickets

**Response:** `200 OK`
\`\`\`json
{
  "tickets": [
    {
      "id": 1,
      "ticket_number": "TKT12345678",
      "subject": "Cannot access my account",
      "description": "I forgot my password and locked out",
      "status": "open",
      "customer": {
        "id": 1,
        "full_name": "John Doe",
        "email": "john@example.com"
      },
      "assigned_to": null,
      "notes": [],
      "created_at": "2025-01-10T15:00:00"
    }
  ]
}
\`\`\`

---

### 17. Update Ticket Status (Support Agent/Admin Only)
**PUT** `/api/support/tickets/<ticket_id>/status`

**Headers:**
\`\`\`
Authorization: Bearer <support_agent_access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "status": "in_progress"
}
\`\`\`

**Valid Status:** `open`, `in_progress`, `resolved`

**Response:** `200 OK`
\`\`\`json
{
  "message": "Ticket status updated successfully",
  "ticket_id": 1,
  "new_status": "in_progress"
}
\`\`\`

---

### 18. Add Ticket Note
**POST** `/api/support/tickets/<ticket_id>/notes`

**Headers:**
\`\`\`
Authorization: Bearer <access_token>
\`\`\`

**Request Body:**
\`\`\`json
{
  "note": "I have reset your password. Please check your email."
}
\`\`\`

**Response:** `201 Created`
\`\`\`json
{
  "message": "Note added successfully",
  "note": {
    "id": 1,
    "note": "I have reset your password. Please check your email.",
    "created_at": "2025-01-10T15:30:00"
  }
}
\`\`\`

---

## Audit & Security Logs

### 19. Search Audit Logs (Auditor/Admin Only)
**GET** `/api/audit/search`

**Headers:**
\`\`\`
Authorization: Bearer <auditor_or_admin_access_token>
\`\`\`

**Query Parameters:**
- `user_id` (optional): Filter by user
- `action` (optional): Specific action type
- `severity` (optional): info, warning, critical
- `start_date` (optional): ISO 8601 format
- `end_date` (optional): ISO 8601 format
- `limit` (optional): Default 100
- `offset` (optional): For pagination

**Example:**
\`\`\`
GET /api/audit/search?severity=warning&limit=50
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "logs": [
    {
      "id": 1,
      "user_id": 1,
      "user_email": "john@example.com",
      "user_name": "John Doe",
      "action": "SUSPICIOUS_TRANSACTION",
      "resource_type": "transaction",
      "resource_id": 5,
      "ip_address": "192.168.1.100",
      "details": "Large amount transfer: $15,000",
      "severity": "warning",
      "created_at": "2025-01-10T16:00:00",
      "log_hash": "a1b2c3..."
    }
  ],
  "total": 150,
  "limit": 50,
  "offset": 0
}
\`\`\`

---

### 20. Get Suspicious Activities (Auditor/Admin Only)
**GET** `/api/audit/suspicious`

**Headers:**
\`\`\`
Authorization: Bearer <auditor_or_admin_access_token>
\`\`\`

**Response:** `200 OK`
\`\`\`json
{
  "suspicious_activities": [
    {
      "id": 1,
      "user_id": 1,
      "user_email": "john@example.com",
      "user_name": "John Doe",
      "action": "SUSPICIOUS_TRANSACTION",
      "details": "Large amount: $15,000, 5 transfers in 5 minutes",
      "severity": "warning",
      "created_at": "2025-01-10T16:00:00"
    },
    {
      "id": 2,
      "user_id": 2,
      "user_email": "jane@example.com",
      "user_name": "Jane Doe",
      "action": "LOGIN_RATE_LIMIT_EXCEEDED",
      "details": "10 failed login attempts",
      "severity": "warning",
      "created_at": "2025-01-10T16:15:00"
    }
  ]
}
\`\`\`

---

## Error Responses

### Standard Error Format
\`\`\`json
{
  "error": "Description of the error"
}
\`\`\`

### Common HTTP Status Codes
- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid input or missing required fields
- `401 Unauthorized` - Missing or invalid authentication token
- `403 Forbidden` - Valid authentication but insufficient permissions
- `404 Not Found` - Resource does not exist
- `409 Conflict` - Resource already exists (e.g., duplicate email)
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server-side error
- `503 Service Unavailable` - Microservice is down
- `504 Gateway Timeout` - Microservice didn't respond in time

---

## Rate Limits Summary

| Endpoint | Rate Limit | Window |
|----------|------------|--------|
| `/api/auth/login` | 5 requests | 15 minutes per IP+email |
| `/api/transactions/*` | 20 requests | 1 minute per user |
| `/api/accounts/*` | 50 requests | 1 minute per user |
| `/api/auth/*` (other) | 20 requests | 1 minute per IP |

---

## Security Headers Required

All authenticated requests must include:
\`\`\`
Authorization: Bearer <access_token>
Content-Type: application/json
\`\`\`

Optional headers:
\`\`\`
Idempotency-Key: <unique-key> (for transaction endpoints)
\`\`\`

---

## JWT Token Structure

**Access Token Payload:**
\`\`\`json
{
  "user_id": 1,
  "email": "john@example.com",
  "role": "customer",
  "exp": 1704988800
}
\`\`\`

**Token Expiration:**
- Access Token: 15 minutes (900 seconds)
- Refresh Token: 7 days (604800 seconds)

---

## Idempotency Keys

For transaction endpoints, you can provide an `Idempotency-Key` header to prevent duplicate transactions:

\`\`\`bash
curl -X POST http://localhost:5000/api/transactions/external-transfer \
  -H "Authorization: Bearer <token>" \
  -H "Idempotency-Key: unique-operation-id-123" \
  -H "Content-Type: application/json" \
  -d '{"from_account_id": 1, "to_account_number": "ACC002", "amount": 500}'
\`\`\`

If the same key is used within 24 hours, the cached result will be returned instead of processing a new transaction.
