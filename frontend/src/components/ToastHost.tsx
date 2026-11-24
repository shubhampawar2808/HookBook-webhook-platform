import { useEffect } from "react";

import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { dismissToast } from "@/store/uiSlice";

export function ToastHost() {
  const toasts = useAppSelector((s) => s.ui.toasts);
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (!toasts.length) return;
    const latest = toasts[toasts.length - 1];
    const t = window.setTimeout(() => dispatch(dismissToast(latest.id)), 4200);
    return () => window.clearTimeout(t);
  }, [toasts, dispatch]);

  if (!toasts.length) return null;

  return (
    <div className="toast-host" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast tone-${toast.tone}`}>
          <div>
            <strong>{toast.title}</strong>
            {toast.message ? <p>{toast.message}</p> : null}
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-sm"
            aria-label="Dismiss"
            onClick={() => dispatch(dismissToast(toast.id))}
          >
            Close
          </button>
        </div>
      ))}
    </div>
  );
}
