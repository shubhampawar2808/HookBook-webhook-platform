import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import { getDelivery, listAttempts, replayDelivery } from "@/services/deliveriesService";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { Delivery, DeliveryAttempt } from "@/types/domain";
import { formatDateTime } from "@/utils/format";

export function DeliveryDetailPage() {
  const { deliveryId = "" } = useParams();
  const dispatch = useAppDispatch();
  const role = useAppSelector((s) => s.auth.user?.role);
  const [delivery, setDelivery] = useState<Delivery | null>(null);
  const [attempts, setAttempts] = useState<DeliveryAttempt[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [d, a] = await Promise.all([getDelivery(deliveryId), listAttempts(deliveryId)]);
      setDelivery(d);
      setAttempts(a);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load delivery");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [deliveryId]);

  async function onReplay() {
    setBusy(true);
    try {
      const result = await replayDelivery(deliveryId);
      setDelivery(result.delivery);
      dispatch(pushToast({ tone: "success", title: "Replay queued", message: result.message }));
      const a = await listAttempts(deliveryId);
      setAttempts(a);
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Replay failed",
          message: err instanceof ApiClientError ? err.message : "Error",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <Loading label="Loading delivery" />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!delivery) return null;

  const canReplay =
    (role === "owner" || role === "admin") &&
    (delivery.status === "failed" || delivery.status === "dead_letter");

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Delivery"
        title={delivery.id}
        description="Attempt timeline, HTTP outcomes, and replay controls."
        actions={
          canReplay ? (
            <button type="button" className="btn btn-primary" onClick={() => void onReplay()} disabled={busy}>
              {busy ? "Queuing…" : "Replay"}
            </button>
          ) : null
        }
      />

      <dl className="meta-strip">
        <div>
          <dt>Status</dt>
          <dd>
            <StatusBadge status={delivery.status} />
          </dd>
        </div>
        <div>
          <dt>Attempts</dt>
          <dd>
            {delivery.attempt_count}/{delivery.max_attempts}
          </dd>
        </div>
        <div>
          <dt>HTTP</dt>
          <dd>{delivery.last_http_status ?? "—"}</dd>
        </div>
        <div>
          <dt>Idempotency</dt>
          <dd>{delivery.idempotency_key}</dd>
        </div>
        <div>
          <dt>Event</dt>
          <dd>
            <Link to="/events">{delivery.event_id}</Link>
          </dd>
        </div>
        <div>
          <dt>Endpoint</dt>
          <dd>
            <Link to={`/endpoints/${delivery.endpoint_id}`}>{delivery.endpoint_id}</Link>
          </dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatDateTime(delivery.created_at)}</dd>
        </div>
        <div>
          <dt>Delivered</dt>
          <dd>{formatDateTime(delivery.delivered_at)}</dd>
        </div>
        <div>
          <dt>Replay count</dt>
          <dd>{delivery.replay_count}</dd>
        </div>
      </dl>

      <section className="detail-grid">
        <div className="panel">
          <h3 style={{ fontSize: "1.15rem", marginBottom: "1rem" }}>Attempt timeline</h3>
          {!attempts.length ? (
            <p className="muted">No attempts recorded yet.</p>
          ) : (
            <ol className="attempt-timeline">
              {attempts.map((attempt) => (
                <li key={attempt.id}>
                  <div className="attempt-index">{attempt.attempt_number}</div>
                  <div className="attempt-card">
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem" }}>
                      <StatusBadge status={attempt.outcome} />
                      <span className="mono muted">{attempt.duration_ms != null ? `${attempt.duration_ms}ms` : "—"}</span>
                    </div>
                    <div className="mono">HTTP {attempt.http_status ?? "—"}</div>
                    <div className="muted" style={{ fontSize: "0.85rem" }}>
                      {formatDateTime(attempt.started_at)}
                      {attempt.completed_at ? ` → ${formatDateTime(attempt.completed_at)}` : ""}
                    </div>
                    {attempt.error_message ? <p style={{ margin: 0 }}>{attempt.error_message}</p> : null}
                    {attempt.response_summary ? (
                      <pre className="json-surface" style={{ maxHeight: 160 }}>
                        {attempt.response_summary}
                      </pre>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
        <div className="panel">
          <h3 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>Last error / response</h3>
          <p className="muted">{delivery.last_error || "No error recorded."}</p>
          {delivery.response_summary ? (
            <pre className="json-surface" style={{ marginTop: "0.75rem" }}>
              {delivery.response_summary}
            </pre>
          ) : null}
          <p className="muted" style={{ marginTop: "1rem", fontSize: "0.85rem" }}>
            Next attempt: {formatDateTime(delivery.next_attempt_at)}
          </p>
        </div>
      </section>
    </div>
  );
}
