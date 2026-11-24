import type { ConnectivityState } from "@/types/api";

const LABELS: Record<ConnectivityState, string> = {
  unknown: "Unknown",
  ok: "Connected",
  degraded: "Degraded",
  down: "Unreachable",
};

interface StatusPillProps {
  state: ConnectivityState;
}

export function StatusPill({ state }: StatusPillProps) {
  return <span className={`pill ${state}`}>{LABELS[state]}</span>;
}
