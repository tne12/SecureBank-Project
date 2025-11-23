# **README for Secure Banking System Project**

---

## **Project Overview**

This project is a **Secure Banking System** designed to provide various banking features, including user authentication, role-based access control (RBAC), account management, transactions, audit logs, and support ticket management. The goal is to build a highly secure, scalable, and modular banking system capable of handling typical banking operations while ensuring top-tier security to prevent common vulnerabilities such as SQL injection, XSS, broken access control, and more.

The system is divided into **multiple services** that work in tandem:

* **RBAC & Authentication Service**: Handles user authentication, JWT issuance, RBAC permissions, and password management.
* **Transaction Service**: Manages accounts, transactions, balance management, and associated database operations.
* **Web App Service**: Provides the frontend interface, supports the admin panel, manages audit logs, and serves static files.

---

## **Technologies & Tools Used**

* **Flask**: Python web framework for backend services.
* **SQLite**: Lightweight database for storing user data, accounts, transactions, and audit logs.
* **Redis**: Used for rate limiting and idempotency keys to prevent duplicate requests.
* **JWT**: JSON Web Tokens for secure user authentication.
* **bcrypt**: Password hashing library to ensure secure password storage.
* **CORS**: Cross-origin resource sharing, enabling the backend to be accessed by the frontend.
* **Requests**: HTTP library for external communication between services (audit logs, token validation, etc.).
* **HTML, CSS, JavaScript**: Frontend technologies used for building the UI (with enhanced security measures like escaping user input).
* **Bootstrap / Tailwind**: Used for frontend design and responsive layouts.
* **SHA-256**: Hashing used for ensuring the integrity of audit logs.
* **Idempotency Key**: Mechanism to avoid duplicate transactions.

---

## **Key Features Implemented**

### **1. Authentication & Authorization**

* **User Registration**: Secure user sign-up with email, phone number, and strong password validation.
* **Login**: JWT-based authentication with login rate-limiting and user role-based access control.
* **Password Management**: Users can change their passwords with validation for strength and format.
* **RBAC**: The system implements role-based access control (RBAC), where users are assigned specific roles (`customer`, `support_agent`, `auditor`, `admin`), and each role has a defined set of permissions.

### **2. Account Management**

* **Account Creation**: Customers and admins can create new accounts (checking, savings) with opening balances.
* **Account Access**: Users can access and view their own accounts, while support agents and admins have access to all accounts.
* **Account Status**: Admins can freeze, unfreeze, or close accounts.

### **3. Transactions**

* **Internal Transfers**: Users can transfer funds between their own accounts.
* **External Transfers**: Users can transfer funds to another user's account, subject to validation checks.
* **Suspicious Transaction Detection**: Rapid or high-value transactions are flagged as suspicious for further review.

### **4. Audit Logs**

* **Audit Log Creation**: Every significant action (e.g., login, role change, account creation) is logged for security and tracking.
* **Log Hashing**: SHA-256 hashing is applied to ensure the integrity of audit logs, preventing tampering.

### **5. Support Tickets**

* **Ticket Creation**: Customers can open support tickets with a subject and description.
* **Ticket Management**: Support agents and admins can view, update, and close tickets.
* **Ticket Notes**: Support agents can add internal notes to tickets for communication and tracking.

### **6. Security Measures**

* **SQL Injection Protection**: All queries are parameterized to prevent SQL injection.
* **XSS Prevention**: User inputs are sanitized and escaped before being inserted into the DOM to prevent cross-site scripting (XSS) attacks.
* **Rate Limiting**: Users are limited to a certain number of login attempts to prevent brute-force attacks.
* **Idempotency**: Idempotency keys are used to prevent duplicate transactions from being processed.
* **Password Security**: Passwords are hashed using bcrypt and must meet strong criteria (length, case, digit, special character).
* **RBAC**: Role-based access control ensures that users only have access to the resources and actions permitted for their role.

---

## **Service Running URLs & Setup**

### **Service URLs**

* **RBAC Authentication Service**: `http://localhost:5001`
* **Transaction Service**: `http://localhost:5002`
* **Web App Service**: `http://localhost:5003`

### **How to Run the Application**

#### **Step 1: Clone the Repository**

Clone the project repository to your local machine:

```bash
git clone https://github.com/your-repository/banking-system.git
cd banking-system
```

#### **Step 2: Set up the Environment**

1. **Create a Virtual Environment**:

   ```bash
   python3 -m venv venv
   source venv/bin/activate  # For Linux/MacOS
   venv\Scripts\activate  # For Windows
   ```

2. **Install Dependencies**:

   Install the required dependencies for all services:

   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Variables**:

   Set up the following environment variables:

   * `SECRET_KEY`: A secure secret key for JWT token signing.
   * `REDIS_HOST`: The hostname for Redis (default: `localhost`).
   * `REDIS_PORT`: The port number for Redis (default: `6379`).
   * `AUDIT_LOG_URL`: URL to send audit logs (default: `http://localhost:5003/api/audit/log`).
   * `RBAC_AUTH_URL`: URL for the RBAC authentication service (default: `http://localhost:5001`).

   Example for `.env` file:

   ```
   SECRET_KEY=your-secret-key
   REDIS_HOST=localhost
   REDIS_PORT=6379
   AUDIT_LOG_URL=http://localhost:5003/api/audit/log
   RBAC_AUTH_URL=http://localhost:5001
   ```

#### **Step 3: Database Setup**

1. **Create the SQLite Database**:

   The project uses SQLite to store user data, accounts, transactions, and audit logs. To set up the database, run the following command:

   ```bash
   python setup_db.py
   ```

2. **Populate Initial Data (Optional)**:

   You can pre-populate the database with sample data by running:

   ```bash
   python seed_db.py
   ```

#### **Step 4: Start the Services**

1. **RBAC Authentication Service**:

   * Start the **RBAC Authentication Service**:

     ```bash
     python rbac_auth_service.py
     ```

2. **Transaction Service**:

   * Start the **Transaction Service**:

     ```bash
     python transaction_service.py
     ```

3. **Web App Service**:

   * Start the **Web App Service**:

     ```bash
     python web_app_service.py
     ```

---

## **File Descriptions**

### **1. `rbac_auth_service.py`**

This file contains the **authentication logic** for the banking system. It handles:

* User registration and login using JWT.
* Password validation and hashing using bcrypt.
* Role-based access control (RBAC) for different roles (`customer`, `support_agent`, `auditor`, `admin`).
* Rate-limiting to prevent brute-force attacks.
* Audit logging for user actions like registration, login, and password changes.

### **2. `transaction_service.py`**

This file manages the **banking transactions**. It includes:

* Account creation and management.
* Internal and external fund transfers.
* Transaction validation, including checks for suspicious activity.
* Use of idempotency keys to prevent duplicate transactions.
* Audit logging for transactions.
* Suspicious transaction detection based on rapid transfer patterns or large amounts.

### **3. `web_app.py`**

This file serves as the **web app backend**. It includes:

* Admin panel for managing users and tickets.
* Support ticket creation, management, and notes.
* Viewing and managing audit logs.
* Profile management and role updates for users.

---

## **Security Measures & Mitigation**

### **1. SQL Injection Prevention**

* **What we did**: All SQL queries are parameterized, preventing SQL injection. For example, user input is passed as query parameters (e.g., `cursor.execute("SELECT id FROM users WHERE email = ?", (email,))`).
* **Why it works**: This ensures that user input is treated strictly as data, not executable code.

### **2. Cross-Site Scripting (XSS)**

* **What we did**: User inputs that are rendered into HTML are sanitized and escaped using `escapeHtml()` before being inserted into the DOM.
* **Why it works**: This prevents malicious scripts from being executed in the browser.

### **3. Cross-Site Request Forgery (CSRF)**

* **What we did**: We use **JWT tokens** for authentication rather than cookies, which prevents CSRF attacks.
* **Why it works**: Since JWT tokens are passed in the `Authorization` header, they are not vulnerable to CSRF, unlike cookies.

### **4. Broken Access Control**

* **What we did**: Role-based access control (RBAC) is implemented, and each role (e.g., `customer`, `support_agent`, `auditor`, `admin`) has a defined set of permissions. We ensure that users can only perform actions that align with their role.
* **Why it works**: This ensures that sensitive actions (e.g., account modification, transferring funds) are only accessible to authorized users.

### **5. Rate Limiting**

* **What we did**: We implemented **rate limiting** for login attempts to prevent brute-force attacks.
* **Why it works**: This restricts the number of attempts a user can make within a certain time period, reducing the risk of password cracking.

### **6. Password Security**

* **What we did**: Passwords are hashed using **bcrypt** with a strong validation policy (length, upper/lowercase, digits, and special characters).
* **Why it works**: bcrypt ensures that passwords are stored securely, and the validation policy ensures that users choose strong passwords.

---

## **Requirements Achieved**

1. **RBAC Implementation**: Fully implemented and enforced across all routes.
2. **Authentication & Authorization**: Secure JWT-based login, registration, and password management.
3. **Transaction Security**: Suspicious transaction detection and idempotency to prevent duplicates.
4. **Audit Logs**: Comprehensive logging of critical actions, with log integrity ensured via SHA-256 hashing.
5. **Security Best Practices**: SQL injection prevention, XSS protection, password hashing, and rate limiting.

---

## **How to Contribute**

If you'd like to contribute to this project:

1. Fork the repository.
2. Create a new branch.
3. Implement your changes.
4. Submit a pull request.

---

This **README** provides a comprehensive overview of the **Secure Banking System**. It outlines the core features, security measures, and how to set up the system locally. Ensure that the application is always run over **HTTPS** in a production environment, and monitor for security vulnerabilities regularly.
