import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationDetailPage } from "@/pages/evaluations/EvaluationDetailPage";
import { EvaluationStatus } from "@/types";

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

vi.mock("@/services/evaluationsApi", () => ({
  getEvaluation: vi.fn(),
  getEvaluationLogs: vi.fn().mockResolvedValue({ lines: [], total: 0 }),
  stopEvaluation: vi.fn(),
  rerunEvaluation: vi.fn(),
}));

// jsdom does not implement scrollIntoView
window.HTMLElement.prototype.scrollIntoView = vi.fn();

const { getEvaluation } = await import("@/services/evaluationsApi");

const MOCK_EVAL = {
  id: "eval-1",
  case_id: "case-1",
  question: "What is the standard of review?",
  model_names: ["meta-llama/Meta-Llama-3-8B-Instruct-Lite", "openai/gpt-oss-20b"],
  status: EvaluationStatus.Done,
  response_count: 200,
  created_at: "2026-01-15T10:00:00Z",
  updated_at: "2026-01-15T11:00:00Z",
};

function renderPage(evaluationId = "eval-1") {
  return render(
    <MemoryRouter initialEntries={[`/evaluations/${evaluationId}`]}>
      <Routes>
        <Route path="/evaluations/:evaluationId" element={<EvaluationDetailPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("EvaluationDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVAL);
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("renders evaluation details after loading", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVAL);
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("What is the standard of review?")).toBeInTheDocument();
    });
    expect(screen.getByText("meta-llama/Meta-Llama-3-8B-Instruct-Lite")).toBeInTheDocument();
    expect(screen.getByText("openai/gpt-oss-20b")).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
  });

  it("shows error message on fetch failure", async () => {
    vi.mocked(getEvaluation).mockRejectedValue(new Error("network error"));
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });

  it("shows View Results button when status is Done", async () => {
    vi.mocked(getEvaluation).mockResolvedValue({ ...MOCK_EVAL, status: EvaluationStatus.Done });
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /evaluations.detail.viewResults/i })
      ).toBeInTheDocument();
    });
  });

  it("hides View Results button when status is Running", async () => {
    vi.mocked(getEvaluation).mockResolvedValue({
      ...MOCK_EVAL,
      status: EvaluationStatus.Running,
      response_count: 50,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("What is the standard of review?")).toBeInTheDocument();
    });
    expect(
      screen.queryByRole("button", { name: /evaluations.detail.viewResults/i })
    ).not.toBeInTheDocument();
  });

  it("shows progress bar when status is Running", async () => {
    vi.mocked(getEvaluation).mockResolvedValue({
      ...MOCK_EVAL,
      status: EvaluationStatus.Running,
      response_count: 100,
    });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("What is the standard of review?")).toBeInTheDocument();
    });

    const progressBar = document.querySelector("[style*='width']");
    expect(progressBar).not.toBeNull();
  });

  it("starts setInterval when status is Running", async () => {
    vi.mocked(getEvaluation).mockResolvedValue({
      ...MOCK_EVAL,
      status: EvaluationStatus.Running,
      response_count: 50,
    });
    const intervalSpy = vi.spyOn(globalThis, "setInterval");
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("What is the standard of review?")).toBeInTheDocument();
    });

    expect(intervalSpy).toHaveBeenCalled();
  });

  it("clears interval on unmount", async () => {
    vi.mocked(getEvaluation).mockResolvedValue({
      ...MOCK_EVAL,
      status: EvaluationStatus.Running,
      response_count: 50,
    });
    const clearSpy = vi.spyOn(globalThis, "clearInterval");
    const { unmount } = renderPage();

    await waitFor(() => {
      expect(screen.getByText("What is the standard of review?")).toBeInTheDocument();
    });

    unmount();
    expect(clearSpy).toHaveBeenCalled();
  });

  it("back button navigates to /evaluations", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVAL);
    const user = userEvent.setup({ delay: null });
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("evaluations.title")).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /evaluations.title/i }));
    expect(mockNavigate).toHaveBeenCalledWith("/evaluations");
  });

  it("View Results button navigates to /results/:id", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVAL);
    const user = userEvent.setup({ delay: null });
    renderPage();

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /evaluations.detail.viewResults/i })
      ).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: /evaluations.detail.viewResults/i }));
    expect(mockNavigate).toHaveBeenCalledWith("/results/eval-1");
  });
});
