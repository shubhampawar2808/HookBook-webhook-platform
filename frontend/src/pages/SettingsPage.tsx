import { FormEvent, useEffect, useState } from "react";

import { ErrorMessage } from "@/components/ErrorMessage";
import { Loading } from "@/components/Loading";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { StatusPage } from "@/pages/StatusPage";
import { ApiClientError } from "@/services/apiClient";
import { getOrganization, updateOrganization } from "@/services/orgService";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { pushToast } from "@/store/uiSlice";
import type { Organization } from "@/types/domain";
import { formatDateTime } from "@/utils/format";

export function SettingsPage() {
  const dispatch = useAppDispatch();
  const user = useAppSelector((s) => s.auth.user);
  const [org, setOrg] = useState<Organization | null>(null);
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await getOrganization();
      setOrg(data);
      setName(data.name);
      setSlug(data.slug);
    } catch (err) {
      setError(err instanceof ApiClientError ? err.message : "Failed to load organization");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    if (user?.role !== "owner") return;
    setBusy(true);
    try {
      const updated = await updateOrganization({ name: name.trim(), slug: slug.trim() });
      setOrg(updated);
      dispatch(pushToast({ tone: "success", title: "Organization updated" }));
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

  return (
    <div className="stack-gap">
      <PageHeader
        eyebrow="Workspace"
        title="Settings"
        description="Organization profile, operator identity, and verified system health."
      />

      {loading ? <Loading label="Loading settings" /> : null}
      {error ? <ErrorMessage message={error} onRetry={load} /> : null}

      {org ? (
        <section className="detail-grid">
          <form className="panel" onSubmit={onSave}>
            <h3 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>Organization</h3>
            <dl className="meta-strip">
              <div>
                <dt>Status</dt>
                <dd>
                  <StatusBadge status={org.status} />
                </dd>
              </div>
              <div>
                <dt>Created</dt>
                <dd>{formatDateTime(org.created_at)}</dd>
              </div>
            </dl>
            <div className="field">
              <label htmlFor="orgName">Name</label>
              <input
                id="orgName"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={user?.role !== "owner"}
              />
            </div>
            <div className="field">
              <label htmlFor="orgSlug">Slug</label>
              <input
                id="orgSlug"
                className="mono"
                value={slug}
                onChange={(e) => setSlug(e.target.value)}
                disabled={user?.role !== "owner"}
              />
            </div>
            {user?.role === "owner" ? (
              <button type="submit" className="btn btn-primary" disabled={busy}>
                {busy ? "Saving…" : "Save changes"}
              </button>
            ) : (
              <p className="muted">Only the organization owner can edit name and slug.</p>
            )}
          </form>

          <div className="panel">
            <h3 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>Signed-in operator</h3>
            <dl className="meta-strip">
              <div>
                <dt>Name</dt>
                <dd>{user?.full_name}</dd>
              </div>
              <div>
                <dt>Email</dt>
                <dd>{user?.email}</dd>
              </div>
              <div>
                <dt>Role</dt>
                <dd>{user?.role}</dd>
              </div>
            </dl>
          </div>
        </section>
      ) : null}

      <section className="panel">
        <h3 style={{ fontSize: "1.15rem", marginBottom: "0.75rem" }}>System status</h3>
        <StatusPage embedded />
      </section>
    </div>
  );
}
