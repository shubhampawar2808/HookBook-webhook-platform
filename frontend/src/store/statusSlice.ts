import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";

import { fetchHealth, fetchReady } from "@/services/healthService";
import { ApiClientError } from "@/services/apiClient";
import type {
  ConnectivityState,
  HealthResponse,
  ReadyResponse,
} from "@/types/api";

export interface StatusState {
  loading: boolean;
  health: HealthResponse | null;
  ready: ReadyResponse | null;
  connectivity: ConnectivityState;
  error: string | null;
  lastCheckedAt: string | null;
}

const initialState: StatusState = {
  loading: false,
  health: null,
  ready: null,
  connectivity: "unknown",
  error: null,
  lastCheckedAt: null,
};

export const checkBackendStatus = createAsyncThunk(
  "status/checkBackendStatus",
  async (_, { rejectWithValue }) => {
    try {
      const health = await fetchHealth();
      let ready: ReadyResponse | null = null;
      let connectivity: ConnectivityState = "ok";

      try {
        ready = await fetchReady();
        connectivity = ready.status === "ready" ? "ok" : "degraded";
      } catch {
        // Liveness succeeded but readiness failed — treat as degraded
        connectivity = "degraded";
      }

      return { health, ready, connectivity };
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : "Failed to reach HookForge backend";
      return rejectWithValue(message);
    }
  },
);

const statusSlice = createSlice({
  name: "status",
  initialState,
  reducers: {
    clearStatusError(state) {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(checkBackendStatus.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(checkBackendStatus.fulfilled, (state, action) => {
        state.loading = false;
        state.health = action.payload.health;
        state.ready = action.payload.ready;
        state.connectivity = action.payload.connectivity;
        state.lastCheckedAt = new Date().toISOString();
      })
      .addCase(checkBackendStatus.rejected, (state, action) => {
        state.loading = false;
        state.health = null;
        state.ready = null;
        state.connectivity = "down";
        state.error = (action.payload as string) || "Backend unreachable";
        state.lastCheckedAt = new Date().toISOString();
      });
  },
});

export const { clearStatusError } = statusSlice.actions;
export const statusReducer = statusSlice.reducer;
