import { useEffect, useMemo, useState } from "react";
import { addCaseNote, closeCase } from "../services/api";
import {
  BriefcaseBusiness,
  CheckCircle2,
  Clock3,
  AlertTriangle,
  Search,
  RefreshCw,
  Filter,
  ChevronRight,
  ShieldAlert,
  X,
  UserRound,
  IndianRupee,
  Activity,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

const STATUS_OPTIONS = [
  "ALL",
  "OPEN",
  "UNDER_REVIEW",
  "ESCALATED",
  "CLOSED",
];

const PRIORITY_OPTIONS = [
  "ALL",
  "LOW",
  "MEDIUM",
  "HIGH",
  "CRITICAL",
];

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

  return date.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatStatus(value) {
  if (!value) return "UNKNOWN";

  return value
    .replaceAll("_", " ")
    .toLowerCase()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function statusClass(status) {
  switch (status) {
    case "OPEN":
      return "case-status case-status-open";

    case "UNDER_REVIEW":
      return "case-status case-status-review";

    case "ESCALATED":
      return "case-status case-status-escalated";

    case "CLOSED":
      return "case-status case-status-closed";

    default:
      return "case-status";
  }
}

function priorityClass(priority) {
  switch (priority) {
    case "CRITICAL":
      return "priority-badge priority-critical";

    case "HIGH":
      return "priority-badge priority-high";

    case "MEDIUM":
      return "priority-badge priority-medium";

    case "LOW":
      return "priority-badge priority-low";

    default:
      return "priority-badge";
  }
}

function getCaseArray(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }

  if (Array.isArray(payload?.cases)) {
    return payload.cases;
  }

  if (Array.isArray(payload?.data)) {
    return payload.data;
  }

  return [];
}

function Cases() {
  const [cases, setCases] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    page_size: 10,
    total_cases: 0,
    total_pages: 0,
  });

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [priorityFilter, setPriorityFilter] = useState("ALL");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedCase, setSelectedCase] = useState(null);
  const [loadingCase, setLoadingCase] = useState(false);

  const [showOpenCase, setShowOpenCase] = useState(false);

  const [newCase, setNewCase] = useState({
    alert_id: "",
    investigator_id: "",
    case_title: "",
    case_description: "",
    priority: "MEDIUM",
  });

  const [openingCase, setOpeningCase] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);
  const [closureReason, setClosureReason] = useState("");
  const [closingCase, setClosingCase] = useState(false);
  async function fetchCases() {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams();

      params.set("page", pagination.page);
      params.set("page_size", pagination.page_size);

      if (search.trim()) {
        params.set("search", search.trim());
      }

      if (statusFilter !== "ALL") {
        params.set("status", statusFilter);
      }

      if (priorityFilter !== "ALL") {
        params.set("priority", priorityFilter);
      }

      const response = await fetch(
        `${API_BASE_URL}/api/cases?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error(`Failed to load cases (${response.status})`);
      }

      const data = await response.json();

      setCases(getCaseArray(data));

      if (data?.pagination) {
        setPagination((current) => ({
          ...current,
          ...data.pagination,
        }));
      }
    } catch (err) {
      console.error(err);
      setError("Unable to load fraud cases from the backend.");
      setCases([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchCases();
  }, [
    pagination.page,
    pagination.page_size,
    search,
    statusFilter,
    priorityFilter,
  ]);

  async function handleViewCase(caseId) {
    setLoadingCase(true);
    setError("");

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/cases/${caseId}`
      );

      if (!response.ok) {
        throw new Error("Failed to retrieve case.");
      }

      const data = await response.json();

      setSelectedCase(data);
    } catch (err) {
      console.error(err);
      setError("Unable to retrieve the selected case.");
    } finally {
      setLoadingCase(false);
    }
  }

async function handleAddNote(event) {
  event.preventDefault();

  if (!selectedCase?.case?.case_id || !noteText.trim()) {
    return;
  }

  setAddingNote(true);
  setError("");

  try {
    await addCaseNote(
      selectedCase.case.case_id,
      selectedCase.case.investigator_id,
      noteText.trim()
    );

    setNoteText("");

    // Reload the case so the new note appears immediately
    await handleViewCase(selectedCase.case.case_id);
  } catch (err) {
    console.error(err);
    setError(
      err?.response?.data?.detail ||
        "Unable to add investigation note."
    );
  } finally {
    setAddingNote(false);
  }
}

async function handleCloseCase(event) {
  event.preventDefault();

  if (!selectedCase?.case?.case_id || !closureReason.trim()) return;

  setClosingCase(true);
  setError("");

  try {
    await closeCase(
      selectedCase.case.case_id,
      selectedCase.case.investigator_id,
      closureReason.trim()
    );

    setClosureReason("");

    await handleViewCase(selectedCase.case.case_id);
    await fetchCases();
  } catch (err) {
    console.error(err);
    setError(
      err?.response?.data?.detail || "Unable to close fraud case."
    );
  } finally {
    setClosingCase(false);
  }
}  
  

  async function handleOpenCase(event) {
    event.preventDefault();

    if (
  !newCase.alert_id ||
  !newCase.investigator_id ||
  !newCase.case_title
) {
  setActionMessage(
    "Alert ID, Investigator ID and case title are required."
  );
  return;
}

    setOpeningCase(true);
    setActionMessage("");

    try {
      const payload = {
  alert_id: Number(newCase.alert_id),
  investigator_id: Number(newCase.investigator_id),
  case_title: newCase.case_title,
  case_description: newCase.case_description || null,
  priority: newCase.priority,
};

      const response = await fetch(`${API_BASE_URL}/api/cases`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data?.detail || "Failed to open fraud case."
        );
      }

      setActionMessage("Fraud case opened successfully.");

      setNewCase({
        alert_id: "",
        investigator_id: "",
        case_title: "",
        case_description: "",
        priority: "MEDIUM",
      });

      setShowOpenCase(false);

      await fetchCases();
    } catch (err) {
      console.error(err);
      setActionMessage(err.message || "Unable to open fraud case.");
    } finally {
      setOpeningCase(false);
    }
  }

  const statistics = useMemo(() => {
    return {
      total: cases.length,

      open: cases.filter(
        (item) => item.case_status === "OPEN"
      ).length,

      underReview: cases.filter(
        (item) => item.case_status === "UNDER_REVIEW"
      ).length,

      escalated: cases.filter(
        (item) => item.case_status === "ESCALATED"
      ).length,

      critical: cases.filter(
        (item) => item.priority === "CRITICAL"
      ).length,
    };
  }, [cases]);

  const visibleCases = useMemo(() => {
    const term = search.trim().toLowerCase();

    if (!term) {
      return cases;
    }

    return cases.filter((item) => {
      return (
        String(item.case_id || "")
          .toLowerCase()
          .includes(term) ||
        String(item.case_title || "")
          .toLowerCase()
          .includes(term) ||
        String(item.account_number || "")
          .toLowerCase()
          .includes(term) ||
        String(item.investigator_name || "")
          .toLowerCase()
          .includes(term)
      );
    });
  }, [cases, search]);

  return (
    <section className="cases-page">
      {/* PAGE HEADER */}
      <div className="page-header">
        <div>
          <p className="page-eyebrow">INVESTIGATION OPERATIONS</p>

          <h1>Fraud Cases</h1>

          <p className="page-description">
            Manage fraud investigations, investigators, suspicious
            transactions and case lifecycle activity.
          </p>
        </div>

        <div className="page-header-actions">
          <button
            className="secondary-button"
            onClick={fetchCases}
            disabled={loading}
          >
            <RefreshCw
              size={16}
              className={loading ? "spin" : ""}
            />

            Refresh
          </button>

          <button
            className="primary-button"
            onClick={() => {
              setActionMessage("");
              setShowOpenCase(true);
            }}
          >
            <BriefcaseBusiness size={17} />

            Open Case
          </button>
        </div>
      </div>

      {/* ERROR */}
      {error && (
        <div className="page-error">
          <AlertTriangle size={18} />

          <span>{error}</span>
        </div>
      )}

      {/* STATISTICS */}
      <div className="stats-grid cases-stats">
        <div className="stat-card">
          <div className="stat-icon stat-icon-blue">
            <BriefcaseBusiness size={21} />
          </div>

          <div>
            <span>Total Cases</span>
            <strong>{pagination.total_cases || statistics.total}</strong>
            <small>Recorded investigations</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-red">
            <ShieldAlert size={21} />
          </div>

          <div>
            <span>Open Cases</span>
            <strong>{statistics.open}</strong>
            <small>Require investigation</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-yellow">
            <Clock3 size={21} />
          </div>

          <div>
            <span>Under Review</span>
            <strong>{statistics.underReview}</strong>
            <small>Currently investigated</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-orange">
            <Activity size={21} />
          </div>

          <div>
            <span>Escalated</span>
            <strong>{statistics.escalated}</strong>
            <small>Require escalation</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon stat-icon-purple">
            <AlertTriangle size={21} />
          </div>

          <div>
            <span>Critical Priority</span>
            <strong>{statistics.critical}</strong>
            <small>Highest investigation priority</small>
          </div>
        </div>
      </div>

      {/* FILTER BAR */}
      <div className="filter-panel">
        <div className="search-control">
          <Search size={18} />

          <input
            type="text"
            placeholder="Search case, account or investigator..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPagination((current) => ({
                ...current,
                page: 1,
              }));
            }}
          />
        </div>

        <div className="select-control">
          <Filter size={17} />

          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value);

              setPagination((current) => ({
                ...current,
                page: 1,
              }));
            }}
          >
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status === "ALL"
                  ? "All statuses"
                  : formatStatus(status)}
              </option>
            ))}
          </select>
        </div>

        <div className="select-control">
          <ShieldAlert size={17} />

          <select
            value={priorityFilter}
            onChange={(event) => {
              setPriorityFilter(event.target.value);

              setPagination((current) => ({
                ...current,
                page: 1,
              }));
            }}
          >
            {PRIORITY_OPTIONS.map((priority) => (
              <option key={priority} value={priority}>
                {priority === "ALL"
                  ? "All priorities"
                  : formatStatus(priority)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* CASE REGISTRY */}
      <div className="content-card cases-registry">
        <div className="content-card-header">
          <div>
            <p className="section-eyebrow">INVESTIGATION WORKSPACE</p>

            <h2>Case Registry</h2>

            <p>
              Fraud cases generated from risk alerts and analyst
              investigations.
            </p>
          </div>

          <span className="result-count">
            {visibleCases.length} shown
          </span>
        </div>

        {loading ? (
          <div className="empty-state">
            <RefreshCw size={24} className="spin" />

            <strong>Loading investigations...</strong>

            <span>
              Retrieving fraud case information from PostgreSQL.
            </span>
          </div>
        ) : visibleCases.length === 0 ? (
          <div className="empty-state">
            <CheckCircle2 size={28} />

            <strong>No fraud cases found</strong>

            <span>
              Try changing the search or filters, or open a new
              investigation.
            </span>
          </div>
        ) : (
          <div className="table-wrapper">
            <table className="data-table cases-table">
              <thead>
                <tr>
                  <th>CASE</th>
                  <th>ACCOUNT</th>
                  <th>INVESTIGATOR</th>
                  <th>PRIORITY</th>
                  <th>STATUS</th>
                  <th>TRANSACTIONS</th>
                  <th>SUSPICIOUS AMOUNT</th>
                  <th>OPENED</th>
                  <th>ACTION</th>
                </tr>
              </thead>

              <tbody>
                {visibleCases.map((item) => (
                  <tr key={item.case_id}>
                    <td>
                      <div className="case-identity">
                        <div className="case-number">
                          #{item.case_id}
                        </div>

                        <div>
                          <strong>
                            {item.case_title || "Untitled case"}
                          </strong>

                          <small>
                            {item.case_description
                              ? item.case_description.slice(0, 55)
                              : "No description provided"}
                          </small>
                        </div>
                      </div>
                    </td>

                    <td>
                      <div className="account-cell">
                        <strong>
                          {item.account_number ||
                            `Account #${item.account_id}`}
                        </strong>

                        <small>
                          Account #{item.account_id}
                        </small>
                      </div>
                    </td>

                    <td>
                      <div className="investigator-cell">
                        <UserRound size={16} />

                        <span>
                          {item.investigator_name ||
                            "Unassigned"}
                        </span>
                      </div>
                    </td>

                    <td>
                      <span className={priorityClass(item.priority)}>
                        {item.priority || "—"}
                      </span>
                    </td>

                    <td>
                      <span className={statusClass(item.case_status)}>
                        {formatStatus(item.case_status)}
                      </span>
                    </td>

                    <td>
                      <span className="metric-value">
                        {item.linked_transaction_count ??
                          item.transaction_count ??
                          0}
                      </span>
                    </td>

                    <td>
                      <div className="amount-cell">
                        <IndianRupee size={14} />

                        {formatCurrency(
                          item.total_suspicious_amount ??
                            item.suspicious_amount ??
                            0
                        )}
                      </div>
                    </td>

                    <td>
                      {formatDate(item.opened_at)}
                    </td>

                    <td>
                      <button
                        className="table-action-button"
                        onClick={() =>
                          handleViewCase(item.case_id)
                        }
                      >
                        Review

                        <ChevronRight size={15} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* PAGINATION */}
        {pagination.total_pages > 1 && (
          <div className="pagination">
            <button
              disabled={pagination.page <= 1}
              onClick={() =>
                setPagination((current) => ({
                  ...current,
                  page: current.page - 1,
                }))
              }
            >
              Previous
            </button>

            <span>
              Page {pagination.page} of{" "}
              {pagination.total_pages}
            </span>

            <button
              disabled={
                pagination.page >= pagination.total_pages
              }
              onClick={() =>
                setPagination((current) => ({
                  ...current,
                  page: current.page + 1,
                }))
              }
            >
              Next
            </button>
          </div>
        )}
      </div>

      {/* CASE DETAIL MODAL */}
      {selectedCase && (
        <div
          className="modal-backdrop"
          onClick={() => setSelectedCase(null)}
        >
          <div
            className="case-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <p className="section-eyebrow">
                  CASE INVESTIGATION
                </p>

                <h2>
                  #{selectedCase.case?.case_id}{" "}
                  {selectedCase.case?.case_title}
                </h2>

                <p>
                  Investigation workspace with linked transaction
                  evidence and case audit history.
                </p>
              </div>

              <button
                className="icon-button"
                onClick={() => setSelectedCase(null)}
                aria-label="Close case investigation"
              >
                <X size={20} />
              </button>
            </div>

            {loadingCase ? (
              <div className="modal-loading">
                <RefreshCw size={24} className="spin" />
                Loading case intelligence...
              </div>
            ) : (
              <div className="case-detail-grid">
                {/* CASE OVERVIEW */}
                <div className="detail-item">
                  <span>Status</span>

                  <strong>
                    {formatStatus(selectedCase.case?.case_status)}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Priority</span>

                  <strong>
                    {selectedCase.case?.priority || "—"}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Account</span>

                  <strong>
                    {selectedCase.case?.account_number ||
                      `#${selectedCase.case?.account_id}`}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Investigator</span>

                  <strong>
                    {selectedCase.case?.investigator_name ||
                      "Unassigned"}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Opened</span>

                  <strong>
                    {formatDate(selectedCase.case?.opened_at)}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Closed</span>

                  <strong>
                    {formatDate(selectedCase.case?.closed_at)}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Linked Transactions</span>

                  <strong>
                    {selectedCase.transactions?.length || 0}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Suspicious Amount</span>

                  <strong>
                    {formatCurrency(
                      selectedCase.case?.suspicious_amount || 0
                    )}
                  </strong>
                </div>

                <div className="detail-item">
                  <span>Fraud Alert</span>

                  <strong>
                    {selectedCase.case?.alert_id
                      ? `Alert #${selectedCase.case.alert_id}`
                      : "No alert linked"}
                  </strong>
                </div>

                {/* DESCRIPTION */}
                <div className="detail-item detail-wide">
                  <span>Description</span>

                  <p>
                    {selectedCase.case?.case_description ||
                      "No case description provided."}
                  </p>
                </div>

                {/* LINKED TRANSACTIONS */}
                <div className="detail-item detail-wide">
                  <div className="content-card-header">
                    <div>
                      <p className="section-eyebrow">
                        EVIDENCE
                      </p>

                      <h2>Linked Transactions</h2>

                      <p>
                        Transactions associated with this fraud
                        investigation.
                      </p>
                    </div>

                    <span className="result-count">
                      {selectedCase.transactions?.length || 0} linked
                    </span>
                  </div>

                  {selectedCase.transactions?.length > 0 ? (
                    <div className="table-wrapper">
                      <table className="data-table cases-table">
                        <thead>
                          <tr>
                            <th>TXN ID</th>
                            <th>FLOW</th>
                            <th>AMOUNT</th>
                            <th>TIME</th>
                            <th>CHANNEL</th>
                            <th>STATUS</th>
                          </tr>
                        </thead>

                        <tbody>
                          {selectedCase.transactions.map(
                            (transaction) => (
                              <tr
                                key={transaction.transaction_id}
                              >
                                <td>
                                  <span className="metric-value">
                                    #{transaction.transaction_id}
                                  </span>
                                </td>

                                <td>
                                  <div className="investigator-cell">
                                    <span>
                                      Account #
                                      {transaction.sender_account_id}
                                    </span>

                                    <ChevronRight size={14} />

                                    <span>
                                      Account #
                                      {transaction.receiver_account_id}
                                    </span>
                                  </div>
                                </td>

                                <td>
                                  <div className="amount-cell">
                                    <IndianRupee size={14} />

                                    {formatCurrency(
                                      transaction.amount
                                    )}
                                  </div>
                                </td>

                                <td>
                                  {new Date(
                                    transaction.txn_time
                                  ).toLocaleString("en-IN", {
                                    day: "2-digit",
                                    month: "short",
                                    year: "numeric",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </td>

                                <td>
                                  {transaction.channel || "—"}
                                </td>

                                <td>
                                  <span className="case-status case-status-closed">
                                    {transaction.status || "UNKNOWN"}
                                  </span>
                                </td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>

                      <div className="form-message">
                        <strong>Link reason:</strong>{" "}
                        {selectedCase.transactions[0]?.link_reason ||
                          "No link reason recorded."}
                      </div>
                    </div>
                  ) : (
                    <div className="empty-state">
                      <CheckCircle2 size={24} />

                      <strong>
                        No linked transactions
                      </strong>

                      <span>
                        No transactions are currently associated
                        with this case.
                      </span>
                    </div>
                  )}
                </div>

                {/* INVESTIGATOR NOTES */}
                <div className="detail-item detail-wide">
                  <div className="content-card-header">
                    <div>
                      <p className="section-eyebrow">
                        INVESTIGATION RECORD
                      </p>

                      <h2>Investigator Notes</h2>

                      <p>
                        Analyst observations recorded during the
                        investigation.
                      </p>
                    </div>

                    <span className="result-count">
                      {selectedCase.notes?.length || 0} notes
                    </span>
                  </div>

                  {selectedCase.notes?.length > 0 ? (
                    <div>
                      {selectedCase.notes.map((note) => (
                        <div
                          className="detail-item"
                          key={note.note_id}
                          style={{ marginBottom: "10px" }}
                        >
                          <span>
                            {note.investigator_name ||
                              "Investigator"}{" "}
                            • {formatDate(note.created_at)}
                          </span>

                          <p>
                            {note.note_text}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="empty-state">
                      <UserRound size={24} />

                      <strong>
                        No investigator notes recorded
                      </strong>

                      <span>
                        Notes can be added as the investigation
                        progresses.
                      </span>
                    </div>
                  )}
                </div>
                {/* ADD INVESTIGATION NOTE */}
<form
  className="case-form"
  onSubmit={handleAddNote}
  style={{ marginTop: "16px" }}
>
  <label className="form-wide">
    Add Investigation Note

    <textarea
      rows="4"
      value={noteText}
      onChange={(event) => setNoteText(event.target.value)}
      placeholder="Record an investigation observation, finding, or follow-up action..."
      maxLength={5000}
      required
    />
  </label>

  <div className="modal-actions">
    <button
      type="submit"
      className="primary-button"
      disabled={addingNote || !noteText.trim()}
    >
      {addingNote ? (
        <>
          <RefreshCw size={16} className="spin" />
          Adding Note...
        </>
      ) : (
        "Add Note"
      )}
    </button>
  </div>
</form>

{selectedCase.case?.case_status !== "CLOSED" && (
  <form
    className="case-form"
    onSubmit={handleCloseCase}
    style={{ marginTop: "16px" }}
  >
    <label className="form-wide">
      Closure Reason
      <textarea
        rows="4"
        value={closureReason}
        onChange={(event) => setClosureReason(event.target.value)}
        placeholder="Explain why this fraud case is being closed..."
        maxLength={5000}
        required
      />
    </label>

    <div className="modal-actions">
      <button
        type="submit"
        className="primary-button"
        disabled={closingCase || !closureReason.trim()}
      >
        {closingCase ? (
          <>
            <RefreshCw size={16} className="spin" />
            Closing Case...
          </>
        ) : (
          "Close Case"
        )}
      </button>
    </div>
  </form>
)}
                  
                {/* STATUS HISTORY */}
                <div className="detail-item detail-wide">
                  <div className="content-card-header">
                    <div>
                      <p className="section-eyebrow">
                        AUDIT TRAIL
                      </p>

                      <h2>Status History</h2>

                      <p>
                        Chronological record of case lifecycle
                        transitions.
                      </p>
                    </div>

                    <span className="result-count">
                      {selectedCase.status_history?.length || 0} events
                    </span>
                  </div>

                  {selectedCase.status_history?.length > 0 ? (
                    <div className="table-wrapper">
                      <table className="data-table cases-table">
                        <thead>
                          <tr>
                            <th>FROM</th>
                            <th>TO</th>
                            <th>CHANGED BY</th>
                            <th>TIME</th>
                            <th>REASON</th>
                          </tr>
                        </thead>

                        <tbody>
                          {selectedCase.status_history.map(
                            (history) => (
                              <tr key={history.history_id}>
                                <td>
                                  <span className="case-status case-status-closed">
                                    {formatStatus(
                                      history.old_status || "INITIAL"
                                    )}
                                  </span>
                                </td>

                                <td>
                                  <span
                                    className={statusClass(
                                      history.new_status
                                    )}
                                  >
                                    {formatStatus(
                                      history.new_status
                                    )}
                                  </span>
                                </td>

                                <td>
                                  <div className="investigator-cell">
                                    <UserRound size={15} />

                                    <span>
                                      {history.investigator_name ||
                                        "System"}
                                    </span>
                                  </div>
                                </td>

                                <td>
                                  {new Date(
                                    history.changed_at
                                  ).toLocaleString("en-IN", {
                                    day: "2-digit",
                                    month: "short",
                                    year: "numeric",
                                    hour: "2-digit",
                                    minute: "2-digit",
                                  })}
                                </td>

                                <td>
                                  {history.change_reason || "—"}
                                </td>
                              </tr>
                            )
                          )}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="empty-state">
                      <Clock3 size={24} />

                      <strong>
                        No status history available
                      </strong>

                      <span>
                        Case lifecycle events will appear here.
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* OPEN CASE MODAL */}
      {showOpenCase && (
        <div
          className="modal-backdrop"
          onClick={() => setShowOpenCase(false)}
        >
          <div
            className="case-modal open-case-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-header">
              <div>
                <p className="section-eyebrow">
                  INVESTIGATION WORKFLOW
                </p>

                <h2>Open Fraud Case</h2>

                <p>
                  Create an investigation using the existing
                  PostgreSQL case procedure.
                </p>
              </div>

              <button
                className="icon-button"
                onClick={() => setShowOpenCase(false)}
              >
                <X size={20} />
              </button>
            </div>

            <form
              className="case-form"
              onSubmit={handleOpenCase}
            >
              <div className="form-grid">
                
                <label>
                  Alert ID
                  <input
                    type="number"
                    min="1"
                    value={newCase.alert_id}
                    onChange={(event) =>
                      setNewCase((current) => ({
                        ...current,
                        alert_id: event.target.value,
                      }))
                    }
                    placeholder="Example: 2"
                    required
                  />
                </label>

                <label>
                  Investigator ID
                  <input
                    type="number"
                    min="1"
                    value={newCase.investigator_id}
                    onChange={(event) =>
                      setNewCase((current) => ({
                        ...current,
                        investigator_id:
                          event.target.value,
                      }))
                    }
                    placeholder="Example: 1"
                    required
                  />
                </label>

                <label>
                  Priority
                  <select
                    value={newCase.priority}
                    onChange={(event) =>
                      setNewCase((current) => ({
                        ...current,
                        priority: event.target.value,
                      }))
                    }
                  >
                    {PRIORITY_OPTIONS.filter(
                      (item) => item !== "ALL"
                    ).map((priority) => (
                      <option
                        key={priority}
                        value={priority}
                      >
                        {priority}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="form-wide">
                  Case Title
                  <input
                    type="text"
                    value={newCase.case_title}
                    onChange={(event) =>
                      setNewCase((current) => ({
                        ...current,
                        case_title: event.target.value,
                      }))
                    }
                    placeholder="Example: Suspicious Rapid Fund Movement"
                    required
                  />
                </label>

                <label className="form-wide">
                  Case Description
                  <textarea
                    rows="5"
                    value={newCase.case_description}
                    onChange={(event) =>
                      setNewCase((current) => ({
                        ...current,
                        case_description:
                          event.target.value,
                      }))
                    }
                    placeholder="Describe the suspicious activity and investigation context..."
                  />
                </label>
              </div>

              {actionMessage && (
                <div className="form-message">
                  {actionMessage}
                </div>
              )}

              <div className="modal-actions">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => setShowOpenCase(false)}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={openingCase}
                >
                  {openingCase ? (
                    <>
                      <RefreshCw
                        size={16}
                        className="spin"
                      />

                      Opening...
                    </>
                  ) : (
                    <>
                      <BriefcaseBusiness size={17} />

                      Open Investigation
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </section>
  );
}

export default Cases;