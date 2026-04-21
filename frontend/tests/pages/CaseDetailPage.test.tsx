import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CaseDetailPage } from "@/pages/cases/CaseDetailPage";
import type { LegalCase } from "@/types";

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

vi.mock("@/services/casesApi", () => ({
  getCase: vi.fn(),
}));

const { getCase } = await import("@/services/casesApi");

const MOCK_CASE: LegalCase = {
  id: "case-1",
  title: "Smith v. Jones",
  filename: "smith.pdf",
  raw_text: "The standard of review is de novo.",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

function renderPage(caseId = "case-1") {
  return render(
    <MemoryRouter initialEntries={[`/cases/${caseId}`]}>
      <Routes>
        <Route path="/cases/:caseId" element={<CaseDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("CaseDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(getCase).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("renders case title and filename after load", async () => {
    vi.mocked(getCase).mockResolvedValue(MOCK_CASE);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("Smith v. Jones")).toBeInTheDocument();
    });
    expect(screen.getByText("smith.pdf")).toBeInTheDocument();
  });

  it("shows extracted text", async () => {
    vi.mocked(getCase).mockResolvedValue(MOCK_CASE);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("The standard of review is de novo.")).toBeInTheDocument();
    });
  });

  it("shows error state when fetch fails", async () => {
    vi.mocked(getCase).mockRejectedValue(new Error("not found"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });

  it("shows no extracted text message when raw_text is empty", async () => {
    vi.mocked(getCase).mockResolvedValue({ ...MOCK_CASE, raw_text: "" });
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("cases.detail.noText")).toBeInTheDocument();
    });
  });
});
