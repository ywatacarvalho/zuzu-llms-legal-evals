import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LoginPage } from "@/pages/LoginPage";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

const mockLogin = vi.fn();
vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({ login: mockLogin }),
}));

vi.mock("@/services/api", () => ({
  apiClient: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

const { apiClient } = await import("@/services/api");

function renderPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the app name and form fields", () => {
    renderPage();
    expect(screen.getByText("LexEval")).toBeInTheDocument();
    expect(screen.getByLabelText("auth.email")).toBeInTheDocument();
    expect(screen.getByLabelText("auth.password")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "auth.login" })).toBeInTheDocument();
  });

  it("successful login calls login() and navigates to /", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { access_token: "tok-abc" } });
    vi.mocked(apiClient.get).mockResolvedValue({
      data: { id: "u1", email: "a@b.com", created_at: "", updated_at: "" },
    });

    const user = userEvent.setup({ delay: null });
    renderPage();

    await user.type(screen.getByLabelText("auth.email"), "a@b.com");
    await user.type(screen.getByLabelText("auth.password"), "secret");
    await user.click(screen.getByRole("button", { name: "auth.login" }));

    await waitFor(() => expect(mockLogin).toHaveBeenCalledWith("tok-abc", expect.any(Object)));
    expect(mockNavigate).toHaveBeenCalledWith("/");
  });

  it("shows invalidCredentials error on 401", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({ response: { status: 401 } });

    const user = userEvent.setup({ delay: null });
    renderPage();

    await user.type(screen.getByLabelText("auth.email"), "bad@example.com");
    await user.type(screen.getByLabelText("auth.password"), "wrong");
    await user.click(screen.getByRole("button", { name: "auth.login" }));

    await waitFor(() => {
      expect(screen.getByText("auth.invalidCredentials")).toBeInTheDocument();
    });
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("shows generic error on non-401 failure", async () => {
    vi.mocked(apiClient.post).mockRejectedValue({ response: { status: 500 } });

    const user = userEvent.setup({ delay: null });
    renderPage();

    await user.type(screen.getByLabelText("auth.email"), "a@b.com");
    await user.type(screen.getByLabelText("auth.password"), "pw");
    await user.click(screen.getByRole("button", { name: "auth.login" }));

    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });
});
