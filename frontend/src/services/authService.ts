import { apiClient } from "@/services/apiClient";
import type { CurrentUser, TokenResponse } from "@/types/domain";

export async function login(body: {
  organization_slug: string;
  email: string;
  password: string;
}): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/api/v1/auth/login", body);
  return data;
}

export async function register(body: {
  organization_name: string;
  organization_slug: string;
  email: string;
  password: string;
  full_name: string;
}): Promise<TokenResponse> {
  const { data } = await apiClient.post<TokenResponse>("/api/v1/auth/register", body);
  return data;
}

export async function fetchMe(): Promise<CurrentUser> {
  const { data } = await apiClient.get<CurrentUser>("/api/v1/auth/me");
  return data;
}
