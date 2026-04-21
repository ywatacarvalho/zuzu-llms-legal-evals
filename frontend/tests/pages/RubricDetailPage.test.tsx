import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { RubricDetailPage } from "@/pages/rubrics/RubricDetailPage";

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

vi.mock("@/services/rubricsApi", () => ({
  getRubric: vi.fn(),
  getRubricLogs: vi.fn().mockResolvedValue({ lines: [], total: 0 }),
  stopRubricBuild: vi.fn(),
}));

// jsdom does not implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

const { getRubric, stopRubricBuild } = await import("@/services/rubricsApi");

const MOCK_RUBRIC = {
  id: "rubric-1",
  evaluation_id: null,
  case_id: "case-1",
  question: "What is the standard of review for appellate courts?",
  status: "frozen" as const,
  criteria: [
    { id: "c1", name: "Accuracy", weight: 0.5 },
    { id: "c2", name: "Completeness", weight: 0.5 },
  ],
  raw_response: null,
  decomposition_tree: null,
  refinement_passes: null,
  stopping_metadata: null,
  conditioning_sample: null,
  is_frozen: true,
  setup_responses: null,
  strong_reference_text: null,
  weak_reference_text: null,
  created_at: "2026-01-15T10:00:00Z",
  updated_at: "2026-01-15T11:00:00Z",
};

function renderPage(rubricId = "rubric-1") {
  return render(
    <MemoryRouter initialEntries={[`/rubrics/${rubricId}`]}>
      <Routes>
        <Route path="/rubrics/:rubricId" element={<RubricDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("RubricDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(getRubric).mockResolvedValue(MOCK_RUBRIC);
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("renders rubric details after loading", async () => {
    vi.mocked(getRubric).mockResolvedValue(MOCK_RUBRIC);
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("What is the standard of review for appellate courts?")
      ).toBeInTheDocument();
    });
    expect(screen.getByText("2")).toBeInTheDocument(); // criteria count
  });

  it("shows error message on fetch failure", async () => {
    vi.mocked(getRubric).mockRejectedValue(new Error("network error"));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });

  it("shows stop button when status is building", async () => {
    vi.mocked(getRubric).mockResolvedValue({ ...MOCK_RUBRIC, status: "building" as const });
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /rubrics.detail.stop/i })).toBeInTheDocument();
    });
  });

  it("hides stop button when status is frozen", async () => {
    vi.mocked(getRubric).mockResolvedValue(MOCK_RUBRIC);
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("What is the standard of review for appellate courts?")
      ).toBeInTheDocument();
    });
    expect(screen.queryByRole("button", { name: /rubrics.detail.stop/i })).not.toBeInTheDocument();
  });

  it("starts polling when status is building", async () => {
    vi.mocked(getRubric).mockResolvedValue({ ...MOCK_RUBRIC, status: "building" as const });
    const intervalSpy = vi.spyOn(globalThis, "setInterval");
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("What is the standard of review for appellate courts?")
      ).toBeInTheDocument();
    });

    expect(intervalSpy).toHaveBeenCalled();
  });

  it("clears interval on unmount", async () => {
    vi.mocked(getRubric).mockResolvedValue({ ...MOCK_RUBRIC, status: "building" as const });
    const clearSpy = vi.spyOn(globalThis, "clearInterval");
    const { unmount } = renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("What is the standard of review for appellate courts?")
      ).toBeInTheDocument();
    });

    unmount();
    expect(clearSpy).toHaveBeenCalled();
  });

  it("back button navigates to /rubrics", async () => {
    vi.mocked(getRubric).mockResolvedValue(MOCK_RUBRIC);
    const user = userEvent.setup({ delay: null });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("rubrics.title")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /rubrics.title/i }));
    expect(mockNavigate).toHaveBeenCalledWith("/rubrics");
  });

  it("calls stopRubricBuild when stop button clicked", async () => {
    vi.mocked(getRubric).mockResolvedValue({ ...MOCK_RUBRIC, status: "building" as const });
    vi.mocked(stopRubricBuild).mockResolvedValue({ ...MOCK_RUBRIC, status: "failed" as const });
    const user = userEvent.setup({ delay: null });
    renderPage();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /rubrics.detail.stop/i })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /rubrics.detail.stop/i }));
    expect(stopRubricBuild).toHaveBeenCalledWith("rubric-1");
  });

  it("shows rubric results sections when rubric is frozen", async () => {
    vi.mocked(getRubric).mockResolvedValue({
      ...MOCK_RUBRIC,
      is_frozen: true,
      stopping_metadata: { reason: "convergence", total_rejected: 1, passes_completed: 1 },
      conditioning_sample: ["Centroid one"],
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("results.rubric.title")).toBeInTheDocument();
    });
    expect(screen.getByText("results.conditioning.title")).toBeInTheDocument();
  });

  it("does not show rubric results when rubric is not frozen", async () => {
    vi.mocked(getRubric).mockResolvedValue({
      ...MOCK_RUBRIC,
      status: "building" as const,
      is_frozen: false,
    });
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByText("What is the standard of review for appellate courts?")
      ).toBeInTheDocument();
    });
    expect(screen.queryByText("results.rubric.title")).not.toBeInTheDocument();
  });
});
