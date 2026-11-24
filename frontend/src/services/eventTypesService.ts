import { apiClient } from "@/services/apiClient";
import type { EventType, PageResponse } from "@/types/domain";

export async function listEventTypes(page = 1, pageSize = 100) {
  const { data } = await apiClient.get<PageResponse<EventType>>("/api/v1/event-types", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function getEventType(id: string) {
  const { data } = await apiClient.get<EventType>(`/api/v1/event-types/${id}`);
  return data;
}

export async function createEventType(body: { name: string; description?: string }) {
  const { data } = await apiClient.post<EventType>("/api/v1/event-types", body);
  return data;
}
