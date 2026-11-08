import { useState, useEffect  } from "react";
import { Search, RefreshCw, History, CheckCircle2, XCircle } from "lucide-react";

const API = "http://127.0.0.1:8000/api/phase2";
const panel = { background: "#FFFFFF", border: "1px solid #D7E0EC", borderRadius: 12, padding: 18 };
const field = { height: 40, border: "1px solid #CBD5E1", borderRadius: 8, padding: "0 10px", background: "#FFFFFF", color: "#172033", minWidth: 0 };
const button = { border: "1px solid #CBD5E1", borderRadius: 8, padding: "9px 13px", background: "#FFFFFF", color: "#1D4ED8", fontWeight: 600, cursor: "pointer" };

function money(value) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(Number(value || 0));
}

export default function TransactionExplorer() {
  const [filters, setFilters] = useState({ search: "", status: "", transaction_type: "", min_amount: "", max_amount: "", date_from: "", date_to: "" });
  const [transactions, setTransactions] = useState([]);
  const [pagination, setPagination] = useState({ page: 1, page_size: 20, total: 0, total_pages: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [audits, setAudits] = useState({});

  async function loadTransactions(page = 1) {
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams({ page: String(page), page_size: "20" });
      Object.entries(filters).forEach(([key, value]) => { if (String(value).trim()) params.set(key, value); });
      const response = await fetch(`${API}/transactions?${params}`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Unable to load transactions.");
      setTransactions(data.transactions || []); setPagination(data.pagination || pagination);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  }
  useEffect(() => {
  loadTransactions(1);
}, []);

  async function finalize(row, status) {
    const reason = window.prompt(`Reason for marking transaction #${row.transaction_id} as ${status}:`);
    if (!reason?.trim()) return;
    try {
      const response = await fetch(`${API}/transactions/${row.transaction_id}/status`, {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_status: status, change_reason: reason.trim() }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Status update failed.");
      await loadTransactions(pagination.page);
      await loadAudit(row.transaction_id);
    } catch (err) { setError(err.message); }
  }

  async function loadAudit(id) {
    try {
      const response = await fetch(`${API}/transactions/${id}/audit`);
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Audit lookup failed.");
      setAudits((current) => ({ ...current, [id]: data.audit_records || [] }));
    } catch (err) { setError(err.message); }
  }

  return (
    <section style={{ maxWidth: 1500, margin: "0 auto" }}>
      <div className="page-header">
        <div><p className="page-eyebrow">PHASE 2 · DATABASE ANALYTICS</p><h1>Advanced Transaction Explorer</h1><p className="page-description">Search transaction records, inspect risk evidence and finalize pending transactions with an automatic audit trail.</p></div>
        <button style={button} onClick={() => loadTransactions(pagination.page)} disabled={loading}><RefreshCw size={15} style={{ verticalAlign: "middle", marginRight: 6 }} />Refresh</button>
      </div>
      <div style={{ ...panel, marginBottom: 16 }}>
        <form onSubmit={(e) => { e.preventDefault(); loadTransactions(1); }} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(145px,1fr))", gap: 10 }}>
          <input style={{ ...field, gridColumn: "span 2" }} placeholder="Transaction ID, account number or customer" value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
          <select style={field} value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}><option value="">All statuses</option><option>PENDING</option><option>SUCCESS</option><option>FAILED</option></select>
          <select style={field} value={filters.transaction_type} onChange={(e) => setFilters({ ...filters, transaction_type: e.target.value })}><option value="">All types</option><option>TRANSFER</option><option>DEPOSIT</option><option>WITHDRAWAL</option></select>
          <input style={field} type="number" min="0" placeholder="Minimum amount" value={filters.min_amount} onChange={(e) => setFilters({ ...filters, min_amount: e.target.value })} />
          <input style={field} type="number" min="0" placeholder="Maximum amount" value={filters.max_amount} onChange={(e) => setFilters({ ...filters, max_amount: e.target.value })} />
          <label style={{ fontSize: 11, color: "#64748B" }}>From<input style={{ ...field, display: "block", width: "100%", marginTop: 4 }} type="date" value={filters.date_from} onChange={(e) => setFilters({ ...filters, date_from: e.target.value })} /></label>
          <label style={{ fontSize: 11, color: "#64748B" }}>To<input style={{ ...field, display: "block", width: "100%", marginTop: 4 }} type="date" value={filters.date_to} onChange={(e) => setFilters({ ...filters, date_to: e.target.value })} /></label>
          <button style={{ ...button, background: "#1D4ED8", color: "white", alignSelf: "end" }} type="submit" disabled={loading}><Search size={15} style={{ verticalAlign: "middle", marginRight: 5 }} />Search</button>
        </form>
      </div>
      {error && <div style={{ ...panel, color: "#B91C1C", marginBottom: 14 }}>{error}</div>}
      <div style={panel}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}><div><strong>Transaction Records</strong><div style={{ color: "#64748B", fontSize: 12, marginTop: 4 }}>{pagination.total} matching records</div></div><span style={{ color: "#64748B", fontSize: 12 }}>Page {pagination.page} of {pagination.total_pages || 1}</span></div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, minWidth: 1000 }}>
            <thead><tr style={{ color: "#64748B", textAlign: "left", background: "#F8FAFC" }}>{["ID / TIME", "SENDER", "RECEIVER", "AMOUNT", "TYPE", "STATUS", "RISK", "ACTIONS"].map((h) => <th key={h} style={{ padding: 11, borderBottom: "1px solid #E2E8F0" }}>{h}</th>)}</tr></thead>
            <tbody>
              {transactions.map((row) => <tr key={row.transaction_id}>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7" }}><strong>#{row.transaction_id}</strong><div style={{ color: "#64748B", marginTop: 3 }}>{new Date(row.txn_time).toLocaleString("en-IN")}</div></td>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7" }}>{row.sender_account_number}<div style={{ color: "#64748B" }}>{row.sender_customer_name}</div></td>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7" }}>{row.receiver_account_number}<div style={{ color: "#64748B" }}>{row.receiver_customer_name}</div></td>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7", fontWeight: 700 }}>{money(row.amount)}</td>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7" }}>{row.transaction_type}<div style={{ color: "#64748B" }}>{row.channel || "—"}</div></td>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7" }}><strong>{row.status}</strong></td>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7" }}>{row.risk_score ?? "—"} {row.risk_level || ""}</td>
                <td style={{ padding: 11, borderBottom: "1px solid #EEF2F7", whiteSpace: "nowrap" }}>
                  {row.status === "PENDING" ? <><button title="Mark successful" style={{ ...button, padding: "6px 8px", marginRight: 5 }} onClick={() => finalize(row, "SUCCESS")}><CheckCircle2 size={14} /></button><button title="Mark failed" style={{ ...button, padding: "6px 8px", color: "#B91C1C" }} onClick={() => finalize(row, "FAILED")}><XCircle size={14} /></button></> : null}
                  <button style={{ ...button, padding: "6px 8px", marginLeft: 5 }} onClick={() => audits[row.transaction_id] ? setAudits((a) => ({ ...a, [row.transaction_id]: null })) : loadAudit(row.transaction_id)}><History size={14} /></button>
                </td>
              </tr>)}
              {transactions.length === 0 && <tr><td colSpan="8" style={{ padding: 24, textAlign: "center", color: "#64748B" }}>{loading ? "Loading transactions..." : "No transactions match the selected filters."}</td></tr>}
            </tbody>
          </table>
        </div>
        {transactions.map((row) => audits[row.transaction_id] && <div key={`audit-${row.transaction_id}`} style={{ marginTop: 12, padding: 12, background: "#F8FAFC", borderRadius: 8 }}><strong>Transaction #{row.transaction_id} status audit</strong>{audits[row.transaction_id].length ? audits[row.transaction_id].map((a) => <div key={a.audit_id} style={{ fontSize: 12, marginTop: 6 }}>{a.old_status} → {a.new_status} · {new Date(a.changed_at).toLocaleString("en-IN")} · {a.change_reason || "No reason supplied"}</div>) : <p style={{ fontSize: 12, color: "#64748B" }}>No status changes recorded.</p>}</div>)}
        <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 16 }}><button style={button} disabled={pagination.page <= 1 || loading} onClick={() => loadTransactions(pagination.page - 1)}>Previous</button><button style={button} disabled={pagination.page >= pagination.total_pages || loading} onClick={() => loadTransactions(pagination.page + 1)}>Next</button></div>
      </div>
    </section>
  );
}
