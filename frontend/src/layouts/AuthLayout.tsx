import { Link, Outlet } from "react-router-dom";

import { HookForgeMark } from "@/brand/HookForgeMark";
import "@/styles/layout.css";
import "@/styles/components.css";

export function AuthLayout() {
  return (
    <div className="auth-shell">
      <section className="auth-visual" aria-label="HookForge brand">
        <Link to="/login" className="sidebar-brand" style={{ width: "fit-content" }}>
          <HookForgeMark size={36} />
          <span className="brand-copy">
            <span className="brand-name">HookForge</span>
            <span className="brand-tag">Webhook Observatory</span>
          </span>
        </Link>
        <div>
          <h1>Industrial precision for webhook delivery.</h1>
          <p>
            Observe event flow, inspect attempts, and recover failures with an operator console built for
            reliability engineering.
          </p>
        </div>
        <svg className="flow-svg" viewBox="0 0 420 120" aria-hidden>
          <path
            d="M20 60h70l30-28 40 56 28-28h90"
            fill="none"
            stroke="#D97745"
            strokeWidth="3"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeDasharray="6 6"
            className="hf-flow-path"
          />
          <circle cx="20" cy="60" r="8" fill="#B6C28A" />
          <circle cx="278" cy="60" r="8" fill="#E8E2D4" />
          <circle cx="400" cy="60" r="8" fill="#A8A49A" />
        </svg>
      </section>
      <section className="auth-panel">
        <div className="auth-card">
          <Outlet />
        </div>
      </section>
    </div>
  );
}
