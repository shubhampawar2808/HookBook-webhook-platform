export interface HealthResponse {
  status: "ok";
  app: string;
  version: string;
  environment: string;
}

export interface ServiceStatus {
  name: string;
  healthy: boolean;
  detail: string | null;
}

export interface ReadyResponse {
  status: "ready" | "not_ready";
  checks: ServiceStatus[];
}

export type ConnectivityState = "unknown" | "ok" | "degraded" | "down";

export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    correlation_id?: string;
    details?: unknown;
  };
}
