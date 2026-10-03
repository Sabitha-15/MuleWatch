import {
  LayoutDashboard,
  Users,
  ShieldAlert,
  BriefcaseBusiness,
  GitBranch,
} from "lucide-react";

const navigationItems = [
  {
    label: "Dashboard",
    icon: LayoutDashboard,
    path: "/",
  },
  {
    label: "Accounts",
    icon: Users,
    path: "/accounts",
  },
  {
    label: "Alerts",
    icon: ShieldAlert,
    path: "/alerts",
  },
  {
    label: "Fraud Cases",
    icon: BriefcaseBusiness,
    path: "/cases",
  },
  {
    label: "Money Flow",
    icon: GitBranch,
    path: "/money-flow",
  },
];

function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-mark">M</div>

        <div>
          <h1>MuleWatch</h1>
          <span>Fraud Investigation</span>
        </div>
      </div>

      <nav className="sidebar-navigation">
        <p className="navigation-label">INVESTIGATION</p>

        {navigationItems.map((item) => {
          const Icon = item.icon;

          return (
            <a
              key={item.path}
              href={item.path}
              className="navigation-item"
            >
              <Icon size={19} strokeWidth={1.8} />
              <span>{item.label}</span>
            </a>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className="system-status">
          <span className="status-dot" />
          <span>System Operational</span>
        </div>

        <p>© 2026 MuleWatch</p>
      </div>
    </aside>
  );
}

export default Sidebar;