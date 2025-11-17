// API Base URLs (updated for SQLite setup)
const API_AUTH = "http://localhost:5001/api/auth"
const API_ACCOUNTS = "http://localhost:5002/api/accounts"
const API_TRANSACTIONS = "http://localhost:5002/api/transactions"
const API_ADMIN = "http://localhost:5003/api/admin"
const API_SUPPORT = "http://localhost:5003/api/support"


// Global state
let currentUser = null
let authToken = null

// Utility functions
function showError(elementId, message) {
  const element = document.getElementById(elementId)
  element.textContent = message
  element.classList.remove("hidden")
  setTimeout(() => element.classList.add("hidden"), 5000)
}

function showSuccess(message) {
  // Simple toast notification
  const toast = document.createElement("div")
  toast.className = "fixed top-4 right-4 bg-primary text-primary-foreground px-6 py-3 rounded-lg shadow-lg z-50"
  toast.textContent = message
  document.body.appendChild(toast)
  setTimeout(() => toast.remove(), 3000)
}

async function apiCall(url, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...options.headers,
  }

  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`
  }

  const response = await fetch(url, {
    ...options,
    headers,
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.error || "An error occurred")
  }

  return data
}

// Auth tab switching
document.getElementById("login-tab").addEventListener("click", () => {
  document.getElementById("login-tab").classList.add("active")
  document.getElementById("register-tab").classList.remove("active")
  document.getElementById("login-form").classList.remove("hidden")
  document.getElementById("register-form").classList.add("hidden")
})

document.getElementById("register-tab").addEventListener("click", () => {
  document.getElementById("register-tab").classList.add("active")
  document.getElementById("login-tab").classList.remove("active")
  document.getElementById("register-form").classList.remove("hidden")
  document.getElementById("login-form").classList.add("hidden")
})

// Login
document.getElementById("login-form-element").addEventListener("submit", async (e) => {
  e.preventDefault()
  const formData = new FormData(e.target)
  const data = Object.fromEntries(formData)

  try {
    const response = await apiCall(`${API_AUTH}/login`, {
      method: "POST",
      body: JSON.stringify(data),
    })

    authToken = response.token
    currentUser = response.user
    localStorage.setItem("authToken", authToken)
    localStorage.setItem("currentUser", JSON.stringify(currentUser))

    // Check if first login
    if (currentUser.is_first_login) {
      showChangePasswordModal()
    } else {
      showDashboard()
    }
  } catch (error) {
    showError("login-error", error.message)
  }
})

// Register
document.getElementById("register-form-element").addEventListener("submit", async (e) => {
  e.preventDefault()
  const formData = new FormData(e.target)
  const data = Object.fromEntries(formData)

  try {
    await apiCall(`${API_AUTH}/register`, {
      method: "POST",
      body: JSON.stringify(data),
    })

    showSuccess("Registration successful! Please log in.")
    document.getElementById("login-tab").click()
    e.target.reset()
  } catch (error) {
    showError("register-error", error.message)
  }
})

// Change Password Modal
function showChangePasswordModal() {
  document.getElementById("change-password-modal").classList.remove("hidden")
}

document.getElementById("change-password-form").addEventListener("submit", async (e) => {
  e.preventDefault()
  const formData = new FormData(e.target)
  const data = Object.fromEntries(formData)

  try {
    await apiCall(`${API_AUTH}/change-password`, {
      method: "POST",
      body: JSON.stringify(data),
    })

    currentUser.is_first_login = false
    localStorage.setItem("currentUser", JSON.stringify(currentUser))

    document.getElementById("change-password-modal").classList.add("hidden")
    showSuccess("Password changed successfully!")
    showDashboard()
  } catch (error) {
    showError("change-password-error", error.message)
  }
})

// Show Dashboard
function showDashboard() {
  document.getElementById("auth-screen").classList.add("hidden")
  document.getElementById("dashboard-screen").classList.remove("hidden")

  // Set user info
  document.getElementById("user-name").textContent = currentUser.full_name
  document.getElementById("user-role").textContent = currentUser.role.replace("_", " ").toUpperCase()

  // Show/hide navigation based on role
  updateNavigationVisibility()

  // Load default view
  loadView("dashboard")
}

function updateNavigationVisibility() {
  const role = currentUser.role

  // Hide all role-specific buttons first
  document.querySelectorAll(".nav-btn").forEach((btn) => {
    btn.classList.add("hidden")
  })

  // Show dashboard for all
  document.querySelector('[data-view="dashboard"]').classList.remove("hidden")

  // Show based on role
  if (role === "customer") {
    document.querySelectorAll(".customer-only").forEach((el) => el.classList.remove("hidden"))
  } else if (role === "support_agent") {
    document.querySelectorAll(".support-only").forEach((el) => el.classList.remove("hidden"))
  } else if (role === "auditor") {
    document.querySelectorAll(".auditor-only").forEach((el) => el.classList.remove("hidden"))
  } else if (role === "admin") {
    document.querySelectorAll(".admin-only").forEach((el) => el.classList.remove("hidden"))
    document.querySelectorAll(".customer-only").forEach((el) => el.classList.remove("hidden"))
  }
}

// Navigation
document.querySelectorAll(".nav-btn").forEach((btn) => {
  btn.addEventListener("click", (e) => {
    document.querySelectorAll(".nav-btn").forEach((b) => b.classList.remove("active"))
    e.target.classList.add("active")
    loadView(e.target.dataset.view)
  })
})

// Logout
document.getElementById("logout-btn").addEventListener("click", () => {
  authToken = null
  currentUser = null
  localStorage.removeItem("authToken")
  localStorage.removeItem("currentUser")

  document.getElementById("dashboard-screen").classList.add("hidden")
  document.getElementById("auth-screen").classList.remove("hidden")
  showSuccess("Logged out successfully")
})

// Load Views
async function loadView(viewName) {
  const container = document.getElementById("view-container")

  switch (viewName) {
    case "dashboard":
      await loadDashboardView(container)
      break
    case "accounts":
      await loadAccountsView(container)
      break
    case "transfer":
      await loadTransferView(container)
      break
    case "support":
      await loadSupportView(container)
      break
    case "admin-users":
      await loadAdminUsersView(container)
      break
    case "admin-accounts":
      await loadAdminAccountsView(container)
      break
    case "audit":
      await loadAuditView(container)
      break
  }
}

// Dashboard View
async function loadDashboardView(container) {
  try {
    const accountsData = await apiCall(`${API_ACCOUNTS}/my-accounts`)
    const accounts = accountsData.accounts

    const totalBalance = accounts.reduce((sum, acc) => sum + acc.balance, 0)

    container.innerHTML = `
            <div class="space-y-6">
                <div>
                    <h2 class="text-3xl font-bold text-balance mb-2">Welcome back, ${currentUser.full_name}</h2>
                    <p class="text-muted-foreground">Here's your account overview</p>
                </div>
                
                <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div class="bg-card border border-border rounded-xl p-6">
                        <div class="text-sm text-muted-foreground mb-2">Total Balance</div>
                        <div class="text-3xl font-bold text-primary">$${totalBalance.toFixed(2)}</div>
                    </div>
                    <div class="bg-card border border-border rounded-xl p-6">
                        <div class="text-sm text-muted-foreground mb-2">Active Accounts</div>
                        <div class="text-3xl font-bold">${accounts.filter((a) => a.status === "active").length}</div>
                    </div>
                    <div class="bg-card border border-border rounded-xl p-6">
                        <div class="text-sm text-muted-foreground mb-2">Recent Transactions</div>
                        <div class="text-3xl font-bold">${accounts.reduce((sum, a) => sum + a.recent_transactions.length, 0)}</div>
                    </div>
                </div>
                
                <div>
                    <h3 class="text-xl font-semibold mb-4">Your Accounts</h3>
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                        ${accounts
                          .map(
                            (account) => `
                            <div class="account-card rounded-xl p-6">
                                <div class="flex justify-between items-start mb-4">
                                    <div>
                                        <div class="text-sm text-muted-foreground mb-1">${account.account_type.toUpperCase()}</div>
                                        <div class="font-mono text-lg">${account.account_number}</div>
                                    </div>
                                    <span class="status-badge status-${account.status}">${account.status}</span>
                                </div>
                                <div class="text-2xl font-bold mb-4">$${account.balance.toFixed(2)}</div>
                                <div class="border-t border-border pt-4">
                                    <div class="text-sm text-muted-foreground mb-2">Recent Transactions</div>
                                    ${
                                      account.recent_transactions.length > 0
                                        ? `
                                        <div class="space-y-2">
                                            ${account.recent_transactions
                                              .slice(0, 3)
                                              .map(
                                                (t) => `
                                                <div class="flex justify-between text-sm">
                                                    <span>${t.description || t.type}</span>
                                                    <span class="${t.receiver_account_id === account.id ? "text-primary" : "text-muted-foreground"}">
                                                        ${t.receiver_account_id === account.id ? "+" : "-"}$${t.amount.toFixed(2)}
                                                    </span>
                                                </div>
                                            `,
                                              )
                                              .join("")}
                                        </div>
                                    `
                                        : '<div class="text-sm text-muted-foreground">No transactions yet</div>'
                                    }
                                </div>
                            </div>
                        `,
                          )
                          .join("")}
                    </div>
                </div>
            </div>
        `
  } catch (error) {
    container.innerHTML = `<div class="text-destructive">Error loading dashboard: ${error.message}</div>`
  }
}

// Accounts View
async function loadAccountsView(container) {
  try {
    const accountsData = await apiCall(`${API_ACCOUNTS}/my-accounts`)
    const accounts = accountsData.accounts

    container.innerHTML = `
            <div class="space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">My Accounts</h2>
                    <button onclick="showCreateAccountModal()" class="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90">
                        <i class="fas fa-plus mr-2"></i>Create Account
                    </button>
                </div>
                
                <div class="grid grid-cols-1 gap-4">
                    ${accounts
                      .map(
                        (account) => `
                        <div class="bg-card border border-border rounded-xl p-6">
                            <div class="flex justify-between items-start mb-4">
                                <div>
                                    <div class="text-sm text-muted-foreground mb-1">${account.account_type.toUpperCase()} ACCOUNT</div>
                                    <div class="font-mono text-xl">${account.account_number}</div>
                                </div>
                                <span class="status-badge status-${account.status}">${account.status}</span>
                            </div>
                            <div class="text-3xl font-bold mb-6">$${account.balance.toFixed(2)}</div>
                            <div class="border-t border-border pt-4">
                                <div class="text-sm font-medium mb-3">Recent Transactions</div>
                                ${
                                  account.recent_transactions.length > 0
                                    ? `
                                    <div class="space-y-2">
                                        ${account.recent_transactions
                                          .map(
                                            (t) => `
                                            <div class="flex justify-between items-center py-2 border-b border-border last:border-0">
                                                <div>
                                                    <div class="text-sm font-medium">${t.description || t.type}</div>
                                                    <div class="text-xs text-muted-foreground">${new Date(t.created_at).toLocaleDateString()}</div>
                                                </div>
                                                <div class="text-sm font-medium ${t.receiver_account_id === account.id ? "text-primary" : "text-muted-foreground"}">
                                                    ${t.receiver_account_id === account.id ? "+" : "-"}$${t.amount.toFixed(2)}
                                                </div>
                                            </div>
                                        `,
                                          )
                                          .join("")}
                                    </div>
                                `
                                    : '<div class="text-sm text-muted-foreground">No transactions yet</div>'
                                }
                            </div>
                        </div>
                    `,
                      )
                      .join("")}
                </div>
            </div>
        `
  } catch (error) {
    container.innerHTML = `<div class="text-destructive">Error loading accounts: ${error.message}</div>`
  }
}

// Create Account Modal
window.showCreateAccountModal = () => {
  const modal = document.createElement("div")
  modal.className = "fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4"
  modal.innerHTML = `
        <div class="bg-card rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <h3 class="text-2xl font-bold mb-6">Create New Account</h3>
            <form id="create-account-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-2">Account Type</label>
                    <select name="account_type" required class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                        <option value="checking">Checking</option>
                        <option value="savings">Savings</option>
                    </select>
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Opening Balance</label>
                    <input type="number" name="opening_balance" step="0.01" min="0" value="0" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                </div>
                <div class="flex gap-3">
                    <button type="submit" class="flex-1 bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90">
                        Create Account
                    </button>
                    <button type="button" onclick="this.closest('.fixed').remove()" class="flex-1 bg-secondary text-secondary-foreground py-2 rounded-lg hover:opacity-90">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    `
  document.body.appendChild(modal)

  document.getElementById("create-account-form").addEventListener("submit", async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const data = Object.fromEntries(formData)

    try {
      await apiCall(`${API_ACCOUNTS}/create`, {
        method: "POST",
        body: JSON.stringify(data),
      })

      modal.remove()
      showSuccess("Account created successfully!")
      loadView("accounts")
    } catch (error) {
      showError("create-account-error", error.message)
    }
  })
}

// Transfer View
async function loadTransferView(container) {
  try {
    const accountsData = await apiCall(`${API_ACCOUNTS}/my-accounts`)
    const accounts = accountsData.accounts.filter((a) => a.status === "active")

    container.innerHTML = `
            <div class="space-y-6">
                <h2 class="text-2xl font-bold">Transfer Money</h2>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- Internal Transfer -->
                    <div class="bg-card border border-border rounded-xl p-6">
                        <h3 class="text-xl font-semibold mb-4">
                            <i class="fas fa-exchange-alt mr-2 text-primary"></i>Internal Transfer
                        </h3>
                        <p class="text-sm text-muted-foreground mb-6">Transfer between your own accounts</p>
                        <form id="internal-transfer-form" class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium mb-2">From Account</label>
                                <select name="from_account_id" required class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                                    ${accounts.map((a) => `<option value="${a.id}">${a.account_number} ($${a.balance.toFixed(2)})</option>`).join("")}
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-2">To Account</label>
                                <select name="to_account_id" required class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                                    ${accounts.map((a) => `<option value="${a.id}">${a.account_number} ($${a.balance.toFixed(2)})</option>`).join("")}
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-2">Amount</label>
                                <input type="number" name="amount" step="0.01" min="0.01" required
                                    class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-2">Description (Optional)</label>
                                <input type="text" name="description"
                                    class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                            </div>
                            <button type="submit" class="w-full bg-primary text-primary-foreground py-3 rounded-lg hover:opacity-90">
                                Transfer
                            </button>
                        </form>
                    </div>
                    
                    <!-- External Transfer -->
                    <div class="bg-card border border-border rounded-xl p-6">
                        <h3 class="text-xl font-semibold mb-4">
                            <i class="fas fa-paper-plane mr-2 text-primary"></i>External Transfer
                        </h3>
                        <p class="text-sm text-muted-foreground mb-6">Send money to another user's account</p>
                        <form id="external-transfer-form" class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium mb-2">From Account</label>
                                <select name="from_account_id" required class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                                    ${accounts.map((a) => `<option value="${a.id}">${a.account_number} ($${a.balance.toFixed(2)})</option>`).join("")}
                                </select>
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-2">To Account Number</label>
                                <input type="text" name="to_account_number" required
                                    class="w-full px-4 py-2 bg-background border border-input rounded-lg font-mono">
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-2">Amount</label>
                                <input type="number" name="amount" step="0.01" min="0.01" required
                                    class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                            </div>
                            <div>
                                <label class="block text-sm font-medium mb-2">Description (Optional)</label>
                                <input type="text" name="description"
                                    class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                            </div>
                            <button type="submit" class="w-full bg-primary text-primary-foreground py-3 rounded-lg hover:opacity-90">
                                Send Money
                            </button>
                        </form>
                    </div>
                </div>
            </div>
        `

    // Internal transfer handler
    document.getElementById("internal-transfer-form").addEventListener("submit", async (e) => {
      e.preventDefault()
      const formData = new FormData(e.target)
      const data = Object.fromEntries(formData)

      try {
        await apiCall(`${API_TRANSACTIONS}/internal-transfer`, {
          method: "POST",
          body: JSON.stringify(data),
        })

        showSuccess("Transfer completed successfully!")
        e.target.reset()
        loadView("dashboard")
      } catch (error) {
        alert(error.message)
      }
    })

    // External transfer handler
    document.getElementById("external-transfer-form").addEventListener("submit", async (e) => {
      e.preventDefault()
      const formData = new FormData(e.target)
      const data = Object.fromEntries(formData)

      try {
        await apiCall(`${API_TRANSACTIONS}/external-transfer`, {
          method: "POST",
          body: JSON.stringify(data),
        })

        showSuccess("Transfer completed successfully!")
        e.target.reset()
        loadView("dashboard")
      } catch (error) {
        alert(error.message)
      }
    })
  } catch (error) {
    container.innerHTML = `<div class="text-destructive">Error loading transfer: ${error.message}</div>`
  }
}

// Support View
async function loadSupportView(container) {
  try {
    const ticketsData = await apiCall(`${API_SUPPORT}/tickets`)
    const tickets = ticketsData.tickets

    const isSupport = currentUser.role === "support_agent" || currentUser.role === "admin"

    container.innerHTML = `
            <div class="space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">Support Tickets</h2>
                    ${
                      !isSupport
                        ? `
                        <button onclick="showCreateTicketModal()" class="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90">
                            <i class="fas fa-plus mr-2"></i>New Ticket
                        </button>
                    `
                        : ""
                    }
                </div>
                
                <div class="space-y-4">
                    ${
                      tickets.length > 0
                        ? tickets
                            .map(
                              (ticket) => `
                        <div class="bg-card border border-border rounded-xl p-6">
                            <div class="flex justify-between items-start mb-4">
                                <div>
                                    <div class="text-sm text-muted-foreground mb-1">Ticket #${ticket.ticket_number}</div>
                                    <h3 class="text-lg font-semibold">${ticket.subject}</h3>
                                    ${isSupport ? `<div class="text-sm text-muted-foreground mt-1">Customer: ${ticket.customer.full_name} (${ticket.customer.email})</div>` : ""}
                                </div>
                                <span class="status-badge status-${ticket.status}">${ticket.status.replace("_", " ")}</span>
                            </div>
                            <p class="text-sm text-muted-foreground mb-4">${ticket.description}</p>
                            
                            ${
                              ticket.notes.length > 0
                                ? `
                                <div class="border-t border-border pt-4 mb-4">
                                    <div class="text-sm font-medium mb-2">Notes</div>
                                    <div class="space-y-2">
                                        ${ticket.notes
                                          .map(
                                            (note) => `
                                            <div class="bg-background rounded-lg p-3">
                                                <div class="flex justify-between text-xs text-muted-foreground mb-1">
                                                    <span>${note.author} (${note.author_role})</span>
                                                    <span>${new Date(note.created_at).toLocaleString()}</span>
                                                </div>
                                                <div class="text-sm">${note.note}</div>
                                            </div>
                                        `,
                                          )
                                          .join("")}
                                    </div>
                                </div>
                            `
                                : ""
                            }
                            
                            <div class="flex gap-3">
                                <button onclick="showAddNoteModal(${ticket.id})" class="flex-1 bg-secondary text-secondary-foreground px-4 py-2 rounded-lg hover:opacity-90">
                                    Add Note
                                </button>
                                ${
                                  isSupport
                                    ? `
                                    <select onchange="updateTicketStatus(${ticket.id}, this.value)" class="flex-1 px-4 py-2 bg-background border border-input rounded-lg">
                                        <option value="">Change Status...</option>
                                        <option value="open">Open</option>
                                        <option value="in_progress">In Progress</option>
                                        <option value="resolved">Resolved</option>
                                    </select>
                                `
                                    : ""
                                }
                            </div>
                        </div>
                    `,
                            )
                            .join("")
                        : '<div class="text-center text-muted-foreground py-8">No tickets found</div>'
                    }
                </div>
            </div>
        `
  } catch (error) {
    container.innerHTML = `<div class="text-destructive">Error loading support tickets: ${error.message}</div>`
  }
}

// Create Ticket Modal
window.showCreateTicketModal = () => {
  const modal = document.createElement("div")
  modal.className = "fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4"
  modal.innerHTML = `
        <div class="bg-card rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <h3 class="text-2xl font-bold mb-6">Create Support Ticket</h3>
            <form id="create-ticket-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-2">Subject</label>
                    <input type="text" name="subject" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Description</label>
                    <textarea name="description" rows="4" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg"></textarea>
                </div>
                <div class="flex gap-3">
                    <button type="submit" class="flex-1 bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90">
                        Create Ticket
                    </button>
                    <button type="button" onclick="this.closest('.fixed').remove()" class="flex-1 bg-secondary text-secondary-foreground py-2 rounded-lg hover:opacity-90">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    `
  document.body.appendChild(modal)

  document.getElementById("create-ticket-form").addEventListener("submit", async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const data = Object.fromEntries(formData)

    try {
      await apiCall(`${API_SUPPORT}/tickets`, {
        method: "POST",
        body: JSON.stringify(data),
      })

      modal.remove()
      showSuccess("Ticket created successfully!")
      loadView("support")
    } catch (error) {
      alert(error.message)
    }
  })
}

// Add Note Modal
window.showAddNoteModal = (ticketId) => {
  const modal = document.createElement("div")
  modal.className = "fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4"
  modal.innerHTML = `
        <div class="bg-card rounded-2xl p-8 max-w-md w-full shadow-2xl">
            <h3 class="text-2xl font-bold mb-6">Add Note</h3>
            <form id="add-note-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-2">Note</label>
                    <textarea name="note" rows="4" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg"></textarea>
                </div>
                <div class="flex gap-3">
                    <button type="submit" class="flex-1 bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90">
                        Add Note
                    </button>
                    <button type="button" onclick="this.closest('.fixed').remove()" class="flex-1 bg-secondary text-secondary-foreground py-2 rounded-lg hover:opacity-90">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    `
  document.body.appendChild(modal)

  document.getElementById("add-note-form").addEventListener("submit", async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const data = Object.fromEntries(formData)

    try {
      await apiCall(`${API_SUPPORT}/tickets/${ticketId}/notes`, {
        method: "POST",
        body: JSON.stringify(data),
      })

      modal.remove()
      showSuccess("Note added successfully!")
      loadView("support")
    } catch (error) {
      alert(error.message)
    }
  })
}

// Update Ticket Status
window.updateTicketStatus = async (ticketId, status) => {
  if (!status) return

  try {
    await apiCall(`${API_SUPPORT}/tickets/${ticketId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    })

    showSuccess("Ticket status updated!")
    loadView("support")
  } catch (error) {
    alert(error.message)
  }
}

// Admin Users View
async function loadAdminUsersView(container) {
  try {
    const usersData = await apiCall(`${API_ADMIN}/users`)
    const users = usersData.users

    container.innerHTML = `
            <div class="space-y-6">
                <div class="flex justify-between items-center">
                    <h2 class="text-2xl font-bold">User Management</h2>
                    <button onclick="showCreateUserModal()" class="bg-primary text-primary-foreground px-4 py-2 rounded-lg hover:opacity-90">
                        <i class="fas fa-user-plus mr-2"></i>Create User
                    </button>
                </div>
                
                <div class="bg-card border border-border rounded-xl overflow-hidden">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Role</th>
                                <th>Created</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${users
                              .map(
                                (user) => `
                                <tr>
                                    <td>${user.full_name}</td>
                                    <td>${user.email}</td>
                                    <td>${user.phone}</td>
                                    <td><span class="status-badge status-active">${user.role.replace("_", " ")}</span></td>
                                    <td>${new Date(user.created_at).toLocaleDateString()}</td>
                                    <td>
                                        <button onclick="showEditUserModal(${user.id})" class="text-primary hover:underline mr-3">
                                            <i class="fas fa-edit"></i>
                                        </button>
                                        ${
                                          user.id !== currentUser.user_id
                                            ? `
                                            <button onclick="deleteUser(${user.id})" class="text-destructive hover:underline">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        `
                                            : ""
                                        }
                                    </td>
                                </tr>
                            `,
                              )
                              .join("")}
                        </tbody>
                    </table>
                </div>
            </div>
        `
  } catch (error) {
    container.innerHTML = `<div class="text-destructive">Error loading users: ${error.message}</div>`
  }
}

// Create User Modal (Admin)
window.showCreateUserModal = () => {
  const modal = document.createElement("div")
  modal.className = "fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4"
  modal.innerHTML = `
        <div class="bg-card rounded-2xl p-8 max-w-md w-full shadow-2xl max-h-[90vh] overflow-y-auto">
            <h3 class="text-2xl font-bold mb-6">Create New User</h3>
            <form id="admin-create-user-form" class="space-y-4">
                <div>
                    <label class="block text-sm font-medium mb-2">Full Name</label>
                    <input type="text" name="full_name" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Email</label>
                    <input type="email" name="email" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Phone</label>
                    <input type="tel" name="phone" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Password</label>
                    <input type="password" name="password" required
                        class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                </div>
                <div>
                    <label class="block text-sm font-medium mb-2">Role</label>
                    <select name="role" required class="w-full px-4 py-2 bg-background border border-input rounded-lg">
                        <option value="customer">Customer</option>
                        <option value="support_agent">Support Agent</option>
                        <option value="auditor">Auditor</option>
                        <option value="admin">Admin</option>
                    </select>
                </div>
                <div class="flex gap-3">
                    <button type="submit" class="flex-1 bg-primary text-primary-foreground py-2 rounded-lg hover:opacity-90">
                        Create User
                    </button>
                    <button type="button" onclick="this.closest('.fixed').remove()" class="flex-1 bg-secondary text-secondary-foreground py-2 rounded-lg hover:opacity-90">
                        Cancel
                    </button>
                </div>
            </form>
        </div>
    `
  document.body.appendChild(modal)

  document.getElementById("admin-create-user-form").addEventListener("submit", async (e) => {
    e.preventDefault()
    const formData = new FormData(e.target)
    const data = Object.fromEntries(formData)

    try {
      await apiCall(`${API_ADMIN}/users`, {
        method: "POST",
        body: JSON.stringify(data),
      })

      modal.remove()
      showSuccess("User created successfully!")
      loadView("admin-users")
    } catch (error) {
      alert(error.message)
    }
  })
}

// Delete User
window.deleteUser = async (userId) => {
  if (!confirm("Are you sure you want to delete this user?")) return

  try {
    await apiCall(`${API_ADMIN}/users/${userId}`, {
      method: "DELETE",
    })

    showSuccess("User deleted successfully!")
    loadView("admin-users")
  } catch (error) {
    alert(error.message)
  }
}

// Admin Accounts View
async function loadAdminAccountsView(container) {
  try {
    const accountsData = await apiCall(`${API_ACCOUNTS}/all`)
    const accounts = accountsData.accounts

    container.innerHTML = `
            <div class="space-y-6">
                <h2 class="text-2xl font-bold">All Bank Accounts</h2>
                
                <div class="bg-card border border-border rounded-xl overflow-hidden">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Account Number</th>
                                <th>Type</th>
                                <th>Owner</th>
                                <th>Balance</th>
                                <th>Status</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${accounts
                              .map(
                                (account) => `
                                <tr>
                                    <td class="font-mono">${account.account_number}</td>
                                    <td>${account.account_type}</td>
                                    <td>${account.user.full_name}</td>
                                    <td class="font-bold">$${account.balance.toFixed(2)}</td>
                                    <td><span class="status-badge status-${account.status}">${account.status}</span></td>
                                    <td>
                                        <select onchange="updateAccountStatus(${account.id}, this.value)" class="px-3 py-1 bg-background border border-input rounded text-sm">
                                            <option value="">Change Status...</option>
                                            <option value="active">Active</option>
                                            <option value="frozen">Frozen</option>
                                            <option value="closed">Closed</option>
                                        </select>
                                    </td>
                                </tr>
                            `,
                              )
                              .join("")}
                        </tbody>
                    </table>
                </div>
            </div>
        `
  } catch (error) {
    container.innerHTML = `<div class="text-destructive">Error loading accounts: ${error.message}</div>`
  }
}

// Update Account Status
window.updateAccountStatus = async (accountId, status) => {
  if (!status) return

  try {
    await apiCall(`${API_ACCOUNTS}/${accountId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status }),
    })

    showSuccess("Account status updated!")
    loadView("admin-accounts")
  } catch (error) {
    alert(error.message)
  }
}

// Audit Logs View
async function loadAuditView(container) {
  try {
    const logsData = await apiCall(`${API_ADMIN}/audit-logs`)
    const logs = logsData.logs

    container.innerHTML = `
            <div class="space-y-6">
                <h2 class="text-2xl font-bold">Audit & Security Logs</h2>
                
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <div class="bg-card border border-border rounded-xl p-4">
                        <div class="text-sm text-muted-foreground mb-1">Total Events</div>
                        <div class="text-2xl font-bold">${logs.length}</div>
                    </div>
                    <div class="bg-card border border-border rounded-xl p-4">
                        <div class="text-sm text-muted-foreground mb-1">Critical</div>
                        <div class="text-2xl font-bold text-destructive">${logs.filter((l) => l.severity === "critical").length}</div>
                    </div>
                    <div class="bg-card border border-border rounded-xl p-4">
                        <div class="text-sm text-muted-foreground mb-1">Warnings</div>
                        <div class="text-2xl font-bold text-yellow-500">${logs.filter((l) => l.severity === "warning").length}</div>
                    </div>
                    <div class="bg-card border border-border rounded-xl p-4">
                        <div class="text-sm text-muted-foreground mb-1">Info</div>
                        <div class="text-2xl font-bold text-primary">${logs.filter((l) => l.severity === "info").length}</div>
                    </div>
                </div>
                
                <div class="bg-card border border-border rounded-xl overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>User</th>
                                    <th>Action</th>
                                    <th>Details</th>
                                    <th>IP Address</th>
                                    <th>Severity</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${logs
                                  .map(
                                    (log) => `
                                    <tr>
                                        <td class="text-sm">${new Date(log.created_at).toLocaleString()}</td>
                                        <td>${log.user_name || "System"}</td>
                                        <td class="font-mono text-sm">${log.action}</td>
                                        <td class="text-sm max-w-xs truncate">${log.details || "-"}</td>
                                        <td class="font-mono text-sm">${log.ip_address || "-"}</td>
                                        <td>
                                            <span class="status-badge ${
                                              log.severity === "critical"
                                                ? "bg-destructive/10 text-destructive"
                                                : log.severity === "warning"
                                                  ? "bg-yellow-500/10 text-yellow-500"
                                                  : "status-active"
                                            }">
                                                ${log.severity}
                                            </span>
                                        </td>
                                    </tr>
                                `,
                                  )
                                  .join("")}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        `
  } catch (error) {
    container.innerHTML = `<div class="text-destructive">Error loading audit logs: ${error.message}</div>`
  }
}

// Check for existing session on page load
window.addEventListener("DOMContentLoaded", () => {
  const savedToken = localStorage.getItem("authToken")
  const savedUser = localStorage.getItem("currentUser")

  if (savedToken && savedUser) {
    authToken = savedToken
    currentUser = JSON.parse(savedUser)

    // Validate token
    apiCall(`${API_AUTH}/validate`)
      .then(() => {
        showDashboard()
      })
      .catch(() => {
        // Token invalid, clear storage
        localStorage.removeItem("authToken")
        localStorage.removeItem("currentUser")
        authToken = null
        currentUser = null
      })
  }
})
