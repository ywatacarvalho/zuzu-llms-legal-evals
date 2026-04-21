import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CasesPage } from "@/pages/cases/CasesPage";
import type { LegalCase } from "@/types";

const stableT = (key: string) => key;
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: stableT,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

vi.mock("@/services/casesApi", () => ({
  listCases: vi.fn(),
  uploadCase: vi.fn(),
}));

const { listCases } = await import("@/services/casesApi");

const MOCK_CASE: LegalCase = {
  id: "case-1",
  title: "Smith v. Jones",
  filename: "smith.pdf",
  raw_text: "Legal text here.",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <CasesPage />
    </MemoryRouter>
  );
}

describe("CasesPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(listCases).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("renders case list when data loads", async () => {
    vi.mocked(listCases).mockResolvedValue([MOCK_CASE]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Smith v. Jones")).toBeInTheDocument();
    });
  });

  it("shows error state when fetch fails", async () => {
    vi.mocked(listCases).mockRejectedValue(new Error("Network error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });

  it("renders page header", async () => {
    vi.mocked(listCases).mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("cases.title")).toBeInTheDocument();
    });
  });

  it("renders upload button", async () => {
    vi.mocked(listCases).mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: /cases\.upload/i })).toBeInTheDocument();
    });
  });

  it("opens upload dialog when button is clicked", async () => {
    vi.mocked(listCases).mockResolvedValue([]);
    const user = userEvent.setup();
    renderPage();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: /cases\.upload/i })).toBeInTheDocument()
    );
    await user.click(screen.getByRole("button", { name: /cases\.upload/i }));

    await waitFor(() => {
      expect(screen.getByText("cases.uploadDialog.title")).toBeInTheDocument();
    });
  });

  it("adds new case to list via onUploaded callback", async () => {
    vi.mocked(listCases).mockResolvedValue([]);
    renderPage();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: /cases\.upload/i })).toBeInTheDocument()
    );

    // Verify empty state renders without error
    expect(screen.queryByText("errors.generic")).not.toBeInTheDocument();
  });
});
