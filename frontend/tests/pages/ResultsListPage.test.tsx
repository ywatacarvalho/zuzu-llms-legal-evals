import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResultsListPage } from "@/pages/results/ResultsListPage";
import { EvaluationStatus, type Evaluation } from "@/types";

const mockNavigate = vi.fn();

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("react-i18next", () => {
  const t = (key: string) => key;
  return {
    useTranslation: () => ({
      t,
      i18n: { changeLanguage: vi.fn() },
    }),
  };
});

vi.mock("@/services/evaluationsApi", () => ({
  listEvaluations: vi.fn(),
}));

const { listEvaluations } = await import("@/services/evaluationsApi");

const DONE_EVAL: Evaluation = {
  id: "eval-done",
  case_id: "case-1",
  question: "What is the standard of review?",
  model_names: ["openai/gpt-oss-20b"],
  status: EvaluationStatus.Done,
  response_count: 200,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const RUNNING_EVAL: Evaluation = {
  ...DONE_EVAL,
  id: "eval-running",
  status: EvaluationStatus.Running,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <Routes>
        <Route path="/" element={<ResultsListPage />} />
        <Route path="/results/:id" element={<div>Detail</div>} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ResultsListPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(listEvaluations).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("shows empty state when no done evaluations exist", async () => {
    vi.mocked(listEvaluations).mockResolvedValue([RUNNING_EVAL]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.list.empty")).toBeInTheDocument();
    });
  });

  it("filters out non-done evaluations", async () => {
    vi.mocked(listEvaluations).mockResolvedValue([DONE_EVAL, RUNNING_EVAL]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("What is the standard of review?")).toBeInTheDocument();
    });
    // Only one item (done), not the running one
    expect(screen.getAllByText("results.list.viewResults").length).toBe(1);
  });

  it("renders page header", async () => {
    vi.mocked(listEvaluations).mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.list.title")).toBeInTheDocument();
    });
  });

  it("shows error when fetch fails", async () => {
    vi.mocked(listEvaluations).mockRejectedValue(new Error("error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });

  it("navigates to results detail on button click", async () => {
    vi.mocked(listEvaluations).mockResolvedValue([DONE_EVAL]);
    const user = userEvent.setup();
    renderPage();

    const btn = await screen.findByText("results.list.viewResults");
    await user.click(btn);

    expect(mockNavigate).toHaveBeenCalledWith("/results/eval-done");
  });
});
