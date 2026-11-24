import { apiClient } from "@/services/apiClient";
import type {
  Endpoint,
  EndpointCreateResponse,
  MessageResponse,
  PageResponse,
  Subscription,
} from "@/types/domain";

export async function listEndpoints(page = 1, pageSize = 20) {
  const { data } = await apiClient.get<PageResponse<Endpoint>>("/api/v1/endpoints", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function getEndpoint(id: string) {
  const { data } = await apiClient.get<Endpoint>(`/api/v1/endpoints/${id}`);
  return data;
}

export async function createEndpoint(body: {
  name: string;
  url: string;
  description?: string;
}) {
  const { data } = await apiClient.post<EndpointCreateResponse>("/api/v1/endpoints", body);
  return data;
}

export async function updateEndpoint(
  id: string,
  body: Partial<{ name: string; url: string; description: string; status: "active" | "disabled" }>,
) {
  const { data } = await apiClient.patch<Endpoint>(`/api/v1/endpoints/${id}`, body);
  return data;
}

export async function deleteEndpoint(id: string) {
  const { data } = await apiClient.delete<MessageResponse>(`/api/v1/endpoints/${id}`);
  return data;
}

export async function listSubscriptions(endpointId: string, page = 1, pageSize = 50) {
  const { data } = await apiClient.get<PageResponse<Subscription>>(
    `/api/v1/endpoints/${endpointId}/subscriptions`,
    { params: { page, page_size: pageSize } },
  );
  return data;
}

export async function createSubscription(endpointId: string, eventTypeId: string) {
  const { data } = await apiClient.post<Subscription>(
    `/api/v1/endpoints/${endpointId}/subscriptions`,
    { event_type_id: eventTypeId },
  );
  return data;
}

export async function deleteSubscription(endpointId: string, subscriptionId: string) {
  const { data } = await apiClient.delete<MessageResponse>(
    `/api/v1/endpoints/${endpointId}/subscriptions/${subscriptionId}`,
  );
  return data;
}
