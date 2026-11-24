import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import { listDeliveries } from "@/services/deliveriesService";
import type { Delivery, DeliveryStatus } from "@/types/domain";
import { formatDateTime, shortId } from "@/utils/format";

const STATUSES: Array<DeliveryStatus | ""> = [
  "",
  "pending",
  "processing",
  "retrying",
  "succeeded",
  "failed",
  "dead_letter",
];

export function DeliveriesPage() {
  const [items, setItems] = useState<Delivery[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState<DeliveryStatus | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load(p = page, st = status) {
    setLoading(true);
    setError(null);
    try {
      const data = await listDeliveries({
        page: p,
        page_size: 20,
        status: st || undefined,
      });
      setItems(data.items);
      setPage(data.page);
      setTotalPages(data.total_pages);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load deliveries");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(1, status);
  }, [status]);

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Inspection"
        title="Deliveries"
        description="Technical delivery console with status filters and attempt history."
      />

      <div className="filters">
        <div className="field">
          <label htmlFor="status">Status</label>
          <select
            id="status"
            value={status}
            onChange={(e) => setStatus(e.target.value as DeliveryStatus | "")}
          >
            <option value="">All</option>
            {STATUSES.filter(Boolean).map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading ? <Loading label="Loading deliveries" /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => load(page)} /> : null}
      {!loading && !items.length ? (
        <EmptyState title="No deliveries" description="Publish an event with an active subscription to create deliveries." />
      ) : null}

      {items.length ? (
        <>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Delivery</th>
                  <th>Event</th>
                  <th>Status</th>
                  <th>Attempts</th>
                  <th>HTTP</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <Link className="mono" to={`/deliveries/${d.id}`}>
                        {shortId(d.id, 10)}
                      </Link>
                    </td>
                    <td className="mono muted">{shortId(d.event_id, 10)}</td>
                    <td>
                      <StatusBadge status={d.status} />
                    </td>
                    <td className="mono">
                      {d.attempt_count}/{d.max_attempts}
                    </td>
                    <td className="mono">{d.last_http_status ?? "—"}</td>
                    <td className="mono">{formatDateTime(d.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} totalPages={totalPages} total={total} onChange={(p) => void load(p)} />
        </>
      ) : null}
    </div>
  );
}
