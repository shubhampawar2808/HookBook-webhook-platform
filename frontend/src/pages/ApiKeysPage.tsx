import { FormEvent, useEffect, useState } from "react";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EmptyState } from "@/components/EmptyState";
import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { Pagination } from "@/components/Pagination";
import { SecretReveal } from "@/components/SecretReveal";
import { StatusBadge } from "@/components/StatusBadge";
import { ApiClientError } from "@/services/apiClient";
import * as apiKeysService from "@/services/apiKeysService";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { APIKey } from "@/types/domain";
import { setPublishApiKey } from "@/features/auth/publishKeyStore";
import { formatDateTime, shortId } from "@/utils/format";

export function ApiKeysPage() {
  const dispatch = useAppDispatch();
  const role = useAppSelector((s) => s.auth.user?.role);
  const canManage = role === "owner" || role === "admin";
  const [items, setItems] = useState<APIKey[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [rawKey, setRawKey] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirm, setConfirm] = useState<{ type: "revoke" | "rotate"; id: string } | null>(null);

  async function load(p = page) {
    setLoading(true);
    setError(null);
    try {
      const data = await apiKeysService.listApiKeys(p, 20);
      setItems(data.items);
      setPage(data.page);
      setTotalPages(data.total_pages);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load API keys");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(1);
  }, []);

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (!canManage) return;
    setBusy(true);
    try {
      const created = await apiKeysService.createApiKey({ name: name.trim() || "publish-key" });
      setRawKey(created.api_key);
      setPublishApiKey(created.api_key);
      setName("");
      dispatch(pushToast({ tone: "success", title: "API key created" }));
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

  async function onConfirm() {
    if (!confirm) return;
    setBusy(true);
    try {
      if (confirm.type === "revoke") {
        await apiKeysService.revokeApiKey(confirm.id);
        dispatch(pushToast({ tone: "success", title: "API key revoked" }));
      } else {
        const rotated = await apiKeysService.rotateApiKey(confirm.id);
        setRawKey(rotated.api_key);
        setPublishApiKey(rotated.api_key);
        dispatch(pushToast({ tone: "success", title: "API key rotated" }));
      }
      setConfirm(null);
      await load(page);
    } catch (err) {
      dispatch(
        pushToast({
          tone: "danger",
          title: "Action failed",
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
        eyebrow="Credentials"
        title="API Keys"
        description="Secure machine credentials for event publishing. Raw secrets are shown once."
      />

      {rawKey ? (
        <SecretReveal
          secret={rawKey}
          label="API key secret"
          warning="Copy now. This value will not be shown again. It is kept in memory only for this tab session for Events publish."
        />
      ) : null}

      {canManage ? (
        <form className="panel" onSubmit={onCreate}>
          <div className="field" style={{ maxWidth: 360 }}>
            <label htmlFor="keyName">Key name</label>
            <input id="keyName" value={name} onChange={(e) => setName(e.target.value)} placeholder="publish-key" />
          </div>
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? "Creating…" : "Create API key"}
          </button>
        </form>
      ) : (
        <p className="muted">Only owners and admins can create, rotate, or revoke keys.</p>
      )}

      {loading ? <Loading label="Loading API keys" /> : null}
      {error ? <ErrorMessage message={error} onRetry={() => load(page)} /> : null}
      {!loading && !items.length ? (
        <EmptyState title="No API keys" description="Create a key to publish events from the console or your services." />
      ) : null}

      {items.length ? (
        <>
          <div className="data-table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Prefix</th>
                  <th>Status</th>
                  <th>Last used</th>
                  <th>Created</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((key) => (
                  <tr key={key.id}>
                    <td>
                      {key.name}
                      <div className="mono muted">{shortId(key.id)}</div>
                    </td>
                    <td className="mono">{key.key_prefix}</td>
                    <td>
                      <StatusBadge status={key.status} />
                    </td>
                    <td className="mono">{formatDateTime(key.last_used_at)}</td>
                    <td className="mono">{formatDateTime(key.created_at)}</td>
                    <td>
                      {canManage && key.status === "active" ? (
                        <div style={{ display: "flex", gap: "0.35rem" }}>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={() => setConfirm({ type: "rotate", id: key.id })}
                          >
                            Rotate
                          </button>
                          <button
                            type="button"
                            className="btn btn-danger btn-sm"
                            onClick={() => setConfirm({ type: "revoke", id: key.id })}
                          >
                            Revoke
                          </button>
                        </div>
                      ) : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} totalPages={totalPages} total={total} onChange={(p) => void load(p)} />
        </>
      ) : null}

      <ConfirmDialog
        open={Boolean(confirm)}
        title={confirm?.type === "rotate" ? "Rotate API key?" : "Revoke API key?"}
        body={
          confirm?.type === "rotate"
            ? "The previous secret stops working immediately. A new secret will be shown once."
            : "Revoked keys cannot publish events. This cannot be undone."
        }
        confirmLabel={confirm?.type === "rotate" ? "Rotate" : "Revoke"}
        danger={confirm?.type === "revoke"}
        busy={busy}
        onCancel={() => setConfirm(null)}
        onConfirm={() => void onConfirm()}
      />
    </div>
  );
}
