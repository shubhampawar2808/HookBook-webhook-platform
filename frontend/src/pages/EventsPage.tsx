import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { JsonViewer } from "@/components/JsonViewer";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import { listDeliveries } from "@/services/deliveriesService";
import { listEventTypes } from "@/services/eventTypesService";
import { publishEvent } from "@/services/eventsService";
import { useAppDispatch } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { Delivery, EventResponse, EventType } from "@/types/domain";
import { getPublishApiKey, setPublishApiKey } from "@/features/auth/publishKeyStore";
import { formatDateTime, shortId } from "@/utils/format";

type EventRow = {
  event_id: string;
  delivery_count: number;
  latest_status: string;
  created_at: string;
  statuses: string[];
};

export function EventsPage() {
  const dispatch = useAppDispatch();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [rows, setRows] = useState<EventRow[]>([]);
  const [types, setTypes] = useState<EventType[]>([]);
  const [selected, setSelected] = useState<EventRow | null>(null);
  const [related, setRelated] = useState<Delivery[]>([]);
  const [apiKey, setApiKey] = useState(() => getPublishApiKey() || "");
  const [eventType, setEventType] = useState("");
  const [payloadText, setPayloadText] = useState('{\n  "hello": "hookforge"\n}');
  const [publishing, setPublishing] = useState(false);
  const [lastPublish, setLastPublish] = useState<EventResponse | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [deliveries, eventTypes] = await Promise.all([
        listDeliveries({ page: 1, page_size: 100 }),
        listEventTypes(1, 100),
      ]);
      setTypes(eventTypes.items);
      if (!eventType && eventTypes.items[0]) setEventType(eventTypes.items[0].name);
      const map = new Map<string, EventRow>();
      for (const d of deliveries.items) {
        const existing = map.get(d.event_id);
        if (!existing) {
          map.set(d.event_id, {
            event_id: d.event_id,
            delivery_count: 1,
            latest_status: d.status,
            created_at: d.created_at,
            statuses: [d.status],
          });
        } else {
          existing.delivery_count += 1;
          existing.statuses.push(d.status);
          if (d.created_at > existing.created_at) {
            existing.created_at = d.created_at;
            existing.latest_status = d.status;
          }
        }
      }
      setRows([...map.values()].sort((a, b) => b.created_at.localeCompare(a.created_at)));
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load events");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  useEffect(() => {
    if (!selected) {
      setRelated([]);
      return;
    }
    void listDeliveries({ page: 1, page_size: 50, event_id: selected.event_id }).then((page) => {
      setRelated(page.items);
    });
  }, [selected]);

  const limitation = useMemo(
    () =>
      "No GET /events API exists. This ledger is derived from recent deliveries (up to 100). Publish uses an API key (hfk_…), not your JWT.",
    [],
  );

  async function onPublish(e: FormEvent) {
    e.preventDefault();
    setPublishing(true);
    try {
      let payload: Record<string, unknown> = {};
      try {
        payload = JSON.parse(payloadText) as Record<string, unknown>;
      } catch {
        throw new Error("Payload must be valid JSON");
      }
      if (!apiKey.startsWith("hfk_")) {
        throw new Error("Publish requires an API key starting with hfk_");
      }
      setPublishApiKey(apiKey);
      const result = await publishEvent(apiKey, { event_type: eventType, payload });
      setLastPublish(result);
      dispatch(
        pushToast({
          tone: "success",
          title: "Event published",
          message: `${result.delivery_count} delivery record(s)`,
        }),
      );
      await load();
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Publish failed",
          message: err instanceof Error ? err.message : "Unknown error",
        }),
      );
    } finally {
      setPublishing(false);
    }
  }

  if (loading) return <Loading label="Loading event ledger" />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Ingress"
        title="Events"
        description="Technical event ledger derived from delivery activity, with API-key publishing."
      />

      <p className="muted">{limitation}</p>

      <section className="detail-grid">
        <div className="panel">
          <h3 style={{ marginBottom: "0.75rem", fontSize: "1.15rem" }}>Recent events</h3>
          {!rows.length ? (
            <EmptyState
              title="No events observed"
              description="Publish an event or wait for deliveries to appear."
            />
          ) : (
            <div className="data-table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Event ID</th>
                    <th>Deliveries</th>
                    <th>Latest status</th>
                    <th>Seen at</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.event_id}>
                      <td>
                        <button
                          type="button"
                          className="btn btn-ghost btn-sm mono"
                          onClick={() => setSelected(row)}
                        >
                          {shortId(row.event_id, 12)}
                        </button>
                      </td>
                      <td className="mono">{row.delivery_count}</td>
                      <td>
                        <StatusBadge status={row.latest_status} />
                      </td>
                      <td className="mono">{formatDateTime(row.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="stack-gap">
          <form className="panel" onSubmit={onPublish}>
            <h3 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>Publish event</h3>
            <div className="field">
              <label htmlFor="apiKey">API key (session only)</label>
              <input
                id="apiKey"
                className="mono"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="hfk_…"
                autoComplete="off"
              />
            </div>
            <div className="field">
              <label htmlFor="eventType">Event type</label>
              <select id="eventType" value={eventType} onChange={(e) => setEventType(e.target.value)}>
                {types.map((t) => (
                  <option key={t.id} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="payload">Payload JSON</label>
              <textarea id="payload" value={payloadText} onChange={(e) => setPayloadText(e.target.value)} />
            </div>
            <button type="submit" className="btn btn-primary" disabled={publishing || !types.length}>
              {publishing ? "Publishing…" : "Publish"}
            </button>
          </form>

          {lastPublish ? (
            <div className="panel">
              <p className="meta-label">Last publish</p>
              <dl className="meta-strip">
                <div>
                  <dt>Event</dt>
                  <dd>{shortId(lastPublish.id)}</dd>
                </div>
                <div>
                  <dt>Delivery</dt>
                  <dd>{lastPublish.delivery}</dd>
                </div>
                <div>
                  <dt>Count</dt>
                  <dd>{lastPublish.delivery_count}</dd>
                </div>
              </dl>
              <JsonViewer value={lastPublish.payload} label="Payload" />
            </div>
          ) : null}

          {selected ? (
            <div className="panel">
              <p className="meta-label">Selected event</p>
              <h3 className="mono" style={{ fontSize: "1rem", margin: "0.35rem 0 0.75rem" }}>
                {selected.event_id}
              </h3>
              <p className="muted">Related deliveries</p>
              <ul className="activity-list">
                {related.map((d) => (
                  <li key={d.id}>
                    <Link to={`/deliveries/${d.id}`}>
                      <span className="mono">{shortId(d.id)}</span>
                    </Link>
                    <StatusBadge status={d.status} />
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </section>
    </div>
  );
}
