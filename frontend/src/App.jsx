import "./App.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import AppLayout from "./components/layout/AppLayout";

import Dashboard from "./pages/Dashboard";
import Accounts from "./pages/Accounts";
import AccountDetails from "./pages/AccountDetails";
import Alerts from "./pages/Alerts";
import Cases from "./pages/Cases";
import MoneyFlow from "./pages/MoneyFlow";
import InvestigationWorkspace
  from "./pages/InvestigationWorkspace";
import TransactionIngestion
  from "./pages/TransactionIngestion";
import TransactionExplorer from "./pages/TransactionExplorer";
import AccountNetwork from "./pages/AccountNetwork";
import InvestigationReports from "./pages/InvestigationReports";
function MoneyFlowPlaceholder() {
  return <h1>Money Flow</h1>;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          {/* Dashboard */}
          <Route path="/" element={<Dashboard />} />

          {/* Accounts */}
          <Route path="/accounts" element={<Accounts />} />
          <Route
            path="/accounts/:accountId"
            element={<AccountDetails />}
          />

          {/* Fraud Alerts */}
          <Route path="/alerts" element={<Alerts />} />

          {/* Fraud Cases */}
          <Route path="/cases" element={<Cases />} />

          {/* Money Flow - coming next */}
          <Route path="/money-flow" element={<MoneyFlow />} />
          <Route
  path="/investigation"
  element={<InvestigationWorkspace />}
          />
          <Route
  path="/transaction-ingestion"
  element={<TransactionIngestion />}
/>
          <Route path="/transaction-explorer" element={<TransactionExplorer />} />
          <Route path="/account-network" element={<AccountNetwork />} />
          <Route path="/investigation-reports" element={<InvestigationReports />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;