import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { NAV_ITEMS } from "@/layouts/navConfig";
import { useAppDispatch, useAppSelector } from "@/hooks/redux";
import { setCommandOpen } from "@/store/uiSlice";

export function CommandPalette() {
  const open = useAppSelector((s) => s.ui.commandOpen);
  const dispatch = useAppDispatch();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState(0);

  const items = useMemo(() => {
    const q = query.trim().toLowerCase();
    return NAV_ITEMS.filter((item) => !q || item.label.toLowerCase().includes(q));
  }, [query]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        dispatch(setCommandOpen(!open));
      }
      if (e.key === "Escape") dispatch(setCommandOpen(false));
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [dispatch, open]);

  useEffect(() => {
    setIndex(0);
  }, [query, open]);

  if (!open) return null;

  function go(to: string) {
    dispatch(setCommandOpen(false));
    setQuery("");
    navigate(to);
  }

  return (
    <div className="command-overlay" onMouseDown={() => dispatch(setCommandOpen(false))}>
      <div
        className="command-palette"
        role="dialog"
        aria-label="Command palette"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <input
          autoFocus
          placeholder="Jump to Overview, Deliveries, Dead Letter…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault();
              setIndex((i) => Math.min(i + 1, Math.max(items.length - 1, 0)));
            }
            if (e.key === "ArrowUp") {
              e.preventDefault();
              setIndex((i) => Math.max(i - 1, 0));
            }
            if (e.key === "Enter" && items[index]) go(items[index].to);
          }}
        />
        <ul className="command-list">
          {items.map((item, i) => (
            <li key={item.to}>
              <button
                type="button"
                aria-selected={i === index}
                onMouseEnter={() => setIndex(i)}
                onClick={() => go(item.to)}
              >
                {item.label}
              </button>
            </li>
          ))}
          {!items.length ? <li className="muted" style={{ padding: "0.75rem" }}>No matches</li> : null}
        </ul>
      </div>
    </div>
  );
}
