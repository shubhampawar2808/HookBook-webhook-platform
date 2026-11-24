import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { listDeliveries } from "@/services/deliveriesService";
import { listEndpoints } from "@/services/endpointsService";
import { checkBackendStatus } from "@/store/statusSlice";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import type { Delivery } from "@/types/domain";
import { formatRelative, percent, shortId } from "@/utils/format";
import { ApiClientError } from "@/services/apiClient";

type Metrics = {
  deliveriesTotal: number;
  succeeded: number;
  failed: number;
  deadLetter: number;
  retrying: number;
  pending: number;
  activeEndpoints: number;
  endpointsTotal: number;
  sample: Delivery[];
  note: string;
};

export function OverviewPage() {
  const dispatch = useAppDispatch();
  const status = useAppSelector((s) => s.status);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<Metrics | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      void dispatch(checkBackendStatus());
      const [all, succeeded, failed, dead, endpoints] = await Promise.all([
        listDeliveries({ page: 1, page_size: 100 }),
        listDeliveries({ page: 1, page_size: 1, status: "succeeded" }),
        listDeliveries({ page: 1, page_size: 1, status: "failed" }),
        listDeliveries({ page: 1, page_size: 1, status: "dead_letter" }),
        listEndpoints(1, 100),
      ]);
      const retrying = all.items.filter((d) => d.status === "retrying").length;
      const pending = all.items.filter((d) => d.status === "pending" || d.status === "processing").length;
      setMetrics({
        deliveriesTotal: all.total,
        succeeded: succeeded.total,
        failed: failed.total,
        deadLetter: dead.total,
        retrying,
        pending,
        activeEndpoints: endpoints.items.filter((e) => e.status === "active").length,
        endpointsTotal: endpoints.total,
        sample: all.items,
        note:
          "Totals use delivery list filters (accurate counts). Status distribution bars use the latest page of up to 100 deliveries — not a full historical series.",
      });
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load overview");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const recentFailures = useMemo(
    () => metrics?.sample.filter((d) => d.status === "failed" || d.status === "dead_letter").slice(0, 6) || [],
    [metrics],
  );

  const uniqueEvents = useMemo(() => {
    if (!metrics) return 0;
    return new Set(metrics.sample.map((d) => d.event_id)).size;
  }, [metrics]);

  if (loading) return <Loading label="Assembling observatory" />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!metrics) return null;

  const terminal = metrics.succeeded + metrics.failed + metrics.deadLetter;
  const successRate = percent(metrics.succeeded, terminal || metrics.deliveriesTotal);

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Observatory"
        title="Overview"
        description="Monitor webhook activity, delivery reliability, and endpoint health."
      />

      <section className="observatory-grid">
        <div className="metric-editorial">
          <div className="metric-hero panel">
            <p className="meta-label">Delivery success rate</p>
            <p className="value">{successRate}</p>
            <p className="muted">
              {metrics.succeeded} succeeded of {terminal || metrics.deliveriesTotal} terminal outcomes
            </p>
          </div>
          <div className="metric-row panel panel-tight">
            <div className="metric-cell">
              <p className="meta-label">Deliveries</p>
              <p className="value">{metrics.deliveriesTotal}</p>
            </div>
            <div className="metric-cell positive">
              <p className="meta-label">Succeeded</p>
              <p className="value">{metrics.succeeded}</p>
            </div>
            <div className="metric-cell">
              <p className="meta-label">Active endpoints</p>
              <p className="value">
                {metrics.activeEndpoints}
                <span className="muted" style={{ fontSize: "0.9rem" }}>
                  {" "}
                  / {metrics.endpointsTotal}
                </span>
              </p>
            </div>
          </div>
        </div>

        <div className="panel flow-panel">
          <div>
            <p className="meta-label">Event flow</p>
            <h2 style={{ fontSize: "1.35rem", marginTop: "0.35rem" }}>Ingress → Attempt → Outcome</h2>
          </div>
          <svg className="flow-svg" viewBox="0 0 360 110" role="img" aria-label="Delivery flow motif">
            <path
              d="M16 55h70l26-24 34 48 24-24h90"
              fill="none"
              stroke="#D97745"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeDasharray="5 5"
            />
            <circle cx="16" cy="55" r="7" fill="#B6C28A" />
            <circle cx="260" cy="55" r="7" fill="#E8E2D4" />
            <circle cx="340" cy="55" r="7" fill="#A8A49A" />
            <text x="8" y="90" fill="#A8A49A" fontSize="10" fontFamily="JetBrains Mono, monospace">
              event
            </text>
            <text x="240" y="90" fill="#A8A49A" fontSize="10" fontFamily="JetBrains Mono, monospace">
              delivery
            </text>
            <text x="312" y="90" fill="#A8A49A" fontSize="10" fontFamily="JetBrains Mono, monospace">
              endpoint
            </text>
          </svg>
          <p className="muted" style={{ margin: 0, fontSize: "0.88rem" }}>
            Sample window includes {uniqueEvents} distinct event IDs from the latest delivery page.
            There is no aggregate events API yet — event totals beyond this sample are unavailable.
          </p>
        </div>
      </section>

      <section className="split-2">
        <div className="panel">
          <p className="meta-label">Status distribution</p>
          <h3 style={{ margin: "0.35rem 0 1rem", fontSize: "1.2rem" }}>Latest delivery page</h3>
          <div className="dist-bars">
            <Bar label="Succeeded" value={metrics.sample.filter((d) => d.status === "succeeded").length} total={metrics.sample.length} tone="sage" />
            <Bar label="Failed" value={metrics.sample.filter((d) => d.status === "failed").length} total={metrics.sample.length} tone="danger" />
            <Bar label="Dead letter" value={metrics.sample.filter((d) => d.status === "dead_letter").length} total={metrics.sample.length} tone="danger" />
            <Bar label="Retrying" value={metrics.retrying} total={metrics.sample.length} tone="warn" />
            <Bar label="In flight" value={metrics.pending} total={metrics.sample.length} tone="info" />
          </div>
          <p className="muted" style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
            {metrics.note}
          </p>
        </div>

        <div className="panel">
          <p className="meta-label">Operational health</p>
          <h3 style={{ margin: "0.35rem 0 1rem", fontSize: "1.2rem" }}>Verified probes</h3>
          {status.loading && !status.health ? <Loading compact label="Checking" /> : null}
          <div className="health-checks">
            <div className="health-check">
              <span>API liveness</span>
              <StatusBadge status={status.health?.status === "ok" ? "succeeded" : "failed"} />
            </div>
            {(status.ready?.checks || []).map((check) => (
              <div className="health-check" key={check.name}>
                <span>
                  {check.name}
                  <div className="muted" style={{ fontSize: "0.8rem" }}>
                    {check.detail}
                  </div>
                </span>
                <StatusBadge status={check.healthy ? "succeeded" : "failed"} />
              </div>
            ))}
            {!status.ready && status.connectivity === "degraded" ? (
              <p className="muted">Readiness probe unavailable or degraded.</p>
            ) : null}
            {status.connectivity === "down" ? (
              <ErrorMessage title="API unreachable" message={status.error || "Backend down"} onRetry={() => dispatch(checkBackendStatus())} />
            ) : null}
          </div>
        </div>
      </section>

      <section className="split-2">
        <div className="panel">
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
            <h3 style={{ fontSize: "1.15rem" }}>Recent deliveries</h3>
            <Link to="/deliveries">View all</Link>
          </div>
          <ul className="activity-list">
            {metrics.sample.slice(0, 8).map((d) => (
              <li key={d.id}>
                <Link to={`/deliveries/${d.id}`}>
                  <div className="mono">{shortId(d.id)}</div>
                  <div className="muted" style={{ fontSize: "0.82rem" }}>
                    event {shortId(d.event_id)} · {formatRelative(d.created_at)}
                  </div>
                </Link>
                <StatusBadge status={d.status} />
              </li>
            ))}
            {!metrics.sample.length ? <li className="muted">No deliveries yet.</li> : null}
          </ul>
        </div>
        <div className="panel">
          <div style={{ display: "flex", justifyContent: "space-between", gap: "1rem" }}>
            <h3 style={{ fontSize: "1.15rem" }}>Recent failures</h3>
            <Link to="/dead-letter">Dead letter</Link>
          </div>
          <ul className="activity-list">
            {recentFailures.map((d) => (
              <li key={d.id}>
                <Link to={`/deliveries/${d.id}`}>
                  <div className="mono">{shortId(d.id)}</div>
                  <div className="muted" style={{ fontSize: "0.82rem" }}>
                    HTTP {d.last_http_status ?? "—"} · {d.last_error || "No error summary"}
                  </div>
                </Link>
                <StatusBadge status={d.status} />
              </li>
            ))}
            {!recentFailures.length ? <li className="muted">No failures in the latest sample.</li> : null}
          </ul>
        </div>
      </section>
    </div>
  );
}

function Bar({
  label,
  value,
  total,
  tone,
}: {
  label: string;
  value: number;
  total: number;
  tone: string;
}) {
  const width = total > 0 ? Math.max(2, Math.round((value / total) * 100)) : 0;
  return (
    <div className="dist-row">
      <span>{label}</span>
      <div className="dist-track">
        <div className={`dist-fill ${tone}`} style={{ width: `${width}%` }} />
      </div>
      <span className="mono">{value}</span>
    </div>
  );
}
