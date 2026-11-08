import { useEffect, useState } from "react";
import axios from "axios";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  GitBranch,
  RefreshCw,
  ShieldAlert,
  WalletCards,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

const INVESTIGATOR_ID = 1;

function formatCurrency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function formatDate(value) {
  if (!value) return "—";

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("en-IN");
}

function InvestigationWorkspace() {
  const params = new URLSearchParams(window.location.search);

  const accountId = params.get("account_id");

  const [timeline, setTimeline] = useState(null);
  const [network, setNetwork] = useState(null);
  const [moneyFlow, setMoneyFlow] = useState(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedTransaction, setSelectedTransaction] =
    useState(null);

  const [findingType, setFindingType] =
    useState("INCONCLUSIVE");

  const [finding, setFinding] = useState("");

  const [closureReason, setClosureReason] =
    useState("");

  const [actionMessage, setActionMessage] =
    useState("");

  async function loadWorkspace() {
    if (!accountId) {
      setError(
        "No account selected. Use /investigation?account_id=..."
      );
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError("");

      const [
        timelineResponse,
        networkResponse,
        moneyFlowResponse,
      ] = await Promise.all([
        axios.get(
          `${API_BASE_URL}/api/investigation/account/${accountId}/timeline`
        ),
        axios.get(
          `${API_BASE_URL}/api/investigation/network/account/${accountId}`,
          {
            params: {
              max_depth: 2,
            },
          }
        ),
        axios.get(
          `${API_BASE_URL}/api/money-flow/${accountId}/investigation`,
          {
            params: {
              max_depth: 3,
            },
          }
        ),
      ]);

      setTimeline(timelineResponse.data);
      setNetwork(networkResponse.data);
      setMoneyFlow(moneyFlowResponse.data);
    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
          "Unable to load investigation workspace."
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadWorkspace();
  }, [accountId]);

  async function saveFinding() {
    if (!timeline?.cases?.length) {
      setActionMessage("No case is linked to this account.");
      return;
    }

    const activeCase =
      timeline.cases.find(
        (item) => item.case_status !== "CLOSED"
      ) || timeline.cases[0];

    if (!finding.trim()) {
      setActionMessage("Enter an investigation finding.");
      return;
    }

    try {
      setActionMessage("");

      await axios.post(
        `${API_BASE_URL}/api/investigation/case/${activeCase.case_id}/finding`,
        {
          investigator_id: INVESTIGATOR_ID,
          finding_type: findingType,
          finding: finding.trim(),
        }
      );

      setActionMessage(
        "Investigation finding recorded successfully."
      );

      setFinding("");

      await loadWorkspace();
    } catch (err) {
      setActionMessage(
        err.response?.data?.detail ||
          "Unable to record finding."
      );
    }
  }

  async function closeCase() {
    if (!timeline?.cases?.length) {
      setActionMessage("No case is linked to this account.");
      return;
    }

    const activeCase = timeline.cases.find(
      (item) => item.case_status !== "CLOSED"
    );

    if (!activeCase) {
      setActionMessage("There is no open case.");
      return;
    }

    if (!finding.trim() || !closureReason.trim()) {
      setActionMessage(
        "Enter both the final finding and closure reason."
      );
      return;
    }

    try {
      setActionMessage("");

      await axios.patch(
        `${API_BASE_URL}/api/investigation/case/${activeCase.case_id}/decision`,
        {
          investigator_id: INVESTIGATOR_ID,
          finding_type: findingType,
          finding: finding.trim(),
          closure_reason: closureReason.trim(),
        }
      );

      setActionMessage(
        "Case decision recorded and case closed."
      );

      setFinding("");
      setClosureReason("");

      await loadWorkspace();
    } catch (err) {
      setActionMessage(
        err.response?.data?.detail ||
          "Unable to close case."
      );
    }
  }

  if (loading) {
    return (
      <div className="investigation-state">
        <RefreshCw className="spin" size={24} />
        <p>Loading investigation workspace...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="investigation-state">
        <AlertTriangle size={25} />
        <h3>Investigation unavailable</h3>
        <p>{error}</p>
        <button onClick={loadWorkspace}>
          Retry
        </button>
      </div>
    );
  }

  const account = timeline?.account;
  const summary = timeline?.investigation_summary || {};

  const highestRisk =
    timeline?.risk_assessments?.length
      ? timeline.risk_assessments.reduce(
          (highest, current) =>
            Number(current.risk_score) >
            Number(highest.risk_score)
              ? current
              : highest
        )
      : null;

  const activeCase =
    timeline?.cases?.find(
      (item) => item.case_status !== "CLOSED"
    ) || null;

  return (
    <section className="investigation-workspace">

      {/* =====================================================
          HEADER
      ===================================================== */}

      <div className="investigation-header">
        <div>
          <span className="page-eyebrow">
            FRAUD INVESTIGATION
          </span>

          <h1>
            {account?.account_number ||
              `Account #${accountId}`}
          </h1>

          <p>
            Investigation workspace for connected activity,
            risk evidence and case review.
          </p>
        </div>

        <button
          className="secondary-button"
          onClick={loadWorkspace}
        >
          <RefreshCw size={15} />
          Refresh
        </button>
      </div>

      {/* =====================================================
          SUMMARY
      ===================================================== */}

      <div className="investigation-kpis">

        <div className="investigation-kpi">
          <span>TRANSACTIONS</span>
          <strong>
            {summary.transaction_count || 0}
          </strong>
        </div>

        <div className="investigation-kpi">
          <span>RISK ASSESSMENTS</span>
          <strong>
            {summary.risk_assessment_count || 0}
          </strong>
        </div>

        <div className="investigation-kpi">
          <span>ALERTS</span>
          <strong>
            {summary.alert_count || 0}
          </strong>
        </div>

        <div className="investigation-kpi">
          <span>CASES</span>
          <strong>
            {summary.case_count || 0}
          </strong>
        </div>

        <div className="investigation-kpi">
          <span>RISK SCORE</span>
          <strong>
            {highestRisk
              ? Number(
                  highestRisk.risk_score
                ).toFixed(1)
              : "—"}
          </strong>
        </div>

      </div>

      {/* =====================================================
          RISK
      ===================================================== */}

      <div className="investigation-grid">

        <div className="investigation-card">

          <div className="investigation-card-header">
            <div>
              <span>AI RISK ASSESSMENT</span>
              <h2>Risk Intelligence</h2>
            </div>

            <ShieldAlert size={20} />
          </div>

          {highestRisk ? (
            <div className="risk-evidence">

              <div className="risk-score-large">
                {Number(
                  highestRisk.risk_score
                ).toFixed(1)}
              </div>

              <div>
                <strong>
                  {highestRisk.risk_level}
                </strong>

                <p>
                  Model:{" "}
                  {highestRisk.model_version}
                </p>

                <p>
                  {highestRisk.reason ||
                    "No explanation recorded."}
                </p>
              </div>

            </div>
          ) : (
            <p>No risk assessment available.</p>
          )}

        </div>

        {/* NETWORK */}

        <div className="investigation-card">

          <div className="investigation-card-header">
            <div>
              <span>ACCOUNT NETWORK</span>
              <h2>Connected Accounts</h2>
            </div>

            <GitBranch size={20} />
          </div>

          <div className="network-summary">

            <strong>
              {network?.network_summary
                ?.relationship_count || 0}
            </strong>

            <span>relationships discovered</span>

          </div>

          <div className="investigation-list">

            {network?.relationships
              ?.slice(0, 8)
              .map((item, index) => (
                <div
                  className="investigation-list-row"
                  key={`${item.related_account_id}-${index}`}
                >
                  <span>
                    {item.source_account_number}
                  </span>

                  <ArrowRight size={14} />

                  <strong>
                    {item.related_account_number}
                  </strong>

                  <small>
                    Depth {item.depth}
                  </small>
                </div>
              ))}

          </div>

        </div>

      </div>

      {/* =====================================================
          MONEY FLOW
      ===================================================== */}

      <div className="investigation-card">

        <div className="investigation-card-header">
          <div>
            <span>MONEY FLOW</span>
            <h2>Transaction Movement</h2>
          </div>

          <WalletCards size={20} />
        </div>

        <div className="flow-summary">

          <div>
            <span>Transactions</span>
            <strong>
              {moneyFlow?.investigation_summary
                ?.transaction_count || 0}
            </strong>
          </div>

          <div>
            <span>Total Moved</span>
            <strong>
              {formatCurrency(
                moneyFlow?.investigation_summary
                  ?.total_amount_moved
              )}
            </strong>
          </div>

          <div>
            <span>High-Risk Accounts</span>
            <strong>
              {moneyFlow?.investigation_summary
                ?.high_risk_accounts || 0}
            </strong>
          </div>

        </div>

        <div className="flow-table-wrapper">

          <table className="investigation-table">

            <thead>
              <tr>
                <th>TXN</th>
                <th>SENDER</th>
                <th>RECEIVER</th>
                <th>AMOUNT</th>
                <th>DEPTH</th>
                <th>TIME</th>
              </tr>
            </thead>

            <tbody>

              {moneyFlow?.money_flow?.map(
                (item) => (
                  <tr key={item.transaction_id}>

                    <td>
                      <button
                        className="link-button"
                        onClick={() =>
                          setSelectedTransaction(
                            item.transaction_id
                          )
                        }
                      >
                        #{item.transaction_id}
                      </button>
                    </td>

                    <td>
                      {item.sender_account_number}
                    </td>

                    <td>
                      {item.receiver_account_number}
                    </td>

                    <td>
                      {formatCurrency(item.amount)}
                    </td>

                    <td>
                      {item.depth}
                    </td>

                    <td>
                      {formatDate(item.txn_time)}
                    </td>

                  </tr>
                )
              )}

            </tbody>

          </table>

        </div>

      </div>

      {/* =====================================================
          TIMELINE
      ===================================================== */}

      <div className="investigation-card">

        <div className="investigation-card-header">
          <div>
            <span>INVESTIGATION HISTORY</span>
            <h2>Account Timeline</h2>
          </div>
        </div>

        <div className="timeline">

          {timeline?.transactions?.map(
            (transaction) => (
              <div
                className="timeline-item"
                key={`txn-${transaction.transaction_id}`}
              >
                <div className="timeline-dot" />

                <div>
                  <strong>
                    Transaction #{transaction.transaction_id}
                  </strong>

                  <p>
                    {transaction.sender_account_number}
                    {" → "}
                    {transaction.receiver_account_number}
                    {" • "}
                    {formatCurrency(transaction.amount)}
                  </p>

                  <small>
                    {formatDate(transaction.txn_time)}
                  </small>
                </div>
              </div>
            )
          )}

        </div>

      </div>

      {/* =====================================================
          CASE DECISION
      ===================================================== */}

      {activeCase && (
        <div className="investigation-card">

          <div className="investigation-card-header">
            <div>
              <span>INVESTIGATOR ACTION</span>
              <h2>
                Case #{activeCase.case_id}
              </h2>
            </div>

            <span className="case-status-open">
              {activeCase.case_status}
            </span>
          </div>

          <div className="finding-form">

            <label>
              Finding Type
              <select
                value={findingType}
                onChange={(event) =>
                  setFindingType(event.target.value)
                }
              >
                <option value="SUSPICIOUS">
                  SUSPICIOUS
                </option>

                <option value="LEGITIMATE">
                  LEGITIMATE
                </option>

                <option value="INCONCLUSIVE">
                  INCONCLUSIVE
                </option>
              </select>
            </label>

            <label>
              Investigation Finding
              <textarea
                value={finding}
                onChange={(event) =>
                  setFinding(event.target.value)
                }
                placeholder="Document the evidence and investigation finding..."
              />
            </label>

            <label>
              Closure Reason
              <textarea
                value={closureReason}
                onChange={(event) =>
                  setClosureReason(event.target.value)
                }
                placeholder="Explain why the investigation is being closed..."
              />
            </label>

            <div className="finding-actions">

              <button
                className="secondary-button"
                onClick={saveFinding}
              >
                Save Finding
              </button>

              <button
                className="primary-button"
                onClick={closeCase}
              >
                <CheckCircle2 size={15} />
                Record Decision & Close
              </button>

            </div>

            {actionMessage && (
              <p className="action-message">
                {actionMessage}
              </p>
            )}

          </div>

        </div>
      )}

      {/* =====================================================
          TRANSACTION DETAIL
      ===================================================== */}

      {selectedTransaction && (
        <TransactionEvidence
          transactionId={selectedTransaction}
          onClose={() =>
            setSelectedTransaction(null)
          }
        />
      )}

    </section>
  );
}


function TransactionEvidence({
  transactionId,
  onClose,
}) {
  const [data, setData] = useState(null);

  useEffect(() => {
    axios
      .get(
        `${API_BASE_URL}/api/investigation/transaction/${transactionId}`
      )
      .then((response) => {
        setData(response.data);
      })
      .catch(() => {
        setData(null);
      });
  }, [transactionId]);

  return (
    <div className="investigation-card">

      <div className="investigation-card-header">

        <div>
          <span>TRANSACTION EVIDENCE</span>
          <h2>
            Transaction #{transactionId}
          </h2>
        </div>

        <button
          className="secondary-button"
          onClick={onClose}
        >
          Close
        </button>

      </div>

      {data ? (
        <div className="transaction-evidence">

          <p>
            <strong>Amount:</strong>{" "}
            {formatCurrency(
              data.transaction?.amount
            )}
          </p>

          <p>
            <strong>Status:</strong>{" "}
            {data.transaction?.status}
          </p>

          <p>
            <strong>Investigation Status:</strong>{" "}
            {data.investigation_summary?.status}
          </p>

          <p>
            <strong>Highest Risk:</strong>{" "}
            {data.investigation_summary
              ?.highest_risk_score ?? "—"}
          </p>

          <p>
            <strong>Alerts:</strong>{" "}
            {data.investigation_summary
              ?.alert_count || 0}
          </p>

          <p>
            <strong>Cases:</strong>{" "}
            {data.investigation_summary
              ?.case_count || 0}
          </p>

        </div>
      ) : (
        <p>Loading transaction evidence...</p>
      )}

    </div>
  );
}

export default InvestigationWorkspace;