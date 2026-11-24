import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import * as endpointsService from "@/services/endpointsService";
import { listEventTypes } from "@/services/eventTypesService";
import { useAppDispatch } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { Endpoint, EventType, Subscription } from "@/types/domain";
import { formatDateTime } from "@/utils/format";

export function EndpointDetailPage() {
  const { endpointId = "" } = useParams();
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const [endpoint, setEndpoint] = useState<Endpoint | null>(null);
  const [subs, setSubs] = useState<Subscription[]>([]);
  const [types, setTypes] = useState<EventType[]>([]);
  const [eventTypeId, setEventTypeId] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [ep, subscriptions, eventTypes] = await Promise.all([
        endpointsService.getEndpoint(endpointId),
        endpointsService.listSubscriptions(endpointId, 1, 100),
        listEventTypes(1, 100),
      ]);
      setEndpoint(ep);
      setSubs(subscriptions.items);
      setTypes(eventTypes.items);
      if (eventTypes.items[0]) setEventTypeId(eventTypes.items[0].id);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load endpoint");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [endpointId]);

  async function toggleStatus() {
    if (!endpoint) return;
    setBusy(true);
    try {
      const next = endpoint.status === "active" ? "disabled" : "active";
      const updated = await endpointsService.updateEndpoint(endpoint.id, { status: next });
      setEndpoint(updated);
      dispatch(pushToast({ tone: "success", title: `Endpoint ${next}` }));
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Update failed",
          message: err instanceof ApiClientError ? err.message : "Error",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  async function onSubscribe(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await endpointsService.createSubscription(endpointId, eventTypeId);
      dispatch(pushToast({ tone: "success", title: "Subscription created" }));
      await load();
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Subscribe failed",
          message: err instanceof ApiClientError ? err.message : "Error",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  async function removeSub(subId: string) {
    setBusy(true);
    try {
      await endpointsService.deleteSubscription(endpointId, subId);
      dispatch(pushToast({ tone: "success", title: "Subscription removed" }));
      await load();
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Remove failed",
          message: err instanceof ApiClientError ? err.message : "Error",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  async function onDelete() {
    setBusy(true);
    try {
      await endpointsService.deleteEndpoint(endpointId);
      dispatch(pushToast({ tone: "success", title: "Endpoint deleted" }));
      navigate("/endpoints");
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Delete failed",
          message: err instanceof ApiClientError ? err.message : "Error",
        }),
      );
      setBusy(false);
      setConfirmDelete(false);
    }
  }

  if (loading) return <Loading label="Loading endpoint" />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;
  if (!endpoint) return null;

  const typeName = (id: string) => types.find((t) => t.id === id)?.name || id;

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Endpoint"
        title={endpoint.name}
        description={endpoint.description || "Webhook destination"}
        actions={
          <>
            <button type="button" className="btn btn-ghost" onClick={toggleStatus} disabled={busy}>
              {endpoint.status === "active" ? "Disable" : "Enable"}
            </button>
            <button type="button" className="btn btn-danger" onClick={() => setConfirmDelete(true)}>
              Delete
            </button>
          </>
        }
      />

      <dl className="meta-strip">
        <div>
          <dt>Status</dt>
          <dd>
            <StatusBadge status={endpoint.status} />
          </dd>
        </div>
        <div>
          <dt>URL</dt>
          <dd>{endpoint.url}</dd>
        </div>
        <div>
          <dt>Created</dt>
          <dd>{formatDateTime(endpoint.created_at)}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>{formatDateTime(endpoint.updated_at)}</dd>
        </div>
      </dl>

      <section className="detail-grid">
        <div className="panel">
          <h3 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>Subscriptions</h3>
          {!subs.length ? (
            <EmptyState title="No subscriptions" description="Attach event types to start matching deliveries." />
          ) : (
            <ul className="activity-list">
              {subs.map((sub) => (
                <li key={sub.id}>
                  <div>
                    <div className="mono">{typeName(sub.event_type_id)}</div>
                    <div className="muted" style={{ fontSize: "0.82rem" }}>
                      {formatDateTime(sub.created_at)}
                    </div>
                  </div>
                  <button type="button" className="btn btn-ghost btn-sm" onClick={() => void removeSub(sub.id)}>
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <form className="panel" onSubmit={onSubscribe}>
          <h3 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>Add subscription</h3>
          <div className="field">
            <label htmlFor="etype">Event type</label>
            <select id="etype" value={eventTypeId} onChange={(e) => setEventTypeId(e.target.value)}>
              {types.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
          </div>
          <button type="submit" className="btn btn-primary" disabled={busy || !types.length}>
            Subscribe
          </button>
          <p className="muted" style={{ marginTop: "0.75rem" }}>
            Manage catalog on <Link to="/event-types">Event Types</Link>.
          </p>
        </form>
      </section>

      <ConfirmDialog
        open={confirmDelete}
        title="Delete endpoint?"
        body="This permanently removes the endpoint and its subscriptions."
        confirmLabel="Delete"
        danger
        busy={busy}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => void onDelete()}
      />
    </div>
  );
}
