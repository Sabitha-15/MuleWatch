import { Bell, Search, ShieldCheck } from "lucide-react";

function Topbar() {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <div>
          <p className="topbar-eyebrow">FINANCIAL FRAUD INTELLIGENCE</p>
          <h2>Investigation Center</h2>
        </div>
      </div>

      <div className="topbar-right">
        <div className="search-box">
          <Search size={18} />
          <input
            type="text"
            placeholder="Search accounts, cases..."
            aria-label="Search"
          />
        </div>

        <button className="notification-button" aria-label="Notifications">
          <Bell size={20} />
          <span className="notification-badge">3</span>
        </button>

        <div className="analyst-profile">
          <div className="profile-avatar">
            <ShieldCheck size={19} />
          </div>

          <div className="profile-info">
            <strong>Investigator</strong>
            <span>Fraud Operations</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Topbar;