import { withApiKey } from "@/services/apiClient";
import type { EventResponse } from "@/types/domain";

export async function publishEvent(
  apiKey: string,
  body: { event_type: string; payload?: Record<string, unknown> },
): Promise<EventResponse> {
  const client = withApiKey(apiKey);
  const { data } = await client.post<EventResponse>("/api/v1/events", body);
  return data;
}
