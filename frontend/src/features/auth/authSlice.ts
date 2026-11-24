import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import * as authService from "@/services/authService";
import { ApiClientError } from "@/services/apiClient";
import type { CurrentUser } from "@/types/domain";
import { AUTH_TOKEN_KEY } from "@/utils/config";

type AuthState = {
  token: string | null;
  user: CurrentUser | null;
  status: "idle" | "loading" | "authenticated" | "anonymous" | "error";
  error: string | null;
  bootstrapped: boolean;
};

const initialState: AuthState = {
  token: localStorage.getItem(AUTH_TOKEN_KEY),
  user: null,
  status: "idle",
  error: null,
  bootstrapped: false,
};

export const bootstrapAuth = createAsyncThunk("auth/bootstrap", async () => {
  const token = localStorage.getItem(AUTH_TOKEN_KEY);
  if (!token) return null;
  return authService.fetchMe();
});

export const login = createAsyncThunk(
  "auth/login",
  async (
    body: { organization_slug: string; email: string; password: string },
    { rejectWithValue },
  ) => {
    try {
      const token = await authService.login(body);
      localStorage.setItem(AUTH_TOKEN_KEY, token.access_token);
      const user = await authService.fetchMe();
      return { token: token.access_token, user };
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : "Login failed";
      return rejectWithValue(message);
    }
  },
);

export const register = createAsyncThunk(
  "auth/register",
  async (
    body: {
      organization_name: string;
      organization_slug: string;
      email: string;
      password: string;
      full_name: string;
    },
    { rejectWithValue },
  ) => {
    try {
      const token = await authService.register(body);
      localStorage.setItem(AUTH_TOKEN_KEY, token.access_token);
      const user = await authService.fetchMe();
      return { token: token.access_token, user };
    } catch (err) {
      const message =
        err instanceof ApiClientError ? err.message : "Registration failed";
      return rejectWithValue(message);
    }
  },
);

const authSlice = createSlice({
  name: "auth",
  initialState,
  reducers: {
    logout(state) {
      localStorage.removeItem(AUTH_TOKEN_KEY);
      state.token = null;
      state.user = null;
      state.status = "anonymous";
      state.error = null;
    },
    clearAuthError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(bootstrapAuth.pending, (state) => {
        state.status = "loading";
      })
      .addCase(bootstrapAuth.fulfilled, (state, action) => {
        state.bootstrapped = true;
        if (!action.payload) {
          state.token = null;
          state.user = null;
          state.status = "anonymous";
          return;
        }
        state.user = action.payload;
        state.status = "authenticated";
      })
      .addCase(bootstrapAuth.rejected, (state) => {
        localStorage.removeItem(AUTH_TOKEN_KEY);
        state.token = null;
        state.user = null;
        state.bootstrapped = true;
        state.status = "anonymous";
      })
      .addCase(login.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(login.fulfilled, (state, action) => {
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.status = "authenticated";
        state.bootstrapped = true;
      })
      .addCase(login.rejected, (state, action) => {
        state.status = "error";
        state.error = (action.payload as string) || "Login failed";
      })
      .addCase(register.pending, (state) => {
        state.status = "loading";
        state.error = null;
      })
      .addCase(register.fulfilled, (state, action) => {
        state.token = action.payload.token;
        state.user = action.payload.user;
        state.status = "authenticated";
        state.bootstrapped = true;
      })
      .addCase(register.rejected, (state, action) => {
        state.status = "error";
        state.error = (action.payload as string) || "Registration failed";
      });
  },
});

export const { logout, clearAuthError } = authSlice.actions;
export default authSlice.reducer;
