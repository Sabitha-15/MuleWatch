import { useState } from "react";
import axios from "axios";
import {
  Search,
  GitBranch,
  Loader2,
  AlertCircle,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

export default function MoneyFlow() {
  const [accountId, setAccountId] = useState("6");
  const [maxDepth, setMaxDepth] = useState("3");
  const [flowData, setFlowData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleTraceMoney(event) {
    event.preventDefault();

    if (!accountId) return;

    setLoading(true);
    setError("");
    setFlowData(null);

    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/money-flow/${accountId}`,
        {
          params: {
            max_depth: Number(maxDepth),
          },
        }
      );

      setFlowData(response.data);
    } catch (err) {
      console.error(err);

      setError(
        err?.response?.data?.detail ||
          "Unable to trace money flow for this account."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="page-container">
      {/* PAGE HEADER */}
      <div className="page-header">
        <div>
          <div className="eyebrow">
            INVESTIGATION ANALYTICS
          </div>

          <h1>Money Flow</h1>

          <p>
            Trace how funds move between accounts and investigate
            transaction chains.
          </p>
        </div>
      </div>

      {/* TRACE FORM */}
      <div className="content-card">
        <div className="section-header">
          <div>
            <div className="section-eyebrow">
              TRACE MONEY
            </div>

            <h2>Account Flow Investigation</h2>

            <p>
              Enter an account and trace successful transactions
              connected to it.
            </p>
          </div>

          <GitBranch size={24} />
        </div>

        <form
          onSubmit={handleTraceMoney}
          className="money-flow-form"
        >
          {/* ACCOUNT ID */}
          <label>
            Account ID

            <input
              type="number"
              min="1"
              value={accountId}
              onChange={(event) =>
                setAccountId(event.target.value)
              }
              placeholder="Example: 6"
              required
            />
          </label>

          {/* TRACE DEPTH */}
          <label>
            Trace Depth

            <select
              value={maxDepth}
              onChange={(event) =>
                setMaxDepth(event.target.value)
              }
            >
              <option value="1">1 level</option>
              <option value="2">2 levels</option>
              <option value="3">3 levels</option>
              <option value="4">4 levels</option>
              <option value="5">5 levels</option>
            </select>
          </label>

          {/* TRACE BUTTON */}
          <button
            type="submit"
            className="primary-button"
            disabled={loading}
          >
            {loading ? (
              <>
                <Loader2
                  size={17}
                  className="spin"
                />
                Tracing...
              </>
            ) : (
              <>
                <Search size={17} />
                Trace Money
              </>
            )}
          </button>
        </form>

        {/* ERROR */}
        {error && (
          <div className="error-banner">
            <AlertCircle size={18} />
            {error}
          </div>
        )}
      </div>

      {/* TRACE RESULT */}
      {flowData && (
        <div className="content-card">
          <div className="section-header">
            <div>
              <div className="section-eyebrow">
                TRACE RESULT
              </div>

              <h2>Money Flow Investigation</h2>

              <p>
                Transaction path detected from Account #
                {flowData.account?.account_id}.
              </p>
            </div>

            <GitBranch size={24} />
          </div>

          {/* SUMMARY CARDS */}
          <div className="flow-summary-grid">
            <div className="flow-summary-card">
              <span>Starting Account</span>

              <strong>
                #{flowData.account?.account_id}
              </strong>

              <small>
                {flowData.account?.account_number}
              </small>
            </div>

            <div className="flow-summary-card">
              <span>Transactions Found</span>

              <strong>
                {flowData.trace?.transactions_found ?? 0}
              </strong>

              <small>
                Max depth:{" "}
                {flowData.trace
                  ?.maximum_depth_reached ?? 0}
              </small>
            </div>

            <div className="flow-summary-card">
              <span>Total Money Movement</span>

              <strong>
                ₹
                {Number(
                  flowData.trace
                    ?.total_money_movement ?? 0
                ).toLocaleString("en-IN")}
              </strong>

              <small>
                Successful transactions
              </small>
            </div>
          </div>

          {/* TRANSACTION CHAIN */}
          <div className="money-flow-chain">
            <div className="flow-chain-title">
              <span>TRANSACTION CHAIN</span>

              <span>
                {flowData.flows?.length ?? 0} movements
              </span>
            </div>

            {flowData.flows?.length > 0 ? (
              flowData.flows.map((flow) => (
                <div
                  className="flow-step"
                  key={flow.transaction_id}
                >
                  {/* SOURCE ACCOUNT */}
                  <div className="flow-node">
                    <span>ACCOUNT</span>

                    <strong>
                      #{flow.source_account_id}
                    </strong>

                    <small>
                      {flow.source_account_number}
                    </small>
                  </div>

                  {/* MONEY MOVEMENT */}
                  <div className="flow-arrow">
                    <span>
                      ₹
                      {Number(
                        flow.amount
                      ).toLocaleString("en-IN")}
                    </span>

                    <div>↓</div>

                    <small>
                      Transaction #
                      {flow.transaction_id}
                    </small>
                  </div>

                  {/* TARGET ACCOUNT */}
                  <div className="flow-node target">
                    <span>ACCOUNT</span>

                    <strong>
                      #{flow.target_account_id}
                    </strong>

                    <small>
                      {flow.target_account_number}
                    </small>
                  </div>
                </div>
              ))
            ) : (
              <div className="empty-state">
                No successful money movements found
                for this account.
              </div>
            )}
          </div>

          {/* TRANSACTION DETAILS */}
          {flowData.flows?.length > 0 && (
            <div className="transaction-details">
              <div className="flow-chain-title">
                <span>TRANSACTION DETAILS</span>

                <span>
                  {flowData.flows.length} records
                </span>
              </div>

              <div className="transaction-table-wrapper">
                <table className="transaction-table">
                  <thead>
                    <tr>
                      <th>Transaction</th>
                      <th>Depth</th>
                      <th>Type</th>
                      <th>Channel</th>
                      <th>Amount</th>
                      <th>Status</th>
                      <th>Time</th>
                    </tr>
                  </thead>

                  <tbody>
                    {flowData.flows.map((flow) => (
                      <tr
                        key={`detail-${flow.transaction_id}`}
                      >
                        <td>
                          #{flow.transaction_id}
                        </td>

                        <td>
                          {flow.depth}
                        </td>

                        <td>
                          {flow.transaction_type}
                        </td>

                        <td>
                          {flow.channel || "—"}
                        </td>

                        <td>
                          ₹
                          {Number(
                            flow.amount
                          ).toLocaleString("en-IN")}
                        </td>

                        <td>
                          <span className="transaction-status">
                            {flow.status}
                          </span>
                        </td>

                        <td>
                          {new Date(
                            flow.txn_time
                          ).toLocaleString("en-IN")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}