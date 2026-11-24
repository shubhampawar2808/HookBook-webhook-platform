import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";

import { HookForgeMark } from "@/brand/HookForgeMark";
import { CommandPalette } from "@/components/CommandPalette";
import { ToastHost } from "@/components/ToastHost";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { logout } from "@/features/auth/authSlice";
import { NAV_ITEMS } from "@/layouts/navConfig";
import { setCommandOpen, setMobileNavOpen, toggleSidebar } from "@/store/uiSlice";
import { APP_ENV } from "@/utils/config";
import "@/styles/layout.css";
import "@/styles/components.css";

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/events": "Events",
  "/deliveries": "Deliveries",
  "/endpoints": "Endpoints",
  "/event-types": "Event Types",
  "/subscriptions": "Subscriptions",
  "/api-keys": "API Keys",
  "/dead-letter": "Dead Letter Queue",
  "/settings": "Settings",
};

export function DashboardLayout() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useAppSelector((s) => s.ui.sidebarCollapsed);
  const mobileOpen = useAppSelector((s) => s.ui.mobileNavOpen);
  const user = useAppSelector((s) => s.auth.user);

  const basePath = "/" + (location.pathname.split("/")[1] || "");
  const crumb = TITLES[basePath] || TITLES[location.pathname] || "Console";

  return (
    <div className={`dash-shell ${collapsed ? "collapsed" : ""}`}>
      {mobileOpen ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => dispatch(setMobileNavOpen(false))}
        />
      ) : null}

      <aside className={`sidebar ${mobileOpen ? "open" : ""}`} aria-label="Primary">
        <NavLink to="/" className="sidebar-brand" onClick={() => dispatch(setMobileNavOpen(false))}>
          <HookForgeMark size={collapsed && !mobileOpen ? 28 : 32} />
          <span className="brand-copy">
            <span className="brand-name">HookForge</span>
            <span className="brand-tag">Observatory</span>
          </span>
        </NavLink>

        <div className="workspace-chip" title={user?.organization_name}>
          <span className="label">Workspace</span>
          <span className="value">{user?.organization_name || "—"}</span>
        </div>

        <ul className="nav-list">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
                title={collapsed ? item.label : undefined}
                onClick={() => dispatch(setMobileNavOpen(false))}
              >
                {item.icon}
                <span className="nav-label">{item.label}</span>
              </NavLink>
            </li>
          ))}
        </ul>

        <div className="sidebar-footer">
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => dispatch(toggleSidebar())}
            aria-pressed={collapsed}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            <span className="btn-label">{collapsed ? "Expand" : "Collapse"}</span>
            {!collapsed ? null : "⇄"}
          </button>
        </div>
      </aside>

      <div className="dash-main">
        <header className="topbar">
          <div className="topbar-left">
            <button
              type="button"
              className="btn btn-ghost mobile-nav-toggle"
              onClick={() => dispatch(setMobileNavOpen(true))}
            >
              Menu
            </button>
            <nav className="breadcrumbs" aria-label="Breadcrumb">
              <span>HookForge</span>
              <span aria-hidden>/</span>
              <strong>{crumb}</strong>
            </nav>
          </div>
          <div className="topbar-right">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => dispatch(setCommandOpen(true))}
              title="Command palette (Ctrl+K)"
            >
              Search
            </button>
            <span className="status-badge tone-neutral" title="Frontend environment">
              {APP_ENV}
            </span>
            <span className="muted" style={{ fontSize: "0.9rem" }}>
              {user?.full_name || user?.email}
            </span>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                dispatch(logout());
                navigate("/login");
              }}
            >
              Logout
            </button>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>

      <CommandPalette />
      <ToastHost />
    </div>
  );
}
