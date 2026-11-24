import { apiClient } from "@/services/apiClient";
import type { HealthResponse, ReadyResponse } from "@/types/domain";

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await apiClient.get<HealthResponse>("/health");
  return data;
}

export async function fetchReady(): Promise<ReadyResponse> {
  const { data } = await apiClient.get<ReadyResponse>("/ready");
  return data;
}
