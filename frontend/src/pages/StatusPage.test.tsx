import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { StatusPage } from "@/pages/StatusPage";
import { store } from "@/store";
import "@/styles/components.css";
import "@/styles/layout.css";

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

describe("StatusPage", () => {
  it("renders status content and connectivity panel", async () => {
    render(
      <Provider store={store}>
        <MemoryRouter>
          <StatusPage />
        </MemoryRouter>
      </Provider>,
    );

    expect(screen.getByRole("heading", { name: "HookForge" })).toBeInTheDocument();
    expect(await screen.findByText("Connected")).toBeInTheDocument();
    expect(screen.getByText(/Backend connectivity/i)).toBeInTheDocument();
  });
});
