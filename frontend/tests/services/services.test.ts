import { beforeEach, describe, expect, it, vi } from "vitest";

// Mock apiClient before importing service modules
vi.mock("@/services/api", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

const { apiClient } = await import("@/services/api");
const { getDashboardStats } = await import("@/services/dashboardApi");
const { listCases, getCase, uploadCase } = await import("@/services/casesApi");
const { listEvaluations, getEvaluation, createEvaluation, listAvailableModels } =
  await import("@/services/evaluationsApi");
const { getAnalysis, runAnalysis } = await import("@/services/analysisApi");
const {
  createRubric,
  listRubrics,
  listFrozenRubrics,
  getRubric,
  getRubricLogs,
  stopRubricBuild,
  getRubricByEvaluation,
  approveRubric,
  validateQuestion,
  generateQuestion,
  extractOnly,
  compareDraft,
  draftFailureModes,
} = await import("@/services/rubricsApi");

beforeEach(() => {
  vi.clearAllMocks();
});

// ── Dashboard ────────────────────────────────────────────────────────────────

describe("getDashboardStats", () => {
  it("calls GET /dashboard/stats and returns data", async () => {
    const stats = { total_cases: 3, evaluations_run: 5, models_evaluated: 4, avg_clusters: 2.1 };
    vi.mocked(apiClient.get).mockResolvedValue({ data: stats });

    const result = await getDashboardStats();

    expect(apiClient.get).toHaveBeenCalledWith("/dashboard/stats");
    expect(result).toEqual(stats);
  });
});

// ── Cases ────────────────────────────────────────────────────────────────────

describe("listCases", () => {
  it("calls GET /cases and returns array", async () => {
    const cases = [{ id: "c1", title: "Case A" }];
    vi.mocked(apiClient.get).mockResolvedValue({ data: cases });

    const result = await listCases();

    expect(apiClient.get).toHaveBeenCalledWith("/cases");
    expect(result).toEqual(cases);
  });
});

describe("getCase", () => {
  it("calls GET /cases/:id", async () => {
    const c = { id: "c1", title: "Case A" };
    vi.mocked(apiClient.get).mockResolvedValue({ data: c });

    const result = await getCase("c1");

    expect(apiClient.get).toHaveBeenCalledWith("/cases/c1");
    expect(result).toEqual(c);
  });
});

describe("uploadCase", () => {
  it("posts FormData to /cases with title", async () => {
    const created = { id: "c2", title: "My Case" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: created });

    const file = new File(["pdf content"], "doc.pdf", { type: "application/pdf" });
    const result = await uploadCase(file, "My Case");

    expect(apiClient.post).toHaveBeenCalledWith(
      "/cases",
      expect.any(FormData),
      expect.objectContaining({ headers: { "Content-Type": "multipart/form-data" } })
    );
    expect(result).toEqual(created);
  });

  it("posts FormData to /cases without title", async () => {
    const created = { id: "c3", title: "doc.pdf" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: created });

    const file = new File(["pdf content"], "doc.pdf", { type: "application/pdf" });
    await uploadCase(file);

    expect(apiClient.post).toHaveBeenCalled();
  });
});

// ── Evaluations ──────────────────────────────────────────────────────────────

describe("listEvaluations", () => {
  it("calls GET /evaluations", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    const result = await listEvaluations();
    expect(apiClient.get).toHaveBeenCalledWith("/evaluations");
    expect(result).toEqual([]);
  });
});

describe("getEvaluation", () => {
  it("calls GET /evaluations/:id", async () => {
    const ev = { id: "e1", question: "Q?" };
    vi.mocked(apiClient.get).mockResolvedValue({ data: ev });
    const result = await getEvaluation("e1");
    expect(apiClient.get).toHaveBeenCalledWith("/evaluations/e1");
    expect(result).toEqual(ev);
  });
});

describe("createEvaluation", () => {
  it("posts to /evaluations with rubric_id and model_names", async () => {
    const ev = { id: "e2" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: ev });

    const result = await createEvaluation("rubric-1", ["openai/gpt-oss-20b"]);

    expect(apiClient.post).toHaveBeenCalledWith("/evaluations", {
      rubric_id: "rubric-1",
      model_names: ["openai/gpt-oss-20b"],
    });
    expect(result).toEqual(ev);
  });
});

describe("listAvailableModels", () => {
  it("calls GET /evaluations/models", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({
      data: [{ id: "openai/gpt-oss-20b", name: "GPT OSS 20B" }],
    });
    const result = await listAvailableModels();
    expect(apiClient.get).toHaveBeenCalledWith("/evaluations/models");
    expect(result).toHaveLength(1);
  });
});

// ── Analysis ─────────────────────────────────────────────────────────────────

describe("getAnalysis", () => {
  it("calls GET /analysis/:evalId", async () => {
    const an = { id: "an-1", k: 3 };
    vi.mocked(apiClient.get).mockResolvedValue({ data: an });
    const result = await getAnalysis("eval-1");
    expect(apiClient.get).toHaveBeenCalledWith("/analysis/eval-1");
    expect(result).toEqual(an);
  });
});

describe("runAnalysis", () => {
  it("calls POST /analysis/:evalId/run", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: {} });
    await runAnalysis("eval-1");
    expect(apiClient.post).toHaveBeenCalledWith("/analysis/eval-1/run");
  });
});

describe("getAnalysisStatus", () => {
  it("calls GET /analysis/:evalId/status and returns status", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: { status: "running" } });
    const { getAnalysisStatus } = await import("@/services/analysisApi");
    const result = await getAnalysisStatus("eval-1");
    expect(apiClient.get).toHaveBeenCalledWith("/analysis/eval-1/status");
    expect(result).toEqual({ status: "running" });
  });
});

describe("getAnalysisLogs", () => {
  it("calls GET /analysis/:evalId/logs with offset param", async () => {
    const logs = { lines: ["line1", "line2"], total: 2 };
    vi.mocked(apiClient.get).mockResolvedValue({ data: logs });
    const { getAnalysisLogs } = await import("@/services/analysisApi");
    const result = await getAnalysisLogs("eval-1", 0);
    expect(apiClient.get).toHaveBeenCalledWith("/analysis/eval-1/logs", { params: { offset: 0 } });
    expect(result).toEqual(logs);
  });
});

// ── Rubrics ──────────────────────────────────────────────────────────────────

describe("createRubric", () => {
  it("posts to /rubrics with case_id and question", async () => {
    const rubric = { id: "r1", status: "building" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: rubric });

    const result = await createRubric("case-1", "What is the burden of proof?");

    expect(apiClient.post).toHaveBeenCalledWith("/rubrics", {
      case_id: "case-1",
      question: "What is the burden of proof?",
    });
    expect(result).toEqual(rubric);
  });
});

describe("listRubrics", () => {
  it("calls GET /rubrics", async () => {
    vi.mocked(apiClient.get).mockResolvedValue({ data: [] });
    const result = await listRubrics();
    expect(apiClient.get).toHaveBeenCalledWith("/rubrics");
    expect(result).toEqual([]);
  });
});

describe("listFrozenRubrics", () => {
  it("calls GET /rubrics/frozen", async () => {
    const rubrics = [{ id: "r1", status: "frozen" }];
    vi.mocked(apiClient.get).mockResolvedValue({ data: rubrics });
    const result = await listFrozenRubrics();
    expect(apiClient.get).toHaveBeenCalledWith("/rubrics/frozen");
    expect(result).toEqual(rubrics);
  });
});

describe("getRubric", () => {
  it("calls GET /rubrics/:rubricId", async () => {
    const rubric = { id: "r1", status: "frozen" };
    vi.mocked(apiClient.get).mockResolvedValue({ data: rubric });
    const result = await getRubric("r1");
    expect(apiClient.get).toHaveBeenCalledWith("/rubrics/r1");
    expect(result).toEqual(rubric);
  });
});

describe("getRubricLogs", () => {
  it("calls GET /rubrics/:id/logs with offset", async () => {
    const logs = { lines: ["line1"], total: 1 };
    vi.mocked(apiClient.get).mockResolvedValue({ data: logs });
    const result = await getRubricLogs("r1", 5);
    expect(apiClient.get).toHaveBeenCalledWith("/rubrics/r1/logs", { params: { offset: 5 } });
    expect(result).toEqual(logs);
  });
});

describe("stopRubricBuild", () => {
  it("posts to /rubrics/:id/stop", async () => {
    const rubric = { id: "r1", status: "failed" };
    vi.mocked(apiClient.post).mockResolvedValue({ data: rubric });
    const result = await stopRubricBuild("r1");
    expect(apiClient.post).toHaveBeenCalledWith("/rubrics/r1/stop");
    expect(result).toEqual(rubric);
  });
});

describe("getRubricByEvaluation", () => {
  it("calls GET /rubrics/evaluation/:evalId and returns rubric", async () => {
    const rubric = { id: "r1", evaluation_id: "eval-1" };
    vi.mocked(apiClient.get).mockResolvedValue({ data: rubric });
    const result = await getRubricByEvaluation("eval-1");
    expect(apiClient.get).toHaveBeenCalledWith("/rubrics/evaluation/eval-1");
    expect(result).toEqual(rubric);
  });

  it("returns null on 404", async () => {
    vi.mocked(apiClient.get).mockRejectedValue({ response: { status: 404 } });
    const result = await getRubricByEvaluation("eval-missing");
    expect(result).toBeNull();
  });
});

// ── Phase 12 rubric operating modes ──────────────────────────────────────────

describe("approveRubric", () => {
  it("posts to /rubrics/:id/approve with body", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { status: "approved", rubric_id: "r1" } });
    const result = await approveRubric("r1", { action: "approve" });
    expect(apiClient.post).toHaveBeenCalledWith("/rubrics/r1/approve", { action: "approve" });
    expect(result.status).toBe("approved");
  });
});

describe("validateQuestion", () => {
  it("T10.16 -- posts to /rubrics/:id/validate-question", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { overall_pass: true, checks: [], red_flags: [], suggestions: [] },
    });
    const result = await validateQuestion("r1");
    expect(apiClient.post).toHaveBeenCalledWith("/rubrics/r1/validate-question");
    expect(result).toHaveProperty("overall_pass");
  });
});

describe("generateQuestion", () => {
  it("T10.17 -- posts to /rubrics/:id/generate-question", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { question: "Is the agreement enforceable?", internal_notes: {} },
    });
    const result = await generateQuestion("r1");
    expect(apiClient.post).toHaveBeenCalledWith("/rubrics/r1/generate-question");
    expect(result).toHaveProperty("question");
  });
});

describe("extractOnly", () => {
  it("T12.16 -- posts to /rubrics/:id/extract-only", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { source_extraction: {}, doctrine_pack: "pack_10" },
    });
    const result = await extractOnly("r1");
    expect(apiClient.post).toHaveBeenCalledWith("/rubrics/r1/extract-only");
    expect(result).toBeDefined();
  });
});

describe("compareDraft", () => {
  it("T12.17 -- posts to /rubrics/:id/compare-draft with draft_text body", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { source_benchmark_alignment: "OK" } });
    const result = await compareDraft("r1", "This agreement lacks writing.");
    expect(apiClient.post).toHaveBeenCalledWith("/rubrics/r1/compare-draft", {
      draft_text: "This agreement lacks writing.",
    });
    expect(result).toBeDefined();
  });
});

describe("draftFailureModes", () => {
  it("T12.18 -- posts to /rubrics/:id/draft-failure-modes", async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: [{ code: "SG", label: "Statute gap", description: "...", severity: "high" }],
    });
    const result = await draftFailureModes("r1");
    expect(apiClient.post).toHaveBeenCalledWith("/rubrics/r1/draft-failure-modes");
    expect(Array.isArray(result)).toBe(true);
  });
});
