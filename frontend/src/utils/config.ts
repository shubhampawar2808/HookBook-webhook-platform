const rawBase = import.meta.env.VITE_API_BASE_URL as string | undefined;

export const API_BASE_URL = (rawBase || "http://localhost:8000").replace(/\/$/, "");
export const APP_ENV = (import.meta.env.VITE_APP_ENV as string) || "development";
export const AUTH_TOKEN_KEY = "hookforge_access_token";
export const SIDEBAR_COLLAPSED_KEY = "hookforge_sidebar_collapsed";
