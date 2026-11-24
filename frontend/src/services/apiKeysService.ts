import { apiClient } from "@/services/apiClient";
import type { APIKey, APIKeyCreateResponse, PageResponse } from "@/types/domain";

export async function listApiKeys(page = 1, pageSize = 20) {
  const { data } = await apiClient.get<PageResponse<APIKey>>("/api/v1/api-keys", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function createApiKey(body: { name: string; expires_at?: string | null }) {
  const { data } = await apiClient.post<APIKeyCreateResponse>("/api/v1/api-keys", body);
  return data;
}

export async function revokeApiKey(id: string) {
  const { data } = await apiClient.delete<APIKey>(`/api/v1/api-keys/${id}`);
  return data;
}

export async function rotateApiKey(id: string) {
  const { data } = await apiClient.post<APIKeyCreateResponse>(`/api/v1/api-keys/${id}/rotate`);
  return data;
}
