import { useEffect } from "react";

import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { StatusPill } from "@/components/StatusPill";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { checkBackendStatus } from "@/store/statusSlice";
import { API_BASE_URL, APP_ENV } from "@/utils/config";

type Props = { embedded?: boolean };

export function StatusPage({ embedded = false }: Props) {
  const dispatch = useAppDispatch();
  const { loading, health, ready, connectivity, error, lastCheckedAt } =
    useAppSelector((state) => state.status);

  useEffect(() => {
    void dispatch(checkBackendStatus());
  }, [dispatch]);

  const refresh = () => {
    void dispatch(checkBackendStatus());
  };

  return (
    <div>
      {!embedded ? (
        <section className="panel" style={{ marginBottom: "1.25rem" }}>
          <p className="eyebrow">System</p>
          <h1 style={{ fontSize: "2rem" }}>HookForge</h1>
          <p className="page-lede">
            Independent webhook infrastructure — verified liveness and readiness probes only.
          </p>
          <div style={{ display: "flex", gap: "0.5rem", marginTop: "1rem" }}>
            <button type="button" className="btn btn-primary" onClick={refresh}>
              Refresh status
            </button>
            <a className="btn btn-ghost" href={`${API_BASE_URL}/docs`} target="_blank" rel="noreferrer">
              API docs
            </a>
          </div>
        </section>
      ) : (
        <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: "0.75rem" }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={refresh}>
            Refresh probes
          </button>
        </div>
      )}

      {loading && !health ? <Loading label="Checking backend connectivity…" compact={embedded} /> : null}

      {error && !health ? (
        <ErrorMessage title="Backend unreachable" message={error} onRetry={refresh} />
      ) : null}

      <section
        className="panel panel-tight"
        aria-label="Application status"
        style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: "0.75rem" }}
      >
        <div className="metric-cell">
          <p className="meta-label">Application</p>
          <p className="value" style={{ fontSize: "1.25rem" }}>
            {health?.app ?? "HookForge"}
          </p>
          <StatusPill state={connectivity === "unknown" && loading ? "unknown" : connectivity} />
        </div>
        <div className="metric-cell">
          <p className="meta-label">Backend connectivity</p>
          <p className="value" style={{ fontSize: "1.15rem" }}>
            {connectivity === "ok"
              ? "Healthy"
              : connectivity === "degraded"
                ? "Partially available"
                : connectivity === "down"
                  ? "Offline"
                  : "Checking…"}
          </p>
          <p className="muted mono" style={{ margin: 0, fontSize: "0.8rem" }}>
            {API_BASE_URL}
          </p>
        </div>
        <div className="metric-cell">
          <p className="meta-label">Environment</p>
          <p className="value" style={{ fontSize: "1.15rem" }}>
            {health?.environment ?? APP_ENV}
          </p>
          <p className="muted" style={{ margin: 0, fontSize: "0.8rem" }}>
            Frontend: {APP_ENV}
          </p>
        </div>
        <div className="metric-cell">
          <p className="meta-label">API version</p>
          <p className="value" style={{ fontSize: "1.15rem" }}>
            {health?.version ?? "—"}
          </p>
          <p className="muted" style={{ margin: 0, fontSize: "0.8rem" }}>
            Last check: {lastCheckedAt ? new Date(lastCheckedAt).toLocaleTimeString() : "—"}
          </p>
        </div>
      </section>

      {ready ? (
        <section className="panel" style={{ marginTop: "1rem" }}>
          <h2 style={{ marginTop: 0, fontSize: "1rem" }}>Dependency checks</h2>
          <div className="health-checks">
            {ready.checks.map((check) => (
              <div className="health-check" key={check.name}>
                <span>
                  <span className="mono">{check.name}</span>
                  <div className="muted" style={{ fontSize: "0.8rem" }}>
                    {check.detail || (check.healthy ? "healthy" : "unhealthy")}
                  </div>
                </span>
                <span className={check.healthy ? "status-badge tone-success" : "status-badge tone-danger"}>
                  {check.healthy ? "healthy" : "unhealthy"}
                </span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
