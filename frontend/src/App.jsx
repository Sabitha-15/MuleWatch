import "./App.css";
import { BrowserRouter, Route, Routes } from "react-router-dom";

import AppLayout from "./components/layout/AppLayout";

import Dashboard from "./pages/Dashboard";
import Accounts from "./pages/Accounts";
import AccountDetails from "./pages/AccountDetails";
import Alerts from "./pages/Alerts";
import Cases from "./pages/Cases";
import MoneyFlow from "./pages/MoneyFlow";

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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;