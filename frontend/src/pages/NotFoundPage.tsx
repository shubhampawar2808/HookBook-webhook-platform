import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="panel" style={{ maxWidth: 520, margin: "2rem auto" }}>
      <p className="eyebrow">404</p>
      <h1 style={{ fontSize: "2rem" }}>Page not found</h1>
      <p className="page-lede">That route is outside the HookForge observatory map.</p>
      <Link className="btn btn-primary" to="/" style={{ marginTop: "1rem", width: "fit-content" }}>
        Back to overview
      </Link>
    </div>
  );
}
