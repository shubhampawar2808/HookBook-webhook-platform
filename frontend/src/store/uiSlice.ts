import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

import { SIDEBAR_COLLAPSED_KEY } from "@/utils/config";

type Toast = {
  id: string;
  tone: "info" | "success" | "warning" | "danger";
  title: string;
  message?: string;
};

type UiState = {
  sidebarCollapsed: boolean;
  mobileNavOpen: boolean;
  commandOpen: boolean;
  toasts: Toast[];
  globalError: string | null;
};

const initialState: UiState = {
  sidebarCollapsed: localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1",
  mobileNavOpen: false,
  commandOpen: false,
  toasts: [],
  globalError: null,
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    toggleSidebar(state) {
      state.sidebarCollapsed = !state.sidebarCollapsed;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, state.sidebarCollapsed ? "1" : "0");
    },
    setSidebarCollapsed(state, action: PayloadAction<boolean>) {
      state.sidebarCollapsed = action.payload;
      localStorage.setItem(SIDEBAR_COLLAPSED_KEY, action.payload ? "1" : "0");
    },
    setMobileNavOpen(state, action: PayloadAction<boolean>) {
      state.mobileNavOpen = action.payload;
    },
    setCommandOpen(state, action: PayloadAction<boolean>) {
      state.commandOpen = action.payload;
    },
    pushToast(state, action: PayloadAction<Omit<Toast, "id"> & { id?: string }>) {
      const id = action.payload.id || crypto.randomUUID();
      state.toasts.push({ ...action.payload, id });
    },
    dismissToast(state, action: PayloadAction<string>) {
      state.toasts = state.toasts.filter((t) => t.id !== action.payload);
    },
    setGlobalError(state, action: PayloadAction<string | null>) {
      state.globalError = action.payload;
    },
  },
});

export const {
  toggleSidebar,
  setSidebarCollapsed,
  setMobileNavOpen,
  setCommandOpen,
  pushToast,
  dismissToast,
  setGlobalError,
} = uiSlice.actions;
export default uiSlice.reducer;
