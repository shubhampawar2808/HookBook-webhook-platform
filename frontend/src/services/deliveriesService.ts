import { apiClient } from "@/services/apiClient";
import type {
  Delivery,
  DeliveryAttempt,
  DeliveryReplayResponse,
  DeliveryStatus,
  PageResponse,
} from "@/types/domain";

export type DeliveryListParams = {
  page?: number;
  page_size?: number;
  status?: DeliveryStatus;
  event_id?: string;
  endpoint_id?: string;
  created_from?: string;
  created_to?: string;
};

export async function listDeliveries(params: DeliveryListParams = {}) {
  const { data } = await apiClient.get<PageResponse<Delivery>>("/api/v1/deliveries", {
    params,
  });
  return data;
}

export async function listDeadLetter(page = 1, pageSize = 20) {
  const { data } = await apiClient.get<PageResponse<Delivery>>("/api/v1/deliveries/dead-letter", {
    params: { page, page_size: pageSize },
  });
  return data;
}

export async function getDelivery(id: string) {
  const { data } = await apiClient.get<Delivery>(`/api/v1/deliveries/${id}`);
  return data;
}

export async function listAttempts(deliveryId: string) {
  const { data } = await apiClient.get<DeliveryAttempt[]>(
    `/api/v1/deliveries/${deliveryId}/attempts`,
  );
  return data;
}

export async function replayDelivery(id: string) {
  const { data } = await apiClient.post<DeliveryReplayResponse>(
    `/api/v1/deliveries/${id}/replay`,
  );
  return data;
}
