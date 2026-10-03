import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  Filter,
  RefreshCw,
  Search,
  ShieldAlert,
  XCircle,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

const STATUS_OPTIONS = [
  "ALL",
  "OPEN",
  "UNDER_REVIEW",
  "RESOLVED",
  "DISMISSED",
];

const LEVEL_OPTIONS = ["ALL", "CRITICAL", "HIGH"];

function formatCurrency(value) {
  const amount = Number(value || 0);

  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function normalizeStatus(status) {
  return String(status || "UNKNOWN").toUpperCase();
}

function normalizeLevel(level) {
  return String(level || "UNKNOWN").toUpperCase();
}

function getStatusIcon(status) {
  switch (status) {
    case "OPEN":
      return <AlertCircle size={14} />;
    case "UNDER_REVIEW":
      return <Clock3 size={14} />;
    case "RESOLVED":
      return <CheckCircle2 size={14} />;
    case "DISMISSED":
      return <XCircle size={14} />;
    default:
      return <ShieldAlert size={14} />;
  }
}

function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 10,
    total_alerts: 0,
    total_pages: 0,
  });

  const [statusFilter, setStatusFilter] = useState("ALL");
  const [levelFilter, setLevelFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const [selectedAlert, setSelectedAlert] = useState(null);
  const [updatingAlertId, setUpdatingAlertId] = useState(null);

  const [page, setPage] = useState(1);
  const pageSize = 10;

  async function loadAlerts(currentPage = page) {
    try {
      setError("");

      if (currentPage === page) {
        setRefreshing(true);
      }

      const params = {
        page: currentPage,
        page_size: pageSize,
      };

      if (statusFilter !== "ALL") {
        params.status = statusFilter;
      }

      if (levelFilter !== "ALL") {
        params.alert_level = levelFilter;
      }

      const response = await axios.get(
        `${API_BASE_URL}/api/alerts`,
        { params }
      );

      const data = response.data;

      setAlerts(Array.isArray(data.alerts) ? data.alerts : []);

      setPagination(
        data.pagination || {
          page: currentPage,
          page_size: pageSize,
          total_alerts: data.alerts?.length || 0,
          total_pages: 1,
        }
      );
    } catch (err) {
      console.error("Failed to load alerts:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to load fraud alerts from the backend."
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadAlerts(page);
  }, [page, statusFilter, levelFilter]);

  function handleStatusFilterChange(value) {
    setStatusFilter(value);
    setPage(1);
  }

  function handleLevelFilterChange(value) {
    setLevelFilter(value);
    setPage(1);
  }

  async function updateAlertStatus(alertId, newStatus) {
    try {
      setUpdatingAlertId(alertId);
      setError("");

      await axios.patch(
        `${API_BASE_URL}/api/alerts/${alertId}/status`,
        {
          status: newStatus,
        }
      );

      await loadAlerts(page);

      if (selectedAlert?.alert_id === alertId) {
        setSelectedAlert((previous) =>
          previous
            ? {
                ...previous,
                alert_status: newStatus,
              }
            : null
        );
      }
    } catch (err) {
      console.error("Failed to update alert:", err);

      setError(
        err.response?.data?.detail ||
          "Unable to update the alert status."
      );
    } finally {
      setUpdatingAlertId(null);
    }
  }

  const filteredAlerts = useMemo(() => {
    const query = search.trim().toLowerCase();

    if (!query) {
      return alerts;
    }

    return alerts.filter((alert) => {
      const searchableText = [
        alert.alert_id,
        alert.account_id,
        alert.account_number,
        alert.customer_name,
        alert.alert_level,
        alert.alert_status,
        alert.alert_message,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return searchableText.includes(query);
    });
  }, [alerts, search]);

  const openCount = alerts.filter(
    (alert) => normalizeStatus(alert.alert_status) === "OPEN"
  ).length;

  const reviewCount = alerts.filter(
    (alert) =>
      normalizeStatus(alert.alert_status) === "UNDER_REVIEW"
  ).length;

  const criticalCount = alerts.filter(
    (alert) => normalizeLevel(alert.alert_level) === "CRITICAL"
  ).length;

  return (
    <div className="alerts-page">

      {/* =====================================================
          PAGE HEADER
          ===================================================== */}

      <div className="alerts-page-header">
        <div>
          <span className="page-eyebrow">FRAUD OPERATIONS</span>

          <h1>Fraud Alerts</h1>

          <p>
            Review risk-triggered alerts and manage investigation status.
          </p>
        </div>

        <button
          className="refresh-button"
          onClick={() => loadAlerts(page)}
          disabled={refreshing}
        >
          <RefreshCw
            size={15}
            className={refreshing ? "spin" : ""}
          />

          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {/* =====================================================
          SUMMARY CARDS
          ===================================================== */}

      <div className="alerts-summary-grid">

        <div className="alerts-summary-card">
          <div className="alerts-summary-icon open">
            <AlertCircle size={19} />
          </div>

          <div>
            <span>Open Alerts</span>
            <strong>{openCount}</strong>
            <small>Require investigation</small>
          </div>
        </div>

        <div className="alerts-summary-card">
          <div className="alerts-summary-icon review">
            <Clock3 size={19} />
          </div>

          <div>
            <span>Under Review</span>
            <strong>{reviewCount}</strong>
            <small>Currently investigated</small>
          </div>
        </div>

        <div className="alerts-summary-card">
          <div className="alerts-summary-icon critical">
            <ShieldAlert size={19} />
          </div>

          <div>
            <span>Critical Alerts</span>
            <strong>{criticalCount}</strong>
            <small>Highest severity</small>
          </div>
        </div>

        <div className="alerts-summary-card">
          <div className="alerts-summary-icon total">
            <Filter size={19} />
          </div>

          <div>
            <span>Total Results</span>
            <strong>{pagination.total_alerts || 0}</strong>
            <small>Matching alerts</small>
          </div>
        </div>

      </div>

      {/* =====================================================
          FILTER BAR
          ===================================================== */}

      <div className="alerts-filter-panel">

        <div className="alerts-search-box">
          <Search size={17} />

          <input
            type="text"
            placeholder="Search alert, account, customer..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>

        <div className="alerts-filter-control">
          <Filter size={15} />

          <select
            value={statusFilter}
            onChange={(event) =>
              handleStatusFilterChange(event.target.value)
            }
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status === "ALL"
                  ? "All statuses"
                  : status.replace("_", " ")}
              </option>
            ))}
          </select>
        </div>

        <div className="alerts-filter-control">
          <ShieldAlert size={15} />

          <select
            value={levelFilter}
            onChange={(event) =>
              handleLevelFilterChange(event.target.value)
            }
          >
            {LEVEL_OPTIONS.map((level) => (
              <option key={level} value={level}>
                {level === "ALL"
                  ? "All severity"
                  : level}
              </option>
            ))}
          </select>
        </div>

      </div>

      {/* =====================================================
          ERROR
          ===================================================== */}

      {error && (
        <div className="alerts-error">
          <AlertCircle size={17} />
          <span>{error}</span>
        </div>
      )}

      {/* =====================================================
          ALERT TABLE
          ===================================================== */}

      <section className="alerts-table-card">

        <div className="alerts-table-header">
          <div>
            <span className="card-eyebrow">RISK MONITORING</span>
            <h2>Alert Registry</h2>
            <p>
              Risk assessments that crossed the configured alert threshold.
            </p>
          </div>

          <span className="alerts-result-count">
            {filteredAlerts.length} shown
          </span>
        </div>

        {loading ? (
          <div className="alerts-loading">
            <RefreshCw size={20} className="spin" />
            <span>Loading fraud alerts...</span>
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="alerts-empty">
            <CheckCircle2 size={30} />
            <h3>No alerts found</h3>
            <p>
              No fraud alerts match the current filters.
            </p>
          </div>
        ) : (
          <div className="alerts-table-wrapper">

            <table className="alerts-table">

              <thead>
                <tr>
                  <th>ALERT</th>
                  <th>ACCOUNT</th>
                  <th>SEVERITY</th>
                  <th>RISK SCORE</th>
                  <th>STATUS</th>
                  <th>MESSAGE</th>
                  <th>CREATED</th>
                  <th>ACTION</th>
                </tr>
              </thead>

              <tbody>
                {filteredAlerts.map((alert) => {
                  const status = normalizeStatus(
                    alert.alert_status
                  );

                  const level = normalizeLevel(
                    alert.alert_level
                  );

                  return (
                    <tr key={alert.alert_id}>

                      <td>
                        <span className="alert-id">
                          #{alert.alert_id}
                        </span>
                      </td>

                      <td>
                        <div className="alert-account-cell">
                          <strong>
                            {alert.account_number ||
                              `Account #${alert.account_id}`}
                          </strong>

                          <span>
                            Account #{alert.account_id}
                          </span>
                        </div>
                      </td>

                      <td>
                        <span
                          className={`alert-level-badge ${level.toLowerCase()}`}
                        >
                          {level}
                        </span>
                      </td>

                      <td>
                        <strong className="alert-risk-score">
                          {alert.risk_score ?? "—"}
                        </strong>
                      </td>

                      <td>
                        <span
                          className={`alert-status-badge ${status.toLowerCase()}`}
                        >
                          {getStatusIcon(status)}
                          {status.replace("_", " ")}
                        </span>
                      </td>

                      <td>
                        <span className="alert-message-cell">
                          {alert.alert_message || "No message available"}
                        </span>
                      </td>

                      <td>
                        <span className="alert-date">
                          {formatDate(alert.created_at)}
                        </span>
                      </td>

                      <td>
                        <button
                          className="alert-review-button"
                          onClick={() => setSelectedAlert(alert)}
                        >
                          Review
                        </button>
                      </td>

                    </tr>
                  );
                })}
              </tbody>

            </table>

          </div>
        )}

        {/* =================================================
            PAGINATION
            ================================================= */}

        {!loading && pagination.total_pages > 0 && (
          <div className="alerts-pagination">

            <span>
              Page {pagination.page} of{" "}
              {pagination.total_pages}
            </span>

            <div>
              <button
                disabled={page <= 1}
                onClick={() => setPage((current) => current - 1)}
              >
                Previous
              </button>

              <button
                disabled={
                  page >= pagination.total_pages
                }
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </button>
            </div>

          </div>
        )}

      </section>

      {/* =====================================================
          ALERT REVIEW PANEL
          ===================================================== */}

      {selectedAlert && (
        <div
          className="alert-modal-backdrop"
          onClick={() => setSelectedAlert(null)}
        >

          <aside
            className="alert-review-panel"
            onClick={(event) => event.stopPropagation()}
          >

            <div className="alert-review-header">

              <div>
                <span className="page-eyebrow">
                  ALERT INVESTIGATION
                </span>

                <h2>
                  Alert #{selectedAlert.alert_id}
                </h2>
              </div>

              <button
                className="alert-close-button"
                onClick={() => setSelectedAlert(null)}
              >
                <XCircle size={20} />
              </button>

            </div>

            <div className="alert-review-risk">

              <div>
                <span>RISK SCORE</span>
                <strong>
                  {selectedAlert.risk_score ?? "—"}
                </strong>
              </div>

              <span
                className={`alert-level-badge ${
                  normalizeLevel(
                    selectedAlert.alert_level
                  ).toLowerCase()
                }`}
              >
                {normalizeLevel(
                  selectedAlert.alert_level
                )}
              </span>

            </div>

            <div className="alert-review-section">

              <span>ACCOUNT</span>

              <strong>
                {selectedAlert.account_number ||
                  `Account #${selectedAlert.account_id}`}
              </strong>

              <small>
                Account #{selectedAlert.account_id}
              </small>

            </div>

            <div className="alert-review-section">

              <span>ALERT MESSAGE</span>

              <p>
                {selectedAlert.alert_message ||
                  "No alert message available."}
              </p>

            </div>

            <div className="alert-review-section">

              <span>CREATED</span>

              <p>
                {formatDate(selectedAlert.created_at)}
              </p>

            </div>

            <div className="alert-review-section">

              <span>UPDATE STATUS</span>

              <div className="alert-status-actions">

                {STATUS_OPTIONS
                  .filter((status) => status !== "ALL")
                  .map((status) => (
                    <button
                      key={status}
                      disabled={
                        updatingAlertId ===
                        selectedAlert.alert_id
                      }
                      className={
                        normalizeStatus(
                          selectedAlert.alert_status
                        ) === status
                          ? "active"
                          : ""
                      }
                      onClick={() =>
                        updateAlertStatus(
                          selectedAlert.alert_id,
                          status
                        )
                      }
                    >
                      {status.replace("_", " ")}
                    </button>
                  ))}

              </div>

            </div>

          </aside>

        </div>
      )}

    </div>
  );
}

export default Alerts;