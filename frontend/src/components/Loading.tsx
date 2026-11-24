type Props = { label?: string; compact?: boolean };

export function Loading({ label = "Loading", compact }: Props) {
  return (
    <div className={`loading-block ${compact ? "compact" : ""}`} role="status" aria-live="polite">
      <span className="loading-meter" aria-hidden />
      <span>{label}</span>
    </div>
  );
}
