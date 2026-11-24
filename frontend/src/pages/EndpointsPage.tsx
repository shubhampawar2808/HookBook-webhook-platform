import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SecretReveal } from "@/components/SecretReveal";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import * as endpointsService from "@/services/endpointsService";
import { useAppDispatch } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { Endpoint } from "@/types/domain";
import { formatDateTime, shortId } from "@/utils/format";

export function EndpointsPage() {
  const dispatch = useAppDispatch();
  const [items, setItems] = useState<Endpoint[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("http://127.0.0.1:9999/hooks");
  const [description, setDescription] = useState("");
  const [secret, setSecret] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load(p = page) {
    setLoading(true);
    setError(null);
    try {
      const data = await endpointsService.listEndpoints(p, 20);
      setItems(data.items);
      setPage(data.page);
      setTotalPages(data.total_pages);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load endpoints");
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
      const created = await endpointsService.createEndpoint({
        name: name.trim(),
        url: url.trim(),
        description: description.trim() || undefined,
      });
      setSecret(created.signing_secret);
      setShowCreate(false);
      setName("");
      setDescription("");
      dispatch(pushToast({ tone: "success", title: "Endpoint created" }));
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
        eyebrow="Connectivity"
        title="Endpoints"
        description="Connection-oriented destinations for signed webhook delivery."
        actions={
          <button type="button" className="btn btn-primary" onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? "Close" : "New endpoint"}
          </button>
        }
      />

      {secret ? (
        <SecretReveal
          secret={secret}
          label="Signing secret"
          warning="This signing secret is shown only once. Store it with your receiver."
        />
      ) : null}

      {showCreate ? (
        <form className="panel" onSubmit={onCreate}>
          <div className="split-2">
            <div className="field">
              <label htmlFor="epName">Name</label>
              <input id="epName" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="epUrl">URL</label>
              <input id="epUrl" className="mono" value={url} onChange={(e) => setUrl(e.target.value)} required />
            </div>
          </div>
          <div className="field">
            <label htmlFor="epDesc">Description</label>
            <input id="epDesc" value={description} onChange={(e) => setDescription(e.target.value)} />
          </div>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Creating…" : "Create endpoint"}
          </button>
        </form>
      ) : null}

      {loading ? <Loading label="Loading endpoints" /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => load(page)} /> : null}

      {!loading && !error && !items.length ? (
        <EmptyState title="No endpoints" description="Create a destination URL to begin delivering events." />
      ) : null}

      {!loading && items.length ? (
        <>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>URL</th>
                  <th>Status</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((ep) => (
                  <tr key={ep.id}>
                    <td>
                      <div>{ep.name}</div>
                      <div className="mono muted">{shortId(ep.id)}</div>
                    </td>
                    <td className="mono" style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis" }}>
                      {ep.url}
                    </td>
                    <td>
                      <StatusBadge status={ep.status} />
                    </td>
                    <td className="mono">{formatDateTime(ep.updated_at)}</td>
                    <td>
                      <Link className="btn btn-ghost btn-sm" to={`/endpoints/${ep.id}`}>
                        Open
                      </Link>
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
