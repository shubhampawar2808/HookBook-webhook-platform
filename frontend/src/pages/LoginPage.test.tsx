import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "@/pages/LoginPage";
import { store } from "@/store";
import { AUTH_TOKEN_KEY } from "@/utils/config";

vi.mock("@/services/authService", () => ({
  login: vi.fn(async () => ({
    access_token: "test-token",
    token_type: "bearer",
    expires_at: new Date(Date.now() + 3600_000).toISOString(),
  })),
  fetchMe: vi.fn(async () => ({
    id: "u1",
    email: "owner@example.com",
    full_name: "Owner",
    role: "owner",
    organization_id: "o1",
    organization_name: "Acme",
  })),
  register: vi.fn(),
}));

describe("LoginPage", () => {
  beforeEach(() => {
    localStorage.removeItem(AUTH_TOKEN_KEY);
  });

  it("validates required fields before submitting", async () => {
    const user = userEvent.setup();
    render(
      <Provider store={store}>
        <MemoryRouter>
          <LoginPage />
        </MemoryRouter>
      </Provider>,
    );

    await user.click(screen.getByRole("button", { name: /Sign in/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/required/i);
  });
});
