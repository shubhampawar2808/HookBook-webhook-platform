import axios, { AxiosError, type AxiosInstance } from "axios";

import { API_BASE_URL, AUTH_TOKEN_KEY } from "@/utils/config";
import type { ApiErrorBody } from "@/types/api";

export class ApiClientError extends Error {
  status: number;
  code: string;
  correlationId?: string;

  constructor(message: string, status: number, code: string, correlationId?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.code = code;
    this.correlationId = correlationId;
  }
}

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: {
    Accept: "application/json",
    "Content-Type": "application/json",
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

type UnauthorizedHandler = () => void;
let onUnauthorized: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null) {
  onUnauthorized = handler;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorBody>) => {
    if (error.response?.status === 401) {
      onUnauthorized?.();
    }

    if (error.response?.data?.error) {
      const body = error.response.data.error;
      return Promise.reject(
        new ApiClientError(
          body.message || "Request failed",
          error.response.status,
          body.code || "http_error",
          body.correlation_id,
        ),
      );
    }

    if (error.code === "ECONNABORTED") {
      return Promise.reject(new ApiClientError("Request timed out", 408, "timeout"));
    }

    if (!error.response) {
      return Promise.reject(
        new ApiClientError("Unable to reach the HookForge API", 0, "network_error"),
      );
    }

    return Promise.reject(
      new ApiClientError(
        error.message || "Unexpected API error",
        error.response.status,
        "http_error",
      ),
    );
  },
);

/** Client that uses a provided API key instead of the JWT. */
export function withApiKey(apiKey: string): AxiosInstance {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: 15000,
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      Authorization: `Bearer ${apiKey}`,
    },
  });
  client.interceptors.response.use(
    (r) => r,
    (error: AxiosError<ApiErrorBody>) => {
      if (error.response?.data?.error) {
        const body = error.response.data.error;
        return Promise.reject(
          new ApiClientError(
            body.message || "Request failed",
            error.response.status,
            body.code || "http_error",
            body.correlation_id,
          ),
        );
      }
      return Promise.reject(
        new ApiClientError(
          error.message || "Unexpected API error",
          error.response?.status ?? 0,
          "http_error",
        ),
      );
    },
  );
  return client;
}
