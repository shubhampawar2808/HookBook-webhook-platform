import { FormEvent, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { ApiClientError } from "@/services/apiClient";
import * as eventTypesService from "@/services/eventTypesService";
import { useAppDispatch } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { EventType } from "@/types/domain";
import { formatDateTime, shortId } from "@/utils/format";

export function EventTypesPage() {
  const dispatch = useAppDispatch();
  const [items, setItems] = useState<EventType[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(p = page) {
    setLoading(true);
    setError(null);
    try {
      const data = await eventTypesService.listEventTypes(p, 20);
      setItems(data.items);
      setPage(data.page);
      setTotalPages(data.total_pages);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load event types");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(1);
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await eventTypesService.createEventType({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      setName("");
      setDescription("");
      dispatch(pushToast({ tone: "success", title: "Event type created" }));
      await load(1);
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Create failed",
          message: err instanceof ApiClientError ? err.message : "Error",
        }),
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Catalog"
        title="Event Types"
        description="Named event contracts used for subscription matching and publish."
      />

      <form className="panel" onSubmit={onCreate}>
        <div className="split-2">
          <div className="field">
            <label htmlFor="etName">Name</label>
            <input
              id="etName"
              className="mono"
              placeholder="order.created"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="etDesc">Description</label>
            <input id="etDesc" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
        </div>
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "Creating…" : "Create event type"}
        </button>
      </form>

      {loading ? <Loading label="Loading event types" /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => load(page)} /> : null}
      {!loading && !items.length ? (
        <EmptyState title="No event types" description="Create a type such as order.created to begin." />
      ) : null}

      {items.length ? (
        <>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>ID</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {items.map((et) => (
                  <tr key={et.id}>
                    <td className="mono">{et.name}</td>
                    <td>{et.description || "—"}</td>
                    <td className="mono muted">{shortId(et.id)}</td>
                    <td className="mono">{formatDateTime(et.created_at)}</td>
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
