import { useEffect } from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { bootstrapAuth, logout } from "@/features/auth/authSlice";
import { Loading } from "@/components/Loading";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { setUnauthorizedHandler } from "@/services/apiClient";

export function RequireAuth() {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const { status, bootstrapped, token } = useAppSelector((s) => s.auth);

  useEffect(() => {
    if (!bootstrapped) {
      void dispatch(bootstrapAuth());
    }
  }, [bootstrapped, dispatch]);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      dispatch(logout());
    });
    return () => setUnauthorizedHandler(null);
  }, [dispatch]);

  if (!bootstrapped || status === "loading" || status === "idle") {
    return (
      <div style={{ padding: "3rem" }}>
        <Loading label="Restoring session" />
      </div>
    );
  }

  if (!token || status === "anonymous" || status === "error") {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
