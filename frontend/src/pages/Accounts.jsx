import { useEffect, useState } from "react";
import axios from "axios";
import {
  ChevronLeft,
  ChevronRight,
  Filter,
  RefreshCw,
  Search,
  UserRound,
  WalletCards,
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