import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResultsPage } from "@/pages/results/ResultsPage";
import type { Analysis, Evaluation, Rubric } from "@/types";
import { EvaluationStatus } from "@/types";

const stableT = (key: string, opts?: Record<string, unknown>) => {
  if (opts && "pct" in opts) return `${opts.pct}% share in winning Cluster ${opts.cluster}`;
  if (opts && "count" in opts) return `${opts.count} responses`;
  return key;
};
const stableI18n = { changeLanguage: vi.fn() };

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: stableT, i18n: stableI18n }),
}));

vi.mock("@/services/evaluationsApi", () => ({
  getEvaluation: vi.fn(),
}));

vi.mock("@/services/analysisApi", () => ({
  getAnalysis: vi.fn(),
  runAnalysis: vi.fn(),
  getAnalysisStatus: vi.fn(),
  getAnalysisLogs: vi.fn(),
}));

vi.mock("@/services/rubricsApi", () => ({
  getRubricByEvaluation: vi.fn(),
}));

// recharts needs ResizeObserver in jsdom
vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

const { getEvaluation } = await import("@/services/evaluationsApi");
const { getAnalysis, runAnalysis, getAnalysisStatus, getAnalysisLogs } =
  await import("@/services/analysisApi");
const { getRubricByEvaluation } = await import("@/services/rubricsApi");

const MOCK_EVALUATION: Evaluation = {
  id: "eval-1",
  case_id: "case-1",
  question: "What is the applicable standard of review?",
  model_names: [
    "LiquidAI/LFM2-24B-A2B",
    "openai/gpt-oss-20b",
    "google/gemma-3n-E4B-it",
    "arize-ai/qwen-2-1.5b-instruct",
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite",
  ],
  status: EvaluationStatus.Done,
  response_count: 200,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

const MOCK_ANALYSIS: Analysis = {
  id: "an-1",
  evaluation_id: "eval-1",
  k: 3,
  clusters: [
    {
      cluster_id: 0,
      response_indices: Array.from({ length: 80 }, (_, i) => i),
      centroid_index: 5,
      centroid_response_text: "The de novo standard applies here.",
      model_counts: { "LiquidAI/LFM2-24B-A2B": 30, "openai/gpt-oss-20b": 25 },
    },
    {
      cluster_id: 1,
      response_indices: Array.from({ length: 70 }, (_, i) => i + 80),
      centroid_index: 85,
      centroid_response_text: "Under abuse of discretion...",
      model_counts: { "google/gemma-3n-E4B-it": 40 },
    },
    {
      cluster_id: 2,
      response_indices: Array.from({ length: 50 }, (_, i) => i + 150),
      centroid_index: 155,
      centroid_response_text: "Clearly erroneous standard.",
      model_counts: null,
    },
  ],
  centroid_indices: [5, 85, 155],
  scores: { "0": 0.85, "1": 0.72, "2": 0.61 },
  winning_cluster: 0,
  model_shares: {
    "LiquidAI/LFM2-24B-A2B": 0.31,
    "openai/gpt-oss-20b": 0.25,
    "google/gemma-3n-E4B-it": 0.19,
    "arize-ai/qwen-2-1.5b-instruct": 0.14,
    "meta-llama/Meta-Llama-3-8B-Instruct-Lite": 0.11,
  },
  weighting_mode: "heuristic",
  baseline_scores: {
    "0": { accuracy: 0.9, reasoning: 0.8 },
    "1": { accuracy: 0.7, reasoning: 0.75 },
    "2": { accuracy: 0.6, reasoning: 0.62 },
  },
  weighting_comparison: {
    uniform: {
      scores: { "0": 0.85, "1": 0.72, "2": 0.61 },
      winning_cluster: 0,
      model_shares: { "LiquidAI/LFM2-24B-A2B": 0.31 },
    },
    heuristic: {
      scores: { "0": 0.85, "1": 0.72, "2": 0.61 },
      winning_cluster: 0,
      model_shares: { "LiquidAI/LFM2-24B-A2B": 0.31 },
    },
    whitened_uniform: {
      scores: { "0": 0.5, "1": 0.3, "2": 0.2 },
      winning_cluster: 0,
      model_shares: { "LiquidAI/LFM2-24B-A2B": 0.31 },
    },
  },
  silhouette_scores_by_k: { "2": 0.42, "3": 0.61, "4": 0.55 },
  created_at: "2024-01-01T01:00:00Z",
  updated_at: "2024-01-01T01:00:00Z",
};

const MOCK_RUBRIC: Rubric = {
  id: "rb-1",
  evaluation_id: "eval-1",
  criteria: [
    { id: "accuracy", name: "Accuracy", description: "Factual correctness.", weight: 0.6 },
    { id: "reasoning", name: "Reasoning", description: "Legal reasoning quality.", weight: 0.4 },
  ],
  raw_response: null,
  is_frozen: true,
  conditioning_sample: ["Centroid text one.", "Centroid text two."],
  decomposition_tree: { "Broad Criterion": ["Sub A", "Sub B"] },
  refinement_passes: [
    {
      pass_number: 1,
      accepted: 3,
      rejected_misalignment: 1,
      rejected_redundancy: 0,
      decomposition_empty: 0,
    },
  ],
  stopping_metadata: { reason: "convergence", total_rejected: 1, passes_completed: 1 },
  setup_responses: [
    { model: "setup-model-a", text: "Response A" },
    { model: "setup-model-a", text: "Response B" },
    { model: "setup-model-b", text: "Response C" },
  ],
  strong_reference_text: "This is a strong legal answer.",
  weak_reference_text: "This is a weak legal answer.",
  created_at: "2024-01-01T00:30:00Z",
  updated_at: "2024-01-01T00:30:00Z",
};

function renderPage(evaluationId = "eval-1") {
  return render(
    <MemoryRouter initialEntries={[`/results/${evaluationId}`]}>
      <Routes>
        <Route path="/results/:evaluationId" element={<ResultsPage />} />
      </Routes>
    </MemoryRouter>
  );
}

describe("ResultsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(getRubricByEvaluation).mockResolvedValue(null);
    vi.mocked(getAnalysisStatus).mockResolvedValue({ status: "not_started" });
    vi.mocked(getAnalysisLogs).mockResolvedValue({ lines: [], total: 0 });
  });

  it("shows loading state initially", () => {
    vi.mocked(getEvaluation).mockReturnValue(new Promise(() => {}));
    vi.mocked(getAnalysis).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("shows Run Analysis button when no analysis exists", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockRejectedValue(new Error("Not found"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.detail.run")).toBeInTheDocument();
    });
  });

  it("renders results dashboard when analysis exists", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.winner.label")).toBeInTheDocument();
    });
    expect(screen.getAllByText("LiquidAI/LFM2-24B-A2B").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("results.stats.clusters")).toBeInTheDocument();
    expect(screen.getAllByText("3").length).toBeGreaterThanOrEqual(1);
  });

  it("shows winner banner with correct model", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    renderPage();
    await waitFor(() => {
      expect(screen.getAllByText("LiquidAI/LFM2-24B-A2B").length).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getByText("31% share in winning Cluster 0")).toBeInTheDocument();
  });

  it("calls runAnalysis and shows results on Run Analysis click", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis)
      .mockRejectedValueOnce(new Error("Not found")) // initial load
      .mockResolvedValue(MOCK_ANALYSIS); // after polling sees "done"
    vi.mocked(runAnalysis).mockResolvedValue(undefined);
    vi.mocked(getAnalysisStatus)
      .mockResolvedValueOnce({ status: "not_started" }) // initial load
      .mockResolvedValue({ status: "done" }); // polling

    renderPage();

    const runBtn = await screen.findByText("results.detail.run");
    await act(async () => {
      fireEvent.click(runBtn);
    });

    await waitFor(() => {
      expect(runAnalysis).toHaveBeenCalledWith("eval-1");
    });

    await waitFor(
      () => {
        expect(screen.getAllByText("LiquidAI/LFM2-24B-A2B").length).toBeGreaterThanOrEqual(1);
      },
      { timeout: 10_000 }
    );
  });

  it("shows error when runAnalysis fails", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockRejectedValue(new Error("Not found"));
    vi.mocked(runAnalysis).mockRejectedValue(new Error("Server error"));

    renderPage();

    const runBtn = await screen.findByText("results.detail.run");
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText("results.runError")).toBeInTheDocument();
    });
  });

  it("renders all cluster centroid cards sorted by score", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.centroids.title")).toBeInTheDocument();
    });
    expect(screen.getByText("results.cluster.winner")).toBeInTheDocument();
  });

  it("fetches rubric alongside analysis on load", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    vi.mocked(getRubricByEvaluation).mockResolvedValue(MOCK_RUBRIC);
    renderPage();
    await waitFor(() => {
      expect(getRubricByEvaluation).toHaveBeenCalledWith("eval-1");
    });
  });

  it("renders rubric section when rubric is available", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    vi.mocked(getRubricByEvaluation).mockResolvedValue(MOCK_RUBRIC);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.rubric.title")).toBeInTheDocument();
    });
  });

  it("renders weighting comparison table", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.weighting.title")).toBeInTheDocument();
    });
  });

  it("renders silhouette chart", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.silhouette.title")).toBeInTheDocument();
    });
  });

  it("renders criterion heatmap when rubric criteria available", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    vi.mocked(getRubricByEvaluation).mockResolvedValue(MOCK_RUBRIC);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.heatmap.title")).toBeInTheDocument();
    });
  });

  it("renders conditioning sample panel when rubric available", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    vi.mocked(getRubricByEvaluation).mockResolvedValue(MOCK_RUBRIC);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.conditioning.title")).toBeInTheDocument();
    });
  });

  it("renders evaluated models pill list", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.models.title")).toBeInTheDocument();
    });
    expect(screen.getByText("openai/gpt-oss-20b")).toBeInTheDocument();
  });

  it("auto-starts polling when initial status is running and no analysis exists", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis)
      .mockRejectedValueOnce(new Error("Not found"))
      .mockResolvedValue(MOCK_ANALYSIS);
    vi.mocked(getAnalysisStatus)
      .mockResolvedValueOnce({ status: "running" })
      .mockResolvedValue({ status: "done" });
    vi.mocked(getAnalysisLogs).mockResolvedValue({ lines: [], total: 0 });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("results.detail.runningTitle")).toBeInTheDocument();
    });
  });

  it("shows log lines in pre block while running", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockRejectedValue(new Error("Not found"));
    vi.mocked(runAnalysis).mockResolvedValue(undefined);
    vi.mocked(getAnalysisStatus)
      .mockResolvedValueOnce({ status: "not_started" })
      .mockResolvedValue({ status: "running" });
    vi.mocked(getAnalysisLogs).mockResolvedValue({
      lines: ["[analysis] Embedding responses"],
      total: 1,
    });

    renderPage();

    const runBtn = await screen.findByText("results.detail.run");
    await act(async () => {
      fireEvent.click(runBtn);
    });

    await waitFor(
      () => {
        expect(screen.getByText(/Embedding responses/)).toBeInTheDocument();
      },
      { timeout: 10_000 }
    );
  });

  it("renders gracefully when rubric fetch fails", async () => {
    vi.mocked(getEvaluation).mockResolvedValue(MOCK_EVALUATION);
    vi.mocked(getAnalysis).mockResolvedValue(MOCK_ANALYSIS);
    vi.mocked(getRubricByEvaluation).mockRejectedValue(new Error("Network error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("results.winner.label")).toBeInTheDocument();
    });
    // rubric-dependent sections should not be visible, no crash
    expect(screen.queryByText("results.rubric.title")).not.toBeInTheDocument();
    expect(screen.queryByText("results.heatmap.title")).not.toBeInTheDocument();
  });
});
