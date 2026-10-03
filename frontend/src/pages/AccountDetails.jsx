import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft,
  ArrowDownLeft,
  ArrowUpRight,
  CalendarDays,
  CircleAlert,
  Mail,
  Phone,
  RefreshCw,
  ShieldAlert,
  UserRound,
  WalletCards,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

function AccountDetails() {
  const { accountId } = useParams();
  const navigate = useNavigate();

  const [account, setAccount] = useState(null);
  const [transactions, setTransactions] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  async function loadAccountDetails(showRefreshState = false) {
    try {
      if (showRefreshState) {
        setRefreshing(true);
      } else {
        setLoading(true);
      }

      setError("");

      const [accountResponse, transactionResponse] =
        await Promise.all([
          axios.get(
            `${API_BASE_URL}/api/accounts/${accountId}`
          ),
          axios.get(
            `${API_BASE_URL}/api/accounts/${accountId}/transactions`,
            {
              params: {
                page: 1,
                page_size: 10,
              },
            }
          ),
        ]);

      setAccount(accountResponse.data);
      setTransactions(
        transactionResponse.data.transactions || []
      );
    } catch (err) {
      console.error("Account details error:", err);

      setError(
        "Unable to load account investigation data. Make sure the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadAccountDetails();
  }, [accountId]);

  function formatCurrency(value) {
    if (value === null || value === undefined) {
      return "₹0";
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

  function formatDateTime(value) {
    if (!value) {
      return "—";
    }

    return new Date(value).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function getRiskClass(level) {
    if (!level) {
      return "unknown";
    }

    return level.toLowerCase();
  }

  function getStatusClass(status) {
    if (!status) {
      return "unknown";
    }

    return status.toLowerCase();
  }

  function getTransactionDirection(transaction) {
    if (
      Number(transaction.sender_account_id) ===
      Number(accountId)
    ) {
      return "outgoing";
    }

    return "incoming";
  }

  const outgoingTransactions = transactions.filter(
    (transaction) =>
      Number(transaction.sender_account_id) ===
      Number(accountId)
  );

  const incomingTransactions = transactions.filter(
    (transaction) =>
      Number(transaction.receiver_account_id) ===
      Number(accountId)
  );

  const outgoingAmount = outgoingTransactions.reduce(
    (total, transaction) =>
      total + Number(transaction.amount || 0),
    0
  );

  const incomingAmount = incomingTransactions.reduce(
    (total, transaction) =>
      total + Number(transaction.amount || 0),
    0
  );

  if (loading) {
    return (
      <div className="dashboard-state">
        <div className="loading-spinner" />
        <p>Loading account investigation...</p>
      </div>
    );
  }

  if (error || !account) {
    return (
      <div className="dashboard-state dashboard-error">
        <CircleAlert size={28} />

        <h3>Investigation unavailable</h3>

        <p>
          {error || "The requested account could not be found."}
        </p>

        <button
          className="retry-button"
          onClick={() => loadAccountDetails()}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="account-details-page">

      {/* =====================================================
          HEADER
      ====================================================== */}

      <div className="account-details-header">

        <div>

          <button
            className="back-button"
            onClick={() => navigate("/accounts")}
          >
            <ArrowLeft size={15} />
            Back to Accounts
          </button>

          <p className="page-eyebrow">
            ACCOUNT INVESTIGATION
          </p>

          <div className="account-title-row">

            <div>
              <h1>{account.account_number}</h1>

              <p>
                Account #{account.account_id} ·{" "}
                {account.account_type}
              </p>
            </div>

            <span
              className={`account-status ${getStatusClass(
                account.account_status
              )}`}
            >
              <span className="status-indicator" />

              {account.account_status}
            </span>

          </div>

        </div>

        <button
          className="accounts-refresh-button"
          onClick={() => loadAccountDetails(true)}
          disabled={refreshing}
        >
          <RefreshCw
            size={14}
            className={
              refreshing ? "refresh-spinning" : ""
            }
          />

          Refresh
        </button>

      </div>

      {/* =====================================================
          RISK BANNER
      ====================================================== */}

      <section className="investigation-risk-banner">

        <div className="risk-banner-left">

          <div
            className={`risk-banner-icon ${getRiskClass(
              account.risk_level
            )}`}
          >
            <ShieldAlert size={22} />
          </div>

          <div>
            <span className="risk-banner-label">
              CURRENT ML RISK ASSESSMENT
            </span>

            <div className="risk-banner-title">
              {account.risk_level || "NOT ASSESSED"}
            </div>

            <p>
              {account.risk_reason ||
                "No risk assessment reason is currently available."}
            </p>
          </div>

        </div>

        <div className="risk-score-display">

          <span>RISK SCORE</span>

          <strong>
            {account.risk_score !== null &&
            account.risk_score !== undefined
              ? Number(account.risk_score).toFixed(0)
              : "—"}
          </strong>

          <small>
            {account.model_version
              ? `Model v${account.model_version}`
              : "No model assessment"}
          </small>

        </div>

      </section>

      {/* =====================================================
          ACCOUNT SNAPSHOT
      ====================================================== */}

      <div className="investigation-grid">

        <section className="investigation-card">

          <div className="investigation-card-header">
            <div>
              <span className="card-eyebrow">
                ACCOUNT PROFILE
              </span>

              <h2>Financial Snapshot</h2>
            </div>

            <WalletCards size={19} />
          </div>

          <div className="profile-detail-grid">

            <div>
              <span>Account Type</span>
              <strong>{account.account_type}</strong>
            </div>

            <div>
              <span>Current Balance</span>
              <strong>
                {formatCurrency(account.balance)}
              </strong>
            </div>

            <div>
              <span>Opened</span>
              <strong>
                {formatDate(account.opened_at)}
              </strong>
            </div>

            <div>
              <span>Account Status</span>
              <strong>
                {account.account_status}
              </strong>
            </div>

          </div>

        </section>

        {/* CUSTOMER PROFILE */}

        <section className="investigation-card">

          <div className="investigation-card-header">

            <div>
              <span className="card-eyebrow">
                CUSTOMER PROFILE
              </span>

              <h2>{account.customer_name}</h2>
            </div>

            <UserRound size={19} />

          </div>

          <div className="customer-contact-list">

            <div>
              <Mail size={15} />

              <span>
                {account.email || "No email available"}
              </span>
            </div>

            <div>
              <Phone size={15} />

              <span>
                {account.phone || "No phone available"}
              </span>
            </div>

            <div>
              <CalendarDays size={15} />

              <span>
                Date of birth:{" "}
                {formatDate(account.date_of_birth)}
              </span>
            </div>

          </div>

          <div className="customer-status-row">

            <span>Customer status</span>

            <strong>
              {account.customer_status}
            </strong>

          </div>

        </section>

      </div>

      {/* =====================================================
          TRANSACTION INTELLIGENCE
      ====================================================== */}

      <section className="investigation-card transaction-intelligence">

        <div className="investigation-card-header">

          <div>
            <span className="card-eyebrow">
              TRANSACTION INTELLIGENCE
            </span>

            <h2>Recent Financial Activity</h2>
          </div>

          <span className="transaction-count">
            {transactions.length} transactions
          </span>

        </div>

        <div className="transaction-summary-grid">

          <div className="transaction-summary incoming">

            <div className="transaction-summary-icon">
              <ArrowDownLeft size={17} />
            </div>

            <div>
              <span>Incoming</span>

              <strong>
                {formatCurrency(incomingAmount)}
              </strong>

              <small>
                {incomingTransactions.length} transactions
              </small>
            </div>

          </div>

          <div className="transaction-summary outgoing">

            <div className="transaction-summary-icon">
              <ArrowUpRight size={17} />
            </div>

            <div>
              <span>Outgoing</span>

              <strong>
                {formatCurrency(outgoingAmount)}
              </strong>

              <small>
                {outgoingTransactions.length} transactions
              </small>
            </div>

          </div>

          <div className="transaction-summary">

            <div className="transaction-summary-icon neutral">
              <WalletCards size={17} />
            </div>

            <div>
              <span>Net Movement</span>

              <strong>
                {formatCurrency(
                  incomingAmount - outgoingAmount
                )}
              </strong>

              <small>
                Based on loaded transactions
              </small>
            </div>

          </div>

        </div>

      </section>

      {/* =====================================================
          TRANSACTION HISTORY
      ====================================================== */}

      <section className="investigation-card">

        <div className="investigation-card-header">

          <div>
            <span className="card-eyebrow">
              TRANSACTION HISTORY
            </span>

            <h2>Account Transactions</h2>
          </div>

          <span className="transaction-count">
            Latest activity
          </span>

        </div>

        <div className="account-transactions-wrapper">

          <table className="account-transactions-table">

            <thead>

              <tr>
                <th>TRANSACTION</th>
                <th>DIRECTION</th>
                <th>COUNTERPARTY</th>
                <th>AMOUNT</th>
                <th>TYPE</th>
                <th>CHANNEL</th>
                <th>STATUS</th>
                <th>TIME</th>
              </tr>

            </thead>

            <tbody>

              {transactions.length > 0 ? (
                transactions.map((transaction) => {

                  const direction =
                    getTransactionDirection(transaction);

                  const isOutgoing =
                    direction === "outgoing";

                  return (
                    <tr key={transaction.transaction_id}>

                      <td>
                        <div className="transaction-id">
                          #{transaction.transaction_id}
                        </div>
                      </td>

                      <td>

                        <span
                          className={`transaction-direction ${direction}`}
                        >
                          {isOutgoing ? (
                            <ArrowUpRight size={13} />
                          ) : (
                            <ArrowDownLeft size={13} />
                          )}

                          {isOutgoing
                            ? "OUTGOING"
                            : "INCOMING"}
                        </span>

                      </td>

                      <td>
                        <div className="counterparty-cell">

                          <strong>
                            {isOutgoing
                              ? transaction.receiver_account_number
                              : transaction.sender_account_number}
                          </strong>

                          <span>
                            Account #
                            {isOutgoing
                              ? transaction.receiver_account_id
                              : transaction.sender_account_id}
                          </span>

                        </div>
                      </td>

                      <td>
                        <strong className="transaction-amount">
                          {formatCurrency(
                            transaction.amount
                          )}
                        </strong>
                      </td>

                      <td>
                        <span className="transaction-type">
                          {transaction.transaction_type}
                        </span>
                      </td>

                      <td>
                        <span className="transaction-channel">
                          {transaction.channel || "—"}
                        </span>
                      </td>

                      <td>
                        <span
                          className={`transaction-status ${getStatusClass(
                            transaction.status
                          )}`}
                        >
                          {transaction.status}
                        </span>
                      </td>

                      <td>
                        <span className="transaction-time">
                          {formatDateTime(
                            transaction.txn_time
                          )}
                        </span>
                      </td>

                    </tr>
                  );
                })
              ) : (
                <tr>

                  <td
                    colSpan="8"
                    className="transactions-empty"
                  >
                    No transactions found for this account.
                  </td>

                </tr>
              )}

            </tbody>

          </table>

        </div>

      </section>

      {/* =====================================================
          INVESTIGATION ACTIONS
      ====================================================== */}

      <section className="investigation-next-section">

        <div>
          <span className="card-eyebrow">
            INVESTIGATION WORKSPACE
          </span>

          <h2>Continue Investigation</h2>

          <p>
            Use the investigation modules to inspect alerts,
            fraud cases and the movement of funds associated
            with this account.
          </p>
        </div>

        <div className="investigation-action-grid">

          <button
            className="investigation-action"
            onClick={() => navigate("/alerts")}
          >
            <CircleAlert size={18} />

            <span>
              <strong>View Alerts</strong>
              <small>Review risk-triggered alerts</small>
            </span>
          </button>

          <button
            className="investigation-action"
            onClick={() => navigate("/cases")}
          >
            <ShieldAlert size={18} />

            <span>
              <strong>Investigate Cases</strong>
              <small>Review active investigations</small>
            </span>
          </button>

          <button
            className="investigation-action"
            onClick={() =>
              navigate(`/money-flow?account=${accountId}`)
            }
          >
            <ArrowUpRight size={18} />

            <span>
              <strong>Trace Money Flow</strong>
              <small>Follow connected transactions</small>
            </span>
          </button>

        </div>

      </section>

    </div>
  );
}

export default AccountDetails;