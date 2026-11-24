import { Link, Outlet } from "react-router-dom";

import { APP_ENV } from "@/utils/config";
import "@/styles/layout.css";
import "@/styles/components.css";

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="brand" aria-label="HookForge home">
          <span className="brand-mark" aria-hidden="true">
            HF
          </span>
          <span className="brand-text">
            <span className="brand-name">HookForge</span>
            <span className="brand-tag">webhook delivery platform</span>
          </span>
        </Link>
        <div className="header-meta">
          <span className={`env-badge ${APP_ENV}`} title="Application environment">
            {APP_ENV}
          </span>
        </div>
      </header>

      <main className="app-main">
        <Outlet />
      </main>

      <footer className="app-footer">
        <span>HookForge · Phase 1 foundation</span>
        <span className="mono muted">v0.1.0</span>
      </footer>
    </div>
  );
}
