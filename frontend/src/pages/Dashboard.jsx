import { useEffect, useState } from "react";
import axios from "axios";
import {
  AlertTriangle,
  ArrowDownLeft,
  ArrowUpRight,
  BriefcaseBusiness,
  CircleDollarSign,
  ShieldAlert,
  Users,
} from "lucide-react";
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const API_BASE_URL = "http://127.0.0.1:8000";

function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchDashboard();
  }, []);

  async function fetchDashboard() {
    try {
      setLoading(true);
      setError("");

      const response = await axios.get(
        `${API_BASE_URL}/api/dashboard/summary`
      );

      setDashboard(response.data);
    } catch (err) {
      console.error("Dashboard API error:", err);
      setError(
        "Unable to load dashboard data. Make sure the FastAPI backend is running."
      );
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="dashboard-state">
        <div className="loading-spinner" />
        <p>Loading investigation intelligence...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-state dashboard-error">
        <AlertTriangle size={24} />
        <h3>Dashboard unavailable</h3>
        <p>{error}</p>

        <button onClick={fetchDashboard} className="retry-button">
          Retry
        </button>
      </div>
    );
  }
  const summary = dashboard?.summary || {};
    
  const riskDistribution = dashboard?.risk_distribution || [];

  const chartData = riskDistribution.map((item) => ({
    name: item.risk_level,
    value: Number(item.assessment_count),
  }));

  const riskColors = {
    LOW: "#22c55e",
    MEDIUM: "#eab308",
    HIGH: "#f97316",
    CRITICAL: "#ef4444",
  };

  return (
    <div className="dashboard-page">

      {/* PAGE HEADER */}
      <div className="page-header">
        <div>
          <p className="page-eyebrow">OVERVIEW</p>
          <h1>Fraud Intelligence Dashboard</h1>
          <p className="page-description">
            Monitor account risk, transaction activity, fraud alerts and
            investigation cases.
          </p>
        </div>

        <button onClick={fetchDashboard} className="refresh-button">
          Refresh Data
        </button>
      </div>

      {/* KPI CARDS */}
      <section className="kpi-grid">

        <div className="kpi-card">
          <div className="kpi-icon blue">
            <Users size={20} />
          </div>

          <div className="kpi-content">
            <span>Total Accounts</span>
            <strong>{summary.total_accounts}</strong>
            <small>Monitored accounts</small>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon purple">
            <ArrowUpRight size={20} />
          </div>

          <div className="kpi-content">
            <span>Total Transactions</span>
            <strong>{summary.total_transactions}</strong>
            <small>Recorded transactions</small>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon green">
            <CircleDollarSign size={20} />
          </div>

          <div className="kpi-content">
            <span>Transaction Volume</span>
            <strong>
              ₹{Number(summary.total_transaction_amount).toLocaleString(
                "en-IN"
              )}
            </strong>
            <small>Total transaction value</small>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon red">
            <ShieldAlert size={20} />
          </div>

          <div className="kpi-content">
            <span>Open Alerts</span>
            <strong>{summary.open_alerts}</strong>
            <small>Require investigation</small>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon orange">
            <BriefcaseBusiness size={20} />
          </div>

          <div className="kpi-content">
            <span>Open Cases</span>
            <strong>{summary.open_cases}</strong>
            <small>Active investigations</small>
          </div>
        </div>

      </section>

      {/* ANALYTICS ROW */}
      <section className="dashboard-grid">

        {/* RISK DISTRIBUTION */}
        <div className="dashboard-card risk-card">

          <div className="card-header">
            <div>
              <h2>Risk Distribution</h2>
              <p>Current account risk classification</p>
            </div>
          </div>

          <div className="risk-content">

            <div className="risk-chart">
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={chartData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    innerRadius={65}
                    outerRadius={92}
                    paddingAngle={3}
                  >
                    {chartData.map((entry) => (
                      <Cell
                        key={entry.name}
                        fill={riskColors[entry.name] || "#64748b"}
                      />
                    ))}
                  </Pie>

                  <Tooltip
                    contentStyle={{
                      background: "#111820",
                      border: "1px solid #28313d",
                      borderRadius: "8px",
                      color: "#e8edf5",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>

              <div className="chart-center">
                <strong>
                  {chartData.reduce((total, item) => total + item.value, 0)}
                </strong>
                <span>Risk Assessments</span>
              </div>
            </div>

            <div className="risk-legend">

              {chartData.map((item) => (
                <div className="risk-legend-item" key={item.name}>
                  <div className="risk-label">
                    <span
                      className="risk-dot"
                      style={{
                        background: riskColors[item.name] || "#64748b",
                      }}
                    />

                    <span>{item.name}</span>
                  </div>

                  <strong>{item.value}</strong>
                </div>
              ))}

            </div>

          </div>
        </div>

        {/* HIGH RISK ACCOUNTS */}
        <div className="dashboard-card">

          <div className="card-header">
            <div>
              <h2>High-Risk Accounts</h2>
              <p>Accounts requiring attention</p>
            </div>
          </div>

          <div className="account-risk-list">

            {dashboard.high_risk_accounts?.length > 0 ? (
              dashboard.high_risk_accounts.map((account) => (
                <div className="account-risk-row" key={account.account_id}>

                  <div className="account-avatar">
                    {account.account_number?.slice(-2)}
                  </div>

                  <div className="account-risk-info">
                    <strong>
                      {account.account_number}
                    </strong>

                    <span>
                      Account #{account.account_id}
                    </span>
                  </div>

                  <div className="risk-score-block">
                    <strong>{account.risk_score}</strong>

                    <span
                      className={`risk-badge ${account.risk_level?.toLowerCase()}`}
                    >
                      {account.risk_level}
                    </span>
                  </div>

                </div>
              ))
            ) : (
              <div className="empty-state">
                No high-risk accounts found.
              </div>
            )}

          </div>
        </div>

      </section>

      {/* LOWER ANALYTICS */}
      <section className="dashboard-grid lower-grid">

        {/* ALERTS */}
        <div className="dashboard-card">

          <div className="card-header">
            <div>
              <h2>Recent Fraud Alerts</h2>
              <p>Latest risk-triggered alerts</p>
            </div>

            <ArrowDownLeft size={18} />
          </div>

          <div className="alert-list">

            {dashboard.recent_alerts?.length > 0 ? (
              dashboard.recent_alerts.map((alert) => (
                <div className="alert-row" key={alert.alert_id}>

                  <div className="alert-icon">
                    <ShieldAlert size={17} />
                  </div>

                  <div className="alert-info">
                    <strong>
                      Account {alert.account_id}
                    </strong>

                    <span>
                      Risk score: {alert.risk_score}
                    </span>
                  </div>

                  <span
                    className={`status-badge ${alert.alert_status?.toLowerCase()}`}
                  >
                    {alert.alert_status}
                  </span>

                </div>
              ))
            ) : (
              <div className="empty-state">
                No recent fraud alerts.
              </div>
            )}

          </div>
        </div>

        {/* CASES */}
        <div className="dashboard-card">

          <div className="card-header">
            <div>
              <h2>Recent Investigation Cases</h2>
              <p>Latest fraud investigations</p>
            </div>

            <BriefcaseBusiness size={18} />
          </div>

          <div className="case-list">

            {dashboard.recent_cases?.length > 0 ? (
              dashboard.recent_cases.map((caseItem) => (
                <div className="case-row" key={caseItem.case_id}>

                  <div className="case-number">
                    #{caseItem.case_id}
                  </div>

                  <div className="case-info">
                    <strong>{caseItem.case_title}</strong>

                    <span>
                      Investigator:{" "}
                      {caseItem.investigator_name || "Unassigned"}
                    </span>
                  </div>

                  <div className="case-meta">

                    <span
                      className={`priority-badge ${caseItem.priority?.toLowerCase()}`}
                    >
                      {caseItem.priority}
                    </span>

                    <span
                      className={`status-badge ${caseItem.case_status?.toLowerCase()}`}
                    >
                      {caseItem.case_status}
                    </span>

                  </div>

                </div>
              ))
            ) : (
              <div className="empty-state">
                No investigation cases found.
              </div>
            )}

          </div>
        </div>

      </section>

    </div>
  );
}

export default Dashboard;