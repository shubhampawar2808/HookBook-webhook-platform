import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";

import { clearAuthError, register } from "@/features/auth/authSlice";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";

export function RegisterPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const auth = useAppSelector((s) => s.auth);
  const [form, setForm] = useState({
    organization_name: "",
    organization_slug: "",
    email: "",
    password: "",
    full_name: "",
  });
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  if (auth.status === "authenticated") {
    return <Navigate to="/" replace />;
  }

  function set<K extends keyof typeof form>(key: K, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    dispatch(clearAuthError());
    if (
      !form.organization_name.trim() ||
      !form.organization_slug.trim() ||
      !form.email.trim() ||
      !form.password ||
      !form.full_name.trim()
    ) {
      setLocalError("All fields are required.");
      return;
    }
    if (form.password.length < 8) {
      setLocalError("Password must be at least 8 characters.");
      return;
    }
    const result = await dispatch(
      register({
        organization_name: form.organization_name.trim(),
        organization_slug: form.organization_slug.trim(),
        email: form.email.trim(),
        password: form.password,
        full_name: form.full_name.trim(),
      }),
    );
    if (register.fulfilled.match(result)) {
      navigate("/", { replace: true });
    }
  }

  return (
    <>
      <h2>Create workspace</h2>
      <p className="lede">Register an organization and owner account against the HookForge API.</p>
      <form onSubmit={onSubmit} noValidate>
        <div className="field">
          <label htmlFor="orgName">Organization name</label>
          <input id="orgName" value={form.organization_name} onChange={(e) => set("organization_name", e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="orgSlug">Organization slug</label>
          <input id="orgSlug" value={form.organization_slug} onChange={(e) => set("organization_slug", e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="fullName">Full name</label>
          <input id="fullName" value={form.full_name} onChange={(e) => set("full_name", e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" value={form.email} onChange={(e) => set("email", e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <div className="password-row">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              value={form.password}
              onChange={(e) => set("password", e.target.value)}
            />
            <button type="button" className="btn btn-ghost" onClick={() => setShowPassword((v) => !v)}>
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>
        </div>
        {(localError || auth.error) && (
          <p className="field-error" role="alert">
            {localError || auth.error}
          </p>
        )}
        <button type="submit" className="btn btn-primary" disabled={auth.status === "loading"} style={{ width: "100%" }}>
          {auth.status === "loading" ? "Creating…" : "Create workspace"}
        </button>
      </form>
      <p className="muted" style={{ marginTop: "1.25rem" }}>
        Already registered? <Link to="/login">Sign in</Link>
      </p>
    </>
  );
}
