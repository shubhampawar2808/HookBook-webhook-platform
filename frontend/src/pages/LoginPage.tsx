import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";

import { clearAuthError, login } from "@/features/auth/authSlice";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";

export function LoginPage() {
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const location = useLocation();
  const auth = useAppSelector((s) => s.auth);
  const [organizationSlug, setOrganizationSlug] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  if (auth.status === "authenticated") {
    const dest = (location.state as { from?: string } | null)?.from || "/";
    return <Navigate to={dest} replace />;
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLocalError(null);
    dispatch(clearAuthError());
    if (!organizationSlug.trim() || !email.trim() || !password) {
      setLocalError("Organization slug, email, and password are required.");
      return;
    }
    const result = await dispatch(
      login({
        organization_slug: organizationSlug.trim(),
        email: email.trim(),
        password,
      }),
    );
    if (login.fulfilled.match(result)) {
      navigate("/", { replace: true });
    }
  }

  return (
    <>
      <h2>Sign in</h2>
      <p className="lede">Access your HookForge workspace with organization credentials.</p>
      <form onSubmit={onSubmit} noValidate>
        <div className="field">
          <label htmlFor="org">Organization slug</label>
          <input
            id="org"
            autoComplete="organization"
            value={organizationSlug}
            onChange={(e) => setOrganizationSlug(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="username"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Password</label>
          <div className="password-row">
            <input
              id="password"
              type={showPassword ? "text" : "password"}
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
          {auth.status === "loading" ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="muted" style={{ marginTop: "1.25rem" }}>
        Need a workspace? <Link to="/register">Create organization</Link>
      </p>
    </>
  );
}
