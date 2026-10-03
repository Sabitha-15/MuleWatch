import axios from "axios";

const api = axios.create({
  baseURL: "http://127.0.0.1:8000",
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

/* =========================================================
   DASHBOARD
   ========================================================= */

export async function getDashboardSummary() {
  const response = await api.get("/api/dashboard/summary");
  return response.data;
}

/* =========================================================
   ACCOUNTS
   ========================================================= */

export async function getAccounts(params = {}) {
  const response = await api.get("/api/accounts", {
    params,
  });

  return response.data;
}

export async function getAccount(accountId) {
  const response = await api.get(
    `/api/accounts/${accountId}`
  );

  return response.data;
}

export async function getAccountTransactions(
  accountId,
  params = {}
) {
  const response = await api.get(
    `/api/accounts/${accountId}/transactions`,
    {
      params,
    }
  );

  return response.data;
}

/* =========================================================
   RISK
   ========================================================= */

export async function assessAccountRisk(accountId) {
  const response = await api.post(
    `/api/risk/${accountId}/assess`
  );

  return response.data;
}

/* =========================================================
   FRAUD ALERTS
   ========================================================= */

export async function getAlerts(params = {}) {
  const response = await api.get("/api/alerts", {
    params,
  });

  return response.data;
}

export async function getAlert(alertId) {
  const response = await api.get(
    `/api/alerts/${alertId}`
  );

  return response.data;
}

export async function updateAlertStatus(
  alertId,
  status
) {
  const response = await api.patch(
    `/api/alerts/${alertId}/status`,
    {
      status,
    }
  );

  return response.data;
}

/* =========================================================
   FRAUD CASES
   ========================================================= */

export async function getCases(params = {}) {
  const response = await api.get("/api/cases", {
    params,
  });

  return response.data;
}

export async function getCase(caseId) {
  const response = await api.get(
    `/api/cases/${caseId}`
  );

  return response.data;
}

export async function addCaseNote(caseId, investigatorId, noteText) {
  const response = await api.post(`/api/cases/${caseId}/notes`, {
    investigator_id: investigatorId,
    note_text: noteText,
  });
  return response.data;
}

export async function openCase(caseData) {
  const response = await api.post(
    "/api/cases",
    caseData
  );

  return response.data;
}

export async function closeCase(
  caseId,
  investigatorId,
  reason
) {
  const response = await api.patch(
    `/api/cases/${caseId}/close`,
    {
      investigator_id: investigatorId,
      closure_reason: reason,
    }
  );

  return response.data;
}

/* =========================================================
   MONEY FLOW
   ========================================================= */

export async function getMoneyFlow(
  accountId,
  maxDepth = 5
) {
  const response = await api.get(
    `/api/money-flow/${accountId}`,
    {
      params: {
        max_depth: maxDepth,
      },
    }
  );

  return response.data;
}

/* =========================================================
   DEFAULT API CLIENT
   ========================================================= */

export default api;