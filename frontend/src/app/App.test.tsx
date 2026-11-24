import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { App } from "@/app/App";
import { store } from "@/store";
import { AUTH_TOKEN_KEY } from "@/utils/config";

vi.mock("@/services/healthService", () => ({
  fetchHealth: vi.fn(async () => ({
    status: "ok",
    app: "HookForge",
    version: "0.1.0",
    environment: "development",
  })),
  fetchReady: vi.fn(async () => ({
    status: "ready",
    checks: [
      { name: "database", healthy: true, detail: null },
      { name: "redis", healthy: true, detail: null },
    ],
  })),
}));

function renderApp(initialPath = "/login") {
  return render(
    <Provider store={store}>
      <MemoryRouter initialEntries={[initialPath]}>
        <App />
      </MemoryRouter>
    </Provider>,
  );
}

describe("App", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.removeItem(AUTH_TOKEN_KEY);
  });

  it("renders HookForge branding on the login shell", async () => {
    renderApp("/login");
    expect(screen.getAllByText("HookForge").length).toBeGreaterThan(0);
    expect(await screen.findByRole("heading", { name: /Sign in/i })).toBeInTheDocument();
  });

  it("redirects unauthenticated users from overview to login", async () => {
    renderApp("/");
    expect(await screen.findByRole("heading", { name: /Sign in/i })).toBeInTheDocument();
  });
});
