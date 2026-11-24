export type PageResponse<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
};

export type CurrentUser = {
  id: string;
  email: string;
  full_name: string;
  role: "owner" | "admin" | "member";
  organization_id: string;
  organization_name: string;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  status: "active" | "suspended";
  created_at: string;
  updated_at: string;
};

export type APIKey = {
  id: string;
  name: string;
  key_prefix: string;
  status: "active" | "revoked" | "expired";
  last_used_at: string | null;
  expires_at: string | null;
  created_by: string;
  created_at: string;
  revoked_at: string | null;
};

export type APIKeyCreateResponse = APIKey & { api_key: string };

export type Endpoint = {
  id: string;
  organization_id: string;
  name: string;
  url: string;
  description: string | null;
  status: "active" | "disabled";
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type EndpointCreateResponse = Endpoint & { signing_secret: string };

export type EventType = {
  id: string;
  organization_id: string;
  name: string;
  description: string | null;
  created_at: string;
};

export type Subscription = {
  id: string;
  organization_id: string;
  endpoint_id: string;
  event_type_id: string;
  status: "active" | "disabled";
  created_at: string;
};

export type EventResponse = {
  id: string;
  event_id: string;
  organization_id: string;
  event_type_id: string;
  payload: Record<string, unknown>;
  status: string;
  created_at: string;
  delivery: "accepted" | "none" | "enqueue_deferred";
  delivery_count: number;
};

export type DeliveryStatus =
  | "pending"
  | "processing"
  | "retrying"
  | "succeeded"
  | "failed"
  | "dead_letter";

export type Delivery = {
  id: string;
  organization_id: string;
  event_id: string;
  endpoint_id: string;
  status: DeliveryStatus;
  attempt_count: number;
  max_attempts: number;
  next_attempt_at: string | null;
  last_attempt_at: string | null;
  last_http_status: number | null;
  last_error: string | null;
  response_summary: string | null;
  idempotency_key: string;
  created_at: string;
  updated_at: string;
  delivered_at: string | null;
  replay_count: number;
  last_replayed_at: string | null;
};

export type DeliveryAttempt = {
  id: string;
  delivery_id: string;
  attempt_number: number;
  started_at: string;
  completed_at: string | null;
  http_status: number | null;
  response_summary: string | null;
  error_type: string | null;
  error_message: string | null;
  duration_ms: number | null;
  outcome: "success" | "retryable_failure" | "permanent_failure";
};

export type DeliveryReplayResponse = {
  delivery: Delivery;
  message: string;
};

export type HealthResponse = {
  status: "ok";
  app: string;
  version: string;
  environment: string;
};

export type ReadyCheck = {
  name: string;
  healthy: boolean;
  detail: string | null;
};

export type ReadyResponse = {
  status: "ready" | "not_ready";
  checks: ReadyCheck[];
};

export type MessageResponse = { message: string };
