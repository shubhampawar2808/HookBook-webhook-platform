import { configureStore } from "@reduxjs/toolkit";

import authReducer from "@/features/auth/authSlice";
import { statusReducer } from "@/store/statusSlice";
import uiReducer from "@/store/uiSlice";

export const store = configureStore({
  reducer: {
    auth: authReducer,
    status: statusReducer,
    ui: uiReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
