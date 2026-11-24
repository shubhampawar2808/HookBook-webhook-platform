import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import { listEndpoints, listSubscriptions } from "@/services/endpointsService";
import { listEventTypes } from "@/services/eventTypesService";
import type { Endpoint, EventType, Subscription } from "@/types/domain";
import { formatDateTime, shortId } from "@/utils/format";

type Row = Subscription & { endpoint?: Endpoint; eventTypeName?: string };

export function SubscriptionsPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [endpointsPage, typesPage] = await Promise.all([
        listEndpoints(1, 100),
        listEventTypes(1, 100),
      ]);
      const typeMap = new Map<string, EventType>(typesPage.items.map((t) => [t.id, t]));
      const collected: Row[] = [];
      for (const ep of endpointsPage.items) {
        const subs = await listSubscriptions(ep.id, 1, 100);
        for (const sub of subs.items) {
          collected.push({
            ...sub,
            endpoint: ep,
            eventTypeName: typeMap.get(sub.event_type_id)?.name,
          });
        }
      }
      setRows(collected);
      setNote(
        endpointsPage.total > endpointsPage.items.length
          ? `Showing subscriptions for the first ${endpointsPage.items.length} of ${endpointsPage.total} endpoints.`
          : "Aggregated from endpoint subscription lists (no top-level subscriptions API).",
      );
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load subscriptions");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  if (loading) return <Loading label="Aggregating subscriptions" />;
  if (error) return <ErrorMessage message={error} onRetry={load} />;

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Routing"
        title="Subscriptions"
        description="Active event-type bindings across webhook endpoints."
        actions={
          <Link className="btn btn-primary" to="/endpoints">
            Manage via endpoints
          </Link>
        }
      />
      <p className="muted">{note}</p>
      {!rows.length ? (
        <EmptyState
          title="No subscriptions"
          description="Open an endpoint and attach an event type to create a subscription."
          action={
            <Link className="btn btn-primary" to="/endpoints">
              Go to endpoints
            </Link>
          }
        />
      ) : (
        <div className="data-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Endpoint</th>
                <th>Event type</th>
                <th>Status</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <Link to={`/endpoints/${row.endpoint_id}`}>{row.endpoint?.name || shortId(row.endpoint_id)}</Link>
                    <div className="mono muted" style={{ fontSize: "0.78rem" }}>
                      {row.endpoint?.url}
                    </div>
                  </td>
                  <td className="mono">{row.eventTypeName || shortId(row.event_type_id)}</td>
                  <td>
                    <StatusBadge status={row.status} />
                  </td>
                  <td className="mono">{formatDateTime(row.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
