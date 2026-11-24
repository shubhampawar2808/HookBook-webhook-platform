import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import { listDeadLetter, replayDelivery } from "@/services/deliveriesService";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { Delivery } from "@/types/domain";
import { formatDateTime, shortId } from "@/utils/format";

export function DeadLetterPage() {
  const dispatch = useAppDispatch();
  const role = useAppSelector((s) => s.auth.user?.role);
  const canReplay = role === "owner" || role === "admin";
  const [items, setItems] = useState<Delivery[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load(p = page) {
    setLoading(true);
    setError(null);
    try {
      const data = await listDeadLetter(p, 20);
      setItems(data.items);
      setPage(data.page);
      setTotalPages(data.total_pages);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load dead letter queue");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(1);
  }, []);

  async function onReplay(id: string) {
    setBusyId(id);
    try {
      await replayDelivery(id);
      dispatch(pushToast({ tone: "success", title: "Replay queued" }));
      await load(page);
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Replay failed",
          message: err instanceof ApiClientError ? err.message : "Error",
        }),
      );
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Exceptions"
        title="Dead Letter Queue"
        description="Focused workspace for exhausted deliveries and controlled replay."
      />

      {loading ? <Loading label="Loading dead letter queue" /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => load(page)} /> : null}
      {!loading && !items.length ? (
        <EmptyState title="Queue clear" description="No dead-letter deliveries in this workspace." />
      ) : null}

      {items.length ? (
        <>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Delivery</th>
                  <th>Failure</th>
                  <th>Attempts</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((d) => (
                  <tr key={d.id}>
                    <td>
                      <Link className="mono" to={`/deliveries/${d.id}`}>
                        {shortId(d.id, 10)}
                      </Link>
                      <div>
                        <StatusBadge status={d.status} />
                      </div>
                    </td>
                    <td>
                      <div>HTTP {d.last_http_status ?? "—"}</div>
                      <div className="muted" style={{ fontSize: "0.85rem" }}>
                        {d.last_error || "No error summary"}
                      </div>
                    </td>
                    <td className="mono">
                      {d.attempt_count}/{d.max_attempts}
                    </td>
                    <td className="mono">{formatDateTime(d.updated_at)}</td>
                    <td>
                      {canReplay ? (
                        <button
                          type="button"
                          className="btn btn-primary btn-sm"
                          disabled={busyId === d.id}
                          onClick={() => void onReplay(d.id)}
                        >
                          {busyId === d.id ? "…" : "Replay"}
                        </button>
                      ) : (
                        <span className="muted">Owner/Admin</span>
                      )}
                    </td>
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
