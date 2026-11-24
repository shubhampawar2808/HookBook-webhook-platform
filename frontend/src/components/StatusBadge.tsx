import type { DeliveryStatus } from "@/types/domain";

const LABELS: Record<string, string> = {
  pending: "Pending",
  processing: "Processing",
  retrying: "Retrying",
  succeeded: "Succeeded",
  failed: "Failed",
  dead_letter: "Dead letter",
  active: "Active",
  disabled: "Disabled",
  revoked: "Revoked",
  expired: "Expired",
  suspended: "Suspended",
  success: "Success",
  retryable_failure: "Retryable",
  permanent_failure: "Permanent",
};

const TONE: Record<string, string> = {
  pending: "neutral",
  processing: "info",
  retrying: "warning",
  succeeded: "success",
  failed: "danger",
  dead_letter: "danger",
  active: "success",
  disabled: "neutral",
  revoked: "danger",
  expired: "warning",
  suspended: "warning",
  success: "success",
  retryable_failure: "warning",
  permanent_failure: "danger",
};

type Props = {
  status: DeliveryStatus | string;
  className?: string;
};

export function StatusBadge({ status, className = "" }: Props) {
  const tone = TONE[status] || "neutral";
  return (
    <span className={`status-badge tone-${tone} ${className}`.trim()}>
      <span className="status-badge-dot" aria-hidden />
      {LABELS[status] || status}
    </span>
  );
}
