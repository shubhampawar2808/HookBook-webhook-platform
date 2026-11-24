import { apiClient } from "@/services/apiClient";
import type { Organization } from "@/types/domain";

export async function getOrganization(): Promise<Organization> {
  const { data } = await apiClient.get<Organization>("/api/v1/organizations/me");
  return data;
}

export async function updateOrganization(body: {
  name?: string;
  slug?: string;
}): Promise<Organization> {
  const { data } = await apiClient.patch<Organization>("/api/v1/organizations/me", body);
  return data;
}
