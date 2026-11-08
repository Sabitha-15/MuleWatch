import { useEffect, useState } from "react";
import axios from "axios";
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  Plus,
  RefreshCw,
  Search,
  UserRound,
  WalletCards,
  X,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

function Accounts() {
  const [accounts, setAccounts] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 10,
    total_accounts: 0,
    total_pages: 0,
  });

  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [showCreateAccount, setShowCreateAccount] = useState(false);
  const [customers, setCustomers] = useState([]);
  const [creatingAccount, setCreatingAccount] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createForm, setCreateForm] = useState({
    customer_id: "",
    account_number: "",
    account_type: "SAVINGS",
    balance: "0",
    status: "ACTIVE",
  });

  const [showCreateCustomer, setShowCreateCustomer] = useState(false);
  const [creatingCustomer, setCreatingCustomer] = useState(false);
  const [customerError, setCustomerError] = useState("");
  const [customerForm, setCustomerForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    date_of_birth: "",
    status: "ACTIVE",
  });

  const [showCustomerManagement, setShowCustomerManagement] = useState(false);
  const [selectedCustomerId, setSelectedCustomerId] = useState("");
  const [customerSummary, setCustomerSummary] = useState(null);
  const [customerAudit, setCustomerAudit] = useState([]);
  const [managementLoading, setManagementLoading] = useState(false);
  const [managementError, setManagementError] = useState("");
  const [newCustomerStatus, setNewCustomerStatus] = useState("ACTIVE");
  const [changeReason, setChangeReason] = useState("");
  const [savingCustomerStatus, setSavingCustomerStatus] = useState(false);

  async function fetchAccounts(
    requestedPage = pagination.page,
    requestedSearch = search,
    requestedStatus = status
  ) {
    try {
      setLoading(true);
      setError("");

      const params = {
        page: requestedPage,
        page_size: 10,
      };

      if (requestedSearch.trim()) {
        params.search = requestedSearch.trim();
      }

      if (requestedStatus) {
        params.status = requestedStatus;
      }

      const response = await axios.get(
        `${API_BASE_URL}/api/accounts`,
        { params }
      );

      setAccounts(response.data.accounts || []);
      setPagination(response.data.pagination);
    } catch (err) {
      console.error("Accounts API error:", err);

      setError(
        "Unable to load account information. Make sure the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAccounts(1, "", "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function handleSearchSubmit(event) {
    event.preventDefault();
    fetchAccounts(1, search, status);
  }

  function handleStatusChange(event) {
    const newStatus = event.target.value;

    setStatus(newStatus);
    fetchAccounts(1, search, newStatus);
  }

  async function openCreateAccount() {
    try {
      setCreateError("");

      const response = await axios.get(
        `${API_BASE_URL}/api/accounts/customers`
      );

      const customerList = response.data.customers || [];
      setCustomers(customerList);

      if (customerList.length === 0) {
        setCreateError("No customers are available.");
      }

      setCreateForm({
        customer_id: customerList[0]?.customer_id
          ? String(customerList[0].customer_id)
          : "",
        account_number: "",
        account_type: "SAVINGS",
        balance: "0",
        status: "ACTIVE",
      });

      setShowCreateAccount(true);
    } catch (err) {
      console.error("Customer API error:", err);
      setCreateError(
        "Unable to load customers. Make sure the FastAPI backend is running."
      );
      setShowCreateAccount(true);
    }
  }

  function closeCreateAccount() {
    if (creatingAccount) {
      return;
    }

    setShowCreateAccount(false);
    setCreateError("");
  }

  function handleCreateFormChange(event) {
    const { name, value } = event.target;

    setCreateForm((current) => ({
      ...current,
      [name]: value,
    }));
  }

  async function handleCreateAccount(event) {
    event.preventDefault();
    setCreateError("");

    if (!createForm.customer_id) {
      setCreateError("Please select a customer.");
      return;
    }

    if (!createForm.account_number.trim()) {
      setCreateError("Please enter an account number.");
      return;
    }

    const balance = Number(createForm.balance);

    if (!Number.isFinite(balance) || balance < 0) {
      setCreateError("Opening balance must be zero or greater.");
      return;
    }

    try {
      setCreatingAccount(true);

      await axios.post(
        `${API_BASE_URL}/api/accounts`,
        {
          customer_id: Number(createForm.customer_id),
          account_number: createForm.account_number.trim(),
          account_type: createForm.account_type,
          balance,
          status: createForm.status,
        }
      );

      setShowCreateAccount(false);
      setCreateError("");

      await fetchAccounts(1, search, status);
    } catch (err) {
      console.error("Create account API error:", err);

      const detail = err?.response?.data?.detail;

      setCreateError(
        detail || "Unable to create the account."
      );
    } finally {
      setCreatingAccount(false);
    }
  }

  function openCreateCustomer() {
    setCustomerError("");
    setCustomerForm({
      full_name: "",
      email: "",
      phone: "",
      date_of_birth: "",
      status: "ACTIVE",
    });
    setShowCreateCustomer(true);
  }

  async function handleCreateCustomer(event) {
    event.preventDefault();
    setCustomerError("");

    if (!customerForm.full_name.trim()) {
      setCustomerError("Customer name is required.");
      return;
    }

    try {
      setCreatingCustomer(true);
      const response = await axios.post(
        `${API_BASE_URL}/api/accounts/customers`,
        {
          full_name: customerForm.full_name.trim(),
          email: customerForm.email.trim() || null,
          phone: customerForm.phone.trim() || null,
          date_of_birth: customerForm.date_of_birth || null,
          status: customerForm.status,
        }
      );

      const createdCustomer = response.data.customer;
      const customersResponse = await axios.get(
        `${API_BASE_URL}/api/accounts/customers`
      );
      const customerList = customersResponse.data.customers || [];
      setCustomers(customerList);
      setCreateForm((current) => ({
        ...current,
        customer_id: String(createdCustomer.customer_id),
      }));
      setShowCreateCustomer(false);
      setShowCreateAccount(true);
    } catch (err) {
      console.error("Create customer API error:", err);
      setCustomerError(
        err?.response?.data?.detail || "Unable to create customer."
      );
    } finally {
      setCreatingCustomer(false);
    }
  }


  async function loadCustomerManagement(customerId) {
    if (!customerId) {
      setCustomerSummary(null);
      setCustomerAudit([]);
      return;
    }

    try {
      setManagementLoading(true);
      setManagementError("");

      const [summaryResponse, auditResponse] = await Promise.all([
        axios.get(
          `${API_BASE_URL}/api/accounts/customers/${customerId}/summary`
        ),
        axios.get(
          `${API_BASE_URL}/api/accounts/customers/${customerId}/audit`
        ),
      ]);

      setCustomerSummary(summaryResponse.data);
      setCustomerAudit(auditResponse.data.audit_records || []);
      setNewCustomerStatus(summaryResponse.data.customer_status || "ACTIVE");
    } catch (err) {
      console.error("Customer management API error:", err);
      setManagementError(
        err?.response?.data?.detail ||
          "Unable to load customer summary and audit history."
      );
      setCustomerSummary(null);
      setCustomerAudit([]);
    } finally {
      setManagementLoading(false);
    }
  }

  async function openCustomerManagement() {
    try {
      setManagementError("");
      const response = await axios.get(
        `${API_BASE_URL}/api/accounts/customers`
      );
      const customerList = response.data.customers || [];
      setCustomers(customerList);

      if (customerList.length === 0) {
        setManagementError("No customers are available.");
        setSelectedCustomerId("");
        setCustomerSummary(null);
        setCustomerAudit([]);
      } else {
        const firstId = String(customerList[0].customer_id);
        setSelectedCustomerId(firstId);
        await loadCustomerManagement(firstId);
      }
      setShowCustomerManagement(true);
    } catch (err) {
      console.error("Customer list API error:", err);
      setManagementError(
        err?.response?.data?.detail || "Unable to load customers."
      );
      setShowCustomerManagement(true);
    }
  }

  async function handleManagementCustomerChange(event) {
    const customerId = event.target.value;
    setSelectedCustomerId(customerId);
    await loadCustomerManagement(customerId);
  }

  async function handleCustomerStatusUpdate(event) {
    event.preventDefault();
    if (!selectedCustomerId) return;

    try {
      setSavingCustomerStatus(true);
      setManagementError("");

      await axios.patch(
        `${API_BASE_URL}/api/accounts/customers/${selectedCustomerId}/status`,
        {
          new_status: newCustomerStatus,
          change_reason: changeReason.trim() || null,
        }
      );

      setChangeReason("");
      await loadCustomerManagement(selectedCustomerId);
      await fetchAccounts(pagination.page, search, status);
    } catch (err) {
      console.error("Customer status update error:", err);
      setManagementError(
        err?.response?.data?.detail ||
          "Unable to update customer status."
      );
    } finally {
      setSavingCustomerStatus(false);
    }
  }

  function handleRefresh() {
    fetchAccounts(pagination.page, search, status);
  }

  function handlePreviousPage() {
    if (pagination.page <= 1) {
      return;
    }

    fetchAccounts(
      pagination.page - 1,
      search,
      status
    );
  }

  function handleNextPage() {
    if (pagination.page >= pagination.total_pages) {
      return;
    }

    fetchAccounts(
      pagination.page + 1,
      search,
      status
    );
  }

  function formatCurrency(value) {
    if (value === null || value === undefined) {
      return "—";
    }

    return `₹${Number(value).toLocaleString("en-IN")}`;
  }

  function formatDate(value) {
    if (!value) {
      return "—";
    }

    return new Date(value).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function getRiskClass(riskLevel) {
    if (!riskLevel) {
      return "unknown";
    }

    return riskLevel.toLowerCase();
  }

  function getStatusClass(accountStatus) {
    if (!accountStatus) {
      return "unknown";
    }

    return accountStatus.toLowerCase();
  }

  if (loading && accounts.length === 0) {
    return (
      <div className="dashboard-state">
        <div className="loading-spinner" />
        <p>Loading account intelligence...</p>
      </div>
    );
  }

  if (error && accounts.length === 0) {
    return (
      <div className="dashboard-state dashboard-error">
        <h3>Accounts unavailable</h3>
        <p>{error}</p>

        <button
          onClick={() => fetchAccounts(1, search, status)}
          className="retry-button"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="accounts-page">

      {showCustomerManagement && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.48)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1200,
            padding: "20px",
            overflowY: "auto",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "900px",
              maxHeight: "90vh",
              overflowY: "auto",
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: "16px",
              boxShadow: "0 24px 70px rgba(15, 23, 42, 0.2)",
              padding: "24px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "16px", marginBottom: "18px" }}>
              <div>
                <p className="page-eyebrow">PHASE 2 · DATABASE OPERATIONS</p>
                <h2 style={{ margin: "4px 0 0" }}>Customer Management</h2>
                <p style={{ margin: "6px 0 0", color: "#64748B", fontSize: "13px" }}>
                  Customer summary, stored-procedure status updates and trigger audit history.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setShowCustomerManagement(false)}
                aria-label="Close customer management"
                style={{ border: "none", background: "transparent", cursor: "pointer", color: "#64748B" }}
              >
                <X size={20} />
              </button>
            </div>

            <label style={{ display: "flex", flexDirection: "column", gap: "7px", maxWidth: "420px", marginBottom: "18px" }}>
              <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Select Customer</span>
              <select
                value={selectedCustomerId}
                onChange={handleManagementCustomerChange}
                style={{ height: "42px", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "0 11px", background: "#FFFFFF" }}
              >
                <option value="">Select customer</option>
                {customers.map((customer) => (
                  <option key={customer.customer_id} value={customer.customer_id}>
                    {customer.full_name} — #{customer.customer_id}
                  </option>
                ))}
              </select>
            </label>

            {managementError && (
              <div style={{ marginBottom: "14px", padding: "11px 12px", borderRadius: "8px", background: "#FEF2F2", border: "1px solid #FECACA", color: "#B91C1C", fontSize: "13px" }}>
                {managementError}
              </div>
            )}

            {managementLoading ? (
              <p style={{ color: "#64748B" }}>Loading customer database details...</p>
            ) : customerSummary ? (
              <>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "12px", marginBottom: "20px" }}>
                  {[
                    ["Customer", customerSummary.full_name],
                    ["Status", customerSummary.customer_status],
                    ["Accounts", customerSummary.account_count],
                    ["Active Accounts", customerSummary.active_account_count],
                    ["Total Balance", formatCurrency(customerSummary.total_account_balance)],
                    ["Transactions", customerSummary.transaction_count],
                  ].map(([label, value]) => (
                    <div key={label} style={{ border: "1px solid #E2E8F0", borderRadius: "10px", padding: "14px", background: "#F8FAFC" }}>
                      <div style={{ color: "#64748B", fontSize: "11px", fontWeight: 700, textTransform: "uppercase" }}>{label}</div>
                      <div style={{ color: "#172033", fontSize: "17px", fontWeight: 700, marginTop: "6px", overflowWrap: "anywhere" }}>{value ?? "—"}</div>
                    </div>
                  ))}
                </div>

                <form onSubmit={handleCustomerStatusUpdate} style={{ border: "1px solid #E2E8F0", borderRadius: "12px", padding: "16px", marginBottom: "20px" }}>
                  <h3 style={{ margin: "0 0 12px", fontSize: "15px" }}>Update Customer Status</h3>
                  <div style={{ display: "grid", gridTemplateColumns: "minmax(150px, 1fr) minmax(200px, 2fr) auto", gap: "10px", alignItems: "end" }}>
                    <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <span style={{ fontSize: "12px", color: "#475569", fontWeight: 600 }}>New Status</span>
                      <select value={newCustomerStatus} onChange={(e) => setNewCustomerStatus(e.target.value)} style={{ height: "40px", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "0 9px", background: "#FFFFFF" }}>
                        <option value="ACTIVE">ACTIVE</option>
                        <option value="INACTIVE">INACTIVE</option>
                        <option value="BLOCKED">BLOCKED</option>
                      </select>
                    </label>
                    <label style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                      <span style={{ fontSize: "12px", color: "#475569", fontWeight: 600 }}>Change Reason</span>
                      <input value={changeReason} onChange={(e) => setChangeReason(e.target.value)} placeholder="Reason for status change" style={{ height: "40px", border: "1px solid #CBD5E1", borderRadius: "8px", padding: "0 10px" }} />
                    </label>
                    <button type="submit" disabled={savingCustomerStatus || !selectedCustomerId} className="accounts-refresh-button" style={{ background: "#1D4ED8", color: "#FFFFFF", borderColor: "#1D4ED8", height: "40px" }}>
                      {savingCustomerStatus ? "Updating..." : "Update Status"}
                    </button>
                  </div>
                  <p style={{ color: "#64748B", fontSize: "12px", margin: "10px 0 0" }}>
                    This action calls the PostgreSQL stored procedure. The database trigger records actual customer changes in the audit log.
                  </p>
                </form>

                <div>
                  <h3 style={{ margin: "0 0 10px", fontSize: "15px" }}>Customer Audit History</h3>
                  {customerAudit.length === 0 ? (
                    <p style={{ color: "#64748B", fontSize: "13px" }}>No audit records for this customer yet.</p>
                  ) : (
                    <div style={{ overflowX: "auto", border: "1px solid #E2E8F0", borderRadius: "10px" }}>
                      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "12px" }}>
                        <thead style={{ background: "#F8FAFC", textAlign: "left" }}>
                          <tr>
                            <th style={{ padding: "10px" }}>Audit ID</th>
                            <th style={{ padding: "10px" }}>Action</th>
                            <th style={{ padding: "10px" }}>Changed At</th>
                            <th style={{ padding: "10px" }}>Reason</th>
                            <th style={{ padding: "10px" }}>Change Details</th>
                          </tr>
                        </thead>
                        <tbody>
                          {customerAudit.map((record) => (
                            <tr key={record.audit_id} style={{ borderTop: "1px solid #E2E8F0" }}>
                              <td style={{ padding: "10px" }}>{record.audit_id}</td>
                              <td style={{ padding: "10px" }}>{record.action_type}</td>
                              <td style={{ padding: "10px", whiteSpace: "nowrap" }}>{formatDate(record.changed_at)}</td>
                              <td style={{ padding: "10px" }}>{record.change_reason || "—"}</td>
                              <td style={{ padding: "10px" }}>
                                <details>
                                  <summary style={{ cursor: "pointer", color: "#1D4ED8" }}>View old/new values</summary>
                                  <pre style={{ whiteSpace: "pre-wrap", maxWidth: "360px", fontSize: "10px" }}>
                                    {JSON.stringify({ old: record.old_data, new: record.new_data }, null, 2)}
                                  </pre>
                                </details>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <p style={{ color: "#64748B", fontSize: "13px" }}>Select a customer to view the database summary and audit history.</p>
            )}
          </div>
        </div>
      )}

      {showCreateCustomer && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.45)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1100,
            padding: "24px",
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "520px",
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: "16px",
              boxShadow: "0 24px 70px rgba(15, 23, 42, 0.18)",
              padding: "24px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
              <div>
                <p className="page-eyebrow">CUSTOMER OPERATIONS</p>
                <h2 style={{ margin: "4px 0 0" }}>Create New Customer</h2>
              </div>
              <button
                type="button"
                onClick={() => setShowCreateCustomer(false)}
                disabled={creatingCustomer}
                aria-label="Close create customer form"
                style={{ border: "none", background: "transparent", cursor: "pointer", color: "#64748B" }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateCustomer}>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                <label style={{ display: "flex", flexDirection: "column", gap: "7px", gridColumn: "1 / -1" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Full Name *</span>
                  <input
                    value={customerForm.full_name}
                    onChange={(e) => setCustomerForm({ ...customerForm, full_name: e.target.value })}
                    required
                    disabled={creatingCustomer}
                    placeholder="Customer full name"
                  />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Email</span>
                  <input
                    type="email"
                    value={customerForm.email}
                    onChange={(e) => setCustomerForm({ ...customerForm, email: e.target.value })}
                    disabled={creatingCustomer}
                    placeholder="name@example.com"
                  />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Phone</span>
                  <input
                    value={customerForm.phone}
                    onChange={(e) => setCustomerForm({ ...customerForm, phone: e.target.value })}
                    disabled={creatingCustomer}
                    placeholder="Phone number"
                  />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Date of Birth</span>
                  <input
                    type="date"
                    value={customerForm.date_of_birth}
                    onChange={(e) => setCustomerForm({ ...customerForm, date_of_birth: e.target.value })}
                    disabled={creatingCustomer}
                  />
                </label>
                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>Status</span>
                  <select
                    value={customerForm.status}
                    onChange={(e) => setCustomerForm({ ...customerForm, status: e.target.value })}
                    disabled={creatingCustomer}
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="INACTIVE">INACTIVE</option>
                    <option value="BLOCKED">BLOCKED</option>
                  </select>
                </label>
              </div>

              {customerError && (
                <div style={{ marginTop: "14px", padding: "11px 12px", borderRadius: "8px", background: "#FEF2F2", border: "1px solid #FECACA", color: "#B91C1C", fontSize: "13px" }}>
                  {customerError}
                </div>
              )}

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "22px" }}>
                <button
                  type="button"
                  onClick={() => setShowCreateCustomer(false)}
                  disabled={creatingCustomer}
                  className="accounts-refresh-button"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingCustomer}
                  className="accounts-refresh-button"
                  style={{ background: "#1D4ED8", color: "#FFFFFF", borderColor: "#1D4ED8", minWidth: "145px" }}
                >
                  {creatingCustomer ? "Creating..." : "Create Customer"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showCreateAccount && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(15, 23, 42, 0.38)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "24px",
          }}
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              closeCreateAccount();
            }
          }}
        >
          <div
            style={{
              width: "100%",
              maxWidth: "560px",
              background: "#FFFFFF",
              border: "1px solid #E2E8F0",
              borderRadius: "16px",
              boxShadow: "0 24px 70px rgba(15, 23, 42, 0.18)",
              padding: "24px",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                marginBottom: "20px",
              }}
            >
              <div>
                <p className="page-eyebrow">ACCOUNT OPERATIONS</p>
                <h2 style={{ margin: "4px 0 6px" }}>
                  Create New Account
                </h2>
                <p
                  style={{
                    margin: 0,
                    color: "#64748B",
                    fontSize: "13px",
                  }}
                >
                  Create a monitored customer account directly in MuleWatch.
                </p>
              </div>

              <button
                type="button"
                onClick={closeCreateAccount}
                disabled={creatingAccount}
                aria-label="Close create account form"
                style={{
                  border: "none",
                  background: "transparent",
                  cursor: "pointer",
                  color: "#64748B",
                  padding: "4px",
                }}
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateAccount}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: "16px",
                }}
              >
                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
                    Customer
                  </span>
                  <select
                    name="customer_id"
                    value={createForm.customer_id}
                    onChange={handleCreateFormChange}
                    disabled={creatingAccount}
                    style={{
                      height: "42px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      padding: "0 11px",
                      background: "#FFFFFF",
                      color: "#172033",
                    }}
                  >
                    <option value="">Select customer</option>
                    {customers.map((customer) => (
                      <option
                        key={customer.customer_id}
                        value={customer.customer_id}
                      >
                        {customer.full_name} — #{customer.customer_id}
                      </option>
                    ))}
                  </select>
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
                    Account Number
                  </span>
                  <input
                    name="account_number"
                    value={createForm.account_number}
                    onChange={handleCreateFormChange}
                    placeholder="e.g. MWACC100011"
                    disabled={creatingAccount}
                    style={{
                      height: "42px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      padding: "0 11px",
                      color: "#172033",
                    }}
                  />
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
                    Account Type
                  </span>
                  <select
                    name="account_type"
                    value={createForm.account_type}
                    onChange={handleCreateFormChange}
                    disabled={creatingAccount}
                    style={{
                      height: "42px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      padding: "0 11px",
                      background: "#FFFFFF",
                      color: "#172033",
                    }}
                  >
                    <option value="SAVINGS">SAVINGS</option>
                    <option value="CURRENT">CURRENT</option>
                  </select>
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: "7px" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
                    Opening Balance
                  </span>
                  <input
                    name="balance"
                    type="number"
                    min="0"
                    step="0.01"
                    value={createForm.balance}
                    onChange={handleCreateFormChange}
                    disabled={creatingAccount}
                    style={{
                      height: "42px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      padding: "0 11px",
                      color: "#172033",
                    }}
                  />
                </label>

                <label style={{ display: "flex", flexDirection: "column", gap: "7px", gridColumn: "1 / -1" }}>
                  <span style={{ fontSize: "12px", fontWeight: 700, color: "#334155" }}>
                    Account Status
                  </span>
                  <select
                    name="status"
                    value={createForm.status}
                    onChange={handleCreateFormChange}
                    disabled={creatingAccount}
                    style={{
                      height: "42px",
                      border: "1px solid #CBD5E1",
                      borderRadius: "8px",
                      padding: "0 11px",
                      background: "#FFFFFF",
                      color: "#172033",
                    }}
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="BLOCKED">BLOCKED</option>
                    <option value="CLOSED">CLOSED</option>
                  </select>
                </label>
              </div>

              {createError && (
                <div
                  style={{
                    marginTop: "16px",
                    padding: "11px 12px",
                    borderRadius: "8px",
                    background: "#FEF2F2",
                    border: "1px solid #FECACA",
                    color: "#B91C1C",
                    fontSize: "13px",
                  }}
                >
                  {createError}
                </div>
              )}

              <div
                style={{
                  display: "flex",
                  justifyContent: "flex-end",
                  gap: "10px",
                  marginTop: "22px",
                }}
              >
                <button
                  type="button"
                  onClick={closeCreateAccount}
                  disabled={creatingAccount}
                  className="accounts-refresh-button"
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  disabled={creatingAccount}
                  className="accounts-refresh-button"
                  style={{
                    background: "#1D4ED8",
                    color: "#FFFFFF",
                    borderColor: "#1D4ED8",
                    minWidth: "140px",
                  }}
                >
                  {creatingAccount ? "Creating..." : "Create Account"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* PAGE HEADER */}

      <div className="accounts-page-header">

        <div>
          <p className="page-eyebrow">ACCOUNT INTELLIGENCE</p>

          <h1>Accounts</h1>

          <p className="page-description">
            Search and investigate customer accounts, balances and current
            risk assessments.
          </p>
        </div>

        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <button
            className="accounts-refresh-button"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw
              size={14}
              className={loading ? "refresh-spinning" : ""}
            />

            Refresh
          </button>

          <button
            className="accounts-refresh-button"
            onClick={openCustomerManagement}
            type="button"
          >
            Customer Management
          </button>

          <button
            className="accounts-refresh-button"
            onClick={openCreateCustomer}
            type="button"
          >
            <Plus size={15} />
            Create Customer
          </button>

          <button
            className="accounts-refresh-button"
            onClick={openCreateAccount}
            type="button"
            style={{
              background: "#1D4ED8",
              color: "#FFFFFF",
              borderColor: "#1D4ED8",
            }}
          >
            <Plus size={15} />
            Create Account
          </button>
        </div>

      </div>

      {/* SUMMARY */}

      <div className="accounts-summary">

        <div className="accounts-summary-card">
          <div className="accounts-summary-icon blue">
            <WalletCards size={18} />
          </div>

          <div>
            <span>Total Accounts</span>
            <strong>{pagination.total_accounts}</strong>
          </div>
        </div>

        <div className="accounts-summary-card">
          <div className="accounts-summary-icon purple">
            <UserRound size={18} />
          </div>

          <div>
            <span>Showing</span>
            <strong>{accounts.length}</strong>
          </div>
        </div>

      </div>

      {/* FILTER BAR */}

      <div className="accounts-toolbar">

        <form
          className="accounts-search"
          onSubmit={handleSearchSubmit}
        >
          <Search size={17} />

          <input
            type="text"
            placeholder="Search account number, customer or email..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />

          <button type="submit">
            Search
          </button>
        </form>

        <div className="status-filter">

          <Filter size={15} />

          <select
            value={status}
            onChange={handleStatusChange}
          >
            <option value="">All statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="BLOCKED">Blocked</option>
            <option value="CLOSED">Closed</option>
          </select>

        </div>

      </div>

      {/* ERROR WHILE REFRESHING */}

      {error && (
        <div className="inline-error">
          {error}
        </div>
      )}

      {/* ACCOUNTS TABLE */}

      <div className="accounts-table-card">

        <div className="accounts-table-header">

          <div>
            <h2>Account Registry</h2>

            <p>
              Customer and risk information for monitored accounts
            </p>
          </div>

          <span>
            Page {pagination.page} of {pagination.total_pages || 1}
          </span>

        </div>

        <div className="accounts-table-wrapper">

          <table className="accounts-table">

            <thead>
              <tr>
                <th>ACCOUNT</th>
                <th>CUSTOMER</th>
                <th>TYPE</th>
                <th>BALANCE</th>
                <th>RISK</th>
                <th>ACCOUNT STATUS</th>
                <th>OPENED</th>
              </tr>
            </thead>

            <tbody>

              {accounts.length > 0 ? (
                accounts.map((account) => (
                  <tr
  key={account.account_id}
  className="account-row-clickable"
  onClick={() =>
    window.location.href = `/accounts/${account.account_id}`
  }
>

                    <td>
                      <div className="account-number-cell">

                        <div className="account-table-avatar">
                          {account.account_number?.slice(-2)}
                        </div>

                        <div>
                          <strong>
                            {account.account_number}
                          </strong>

                          <span>
                            ID #{account.account_id}
                          </span>
                        </div>

                      </div>
                    </td>

                    <td>
                      <div className="customer-cell">

                        <strong>
                          {account.customer_name}
                        </strong>

                        <span>
                          {account.email || "No email"}
                        </span>

                      </div>
                    </td>

                    <td>
                      <span className="account-type">
                        {account.account_type}
                      </span>
                    </td>

                    <td>
                      <strong className="balance-value">
                        {formatCurrency(account.balance)}
                      </strong>
                    </td>

                    <td>
                      <div className="risk-cell">

                        {account.risk_score !== null &&
                        account.risk_score !== undefined ? (
                          <>
                            <strong>
                              {Number(account.risk_score).toFixed(0)}
                            </strong>

                            <span
                              className={`risk-badge ${getRiskClass(
                                account.risk_level
                              )}`}
                            >
                              {account.risk_level}
                            </span>
                          </>
                        ) : (
                          <span className="no-risk">
                            Not assessed
                          </span>
                        )}

                      </div>
                    </td>

                    <td>
                      <span
                        className={`account-status ${getStatusClass(
                          account.account_status
                        )}`}
                      >
                        <span className="status-indicator" />

                        {account.account_status}
                      </span>
                    </td>

                    <td>
                      <span className="opened-date">
                        {formatDate(account.opened_at)}
                      </span>
                    </td>

                  </tr>
                ))
              ) : (
                <tr>
                  <td
                    colSpan="7"
                    className="accounts-empty-row"
                  >
                    <Search size={22} />

                    <strong>No accounts found</strong>

                    <span>
                      Try changing your search or status filter.
                    </span>
                  </td>
                </tr>
              )}

            </tbody>

          </table>

        </div>

        {/* PAGINATION */}

        <div className="accounts-pagination">

          <span>
            Showing {accounts.length} of{" "}
            {pagination.total_accounts} accounts
          </span>

          <div className="pagination-controls">

            <button
              onClick={handlePreviousPage}
              disabled={pagination.page <= 1 || loading}
              aria-label="Previous page"
            >
              <ChevronLeft size={16} />
            </button>

            <span>
              {pagination.page}
            </span>

            <button
              onClick={handleNextPage}
              disabled={
                pagination.page >= pagination.total_pages ||
                loading
              }
              aria-label="Next page"
            >
              <ChevronRight size={16} />
            </button>

          </div>

        </div>

      </div>

    </div>
  );
}

export default Accounts;