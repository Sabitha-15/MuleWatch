import { useState } from "react";
import axios from "axios";
import {
  ArrowRight,
  CheckCircle2,
  ShieldAlert,
} from "lucide-react";

const API_BASE_URL = "http://127.0.0.1:8000";

function TransactionIngestion() {
  const [form, setForm] = useState({
    idempotency_key: `TXN-${Date.now()}`,
    sender_account_id: "",
    receiver_account_id: "",
    beneficiary_id: "",
    amount: "",
    transaction_type: "TRANSFER",
    channel: "ONLINE",
    description: "",
  });

  const [result, setResult] = useState(null);
  const [error, setError] = useState("");

  function updateField(field, value) {
    setForm((previous) => ({
      ...previous,
      [field]: value,
    }));
  }

  async function submitTransaction(event) {
    event.preventDefault();

    try {
      setError("");
      setResult(null);

      const payload = {
        idempotency_key: form.idempotency_key,
        sender_account_id:
          Number(form.sender_account_id),
        receiver_account_id:
          Number(form.receiver_account_id),
        beneficiary_id:
          form.beneficiary_id
            ? Number(form.beneficiary_id)
            : null,
        amount: Number(form.amount),
        transaction_type:
          form.transaction_type,
        channel: form.channel,
        description:
          form.description || null,
      };

      const response = await axios.post(
        `${API_BASE_URL}/api/accounts/transactions/ingest`,
        payload
      );

      setResult(response.data);
    } catch (err) {
      setError(
        err.response?.data?.detail ||
          "Transaction ingestion failed."
      );
    }
  }

  return (
    <section className="transaction-ingestion-page">

      <div className="page-header">
        <div>
          <span className="page-eyebrow">
            TRANSACTION OPERATIONS
          </span>

          <h1>Transaction Ingestion</h1>

          <p className="page-description">
            Simulate an incoming banking transaction and
            execute the complete MuleWatch risk pipeline.
          </p>
        </div>
      </div>

      <div className="ingestion-layout">

        <form
          className="ingestion-card"
          onSubmit={submitTransaction}
        >

          <h2>New Transaction</h2>

          <label>
            Idempotency Key
            <input
              value={form.idempotency_key}
              onChange={(event) =>
                updateField(
                  "idempotency_key",
                  event.target.value
                )
              }
              required
            />
          </label>

          <label>
            Sender Account ID
            <input
              type="number"
              value={form.sender_account_id}
              onChange={(event) =>
                updateField(
                  "sender_account_id",
                  event.target.value
                )
              }
              required
            />
          </label>

          <label>
            Receiver Account ID
            <input
              type="number"
              value={form.receiver_account_id}
              onChange={(event) =>
                updateField(
                  "receiver_account_id",
                  event.target.value
                )
              }
              required
            />
          </label>

          <label>
            Beneficiary ID
            <input
              type="number"
              value={form.beneficiary_id}
              onChange={(event) =>
                updateField(
                  "beneficiary_id",
                  event.target.value
                )
              }
            />
          </label>

          <label>
            Amount
            <input
              type="number"
              min="1"
              value={form.amount}
              onChange={(event) =>
                updateField(
                  "amount",
                  event.target.value
                )
              }
              required
            />
          </label>

          <label>
            Channel
            <select
              value={form.channel}
              onChange={(event) =>
                updateField(
                  "channel",
                  event.target.value
                )
              }
            >
              <option>ONLINE</option>
              <option>MOBILE</option>
              <option>ATM</option>
              <option>BRANCH</option>
            </select>
          </label>

          <label>
            Description
            <textarea
              value={form.description}
              onChange={(event) =>
                updateField(
                  "description",
                  event.target.value
                )
              }
            />
          </label>

          <button
            className="primary-button"
            type="submit"
          >
            Process Transaction
            <ArrowRight size={15} />
          </button>

        </form>

        <div className="ingestion-card">

          <h2>Automated Pipeline</h2>

          <div className="pipeline-step">
            <CheckCircle2 size={17} />
            Transaction Validation
          </div>

          <div className="pipeline-step">
            <CheckCircle2 size={17} />
            PostgreSQL Transaction Insert
          </div>

          <div className="pipeline-step">
            <CheckCircle2 size={17} />
            ML Risk Assessment
          </div>

          <div className="pipeline-step">
            <ShieldAlert size={17} />
            Automatic Fraud Alert
          </div>

          {error && (
            <div className="ingestion-error">
              {error}
            </div>
          )}

          {result && (
            <div className="ingestion-result">

              <h3>Transaction Processed</h3>

              <p>
                Transaction #
                {result.transaction?.transaction_id}
              </p>

              <p>
                Risk Score:{" "}
                <strong>
                  {result.risk_assessment?.risk_score}
                </strong>
              </p>

              <p>
                Risk Level:{" "}
                <strong>
                  {result.risk_assessment?.risk_level}
                </strong>
              </p>

              <p>
                Investigation Priority:{" "}
                <strong>
                  {result.investigation?.priority}
                </strong>
              </p>

              {result.alert && (
                <p>
                  Alert #{result.alert.alert_id} created
                </p>
              )}

            </div>
          )}

        </div>

      </div>

    </section>
  );
}

export default TransactionIngestion;