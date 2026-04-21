import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { EvaluationsPage } from "@/pages/evaluations/EvaluationsPage";
import { EvaluationStatus, type Evaluation } from "@/types";

const stableT = (key: string) => key;
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: stableT,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

vi.mock("@/services/evaluationsApi", () => ({
  listEvaluations: vi.fn(),
  listAvailableModels: vi.fn(),
  createEvaluation: vi.fn(),
}));

vi.mock("@/services/casesApi", () => ({
  listCases: vi.fn(),
}));

vi.mock("@/services/rubricsApi", () => ({
  listFrozenRubrics: vi.fn().mockResolvedValue([]),
}));

const { listEvaluations } = await import("@/services/evaluationsApi");

const MOCK_EVAL: Evaluation = {
  id: "eval-1",
  case_id: "case-1",
  question: "What is the burden of proof?",
  model_names: [
    "LiquidAI/LFM2-24B-A2B",
    "openai/gpt-oss-20b",
    "arize-ai/qwen-2-1.5b-instruct",
    "essentialai/rnj-1-instruct",
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
  ],
  status: EvaluationStatus.Done,
  response_count: 200,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <EvaluationsPage />
    </MemoryRouter>
  );
}

describe("EvaluationsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(listEvaluations).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("renders evaluations list after load", async () => {
    vi.mocked(listEvaluations).mockResolvedValue([MOCK_EVAL]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("What is the burden of proof?")).toBeInTheDocument();
    });
  });

  it("shows error state when fetch fails", async () => {
    vi.mocked(listEvaluations).mockRejectedValue(new Error("error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });

  it("renders page header and new evaluation button", async () => {
    vi.mocked(listEvaluations).mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("evaluations.title")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /evaluations\.new/i })).toBeInTheDocument();
  });
});
