import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RubricsPage } from "@/pages/rubrics/RubricsPage";
import type { Rubric } from "@/types";

const stableT = (key: string) => key;
vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: stableT,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

vi.mock("@/services/rubricsApi", () => ({
  listRubrics: vi.fn(),
  createRubric: vi.fn(),
}));

vi.mock("@/services/casesApi", () => ({
  listCases: vi.fn(),
}));

const { listRubrics } = await import("@/services/rubricsApi");

const MOCK_RUBRIC: Rubric = {
  id: "rubric-1",
  evaluation_id: null,
  case_id: "case-1",
  question: "What is the burden of proof in civil cases?",
  status: "frozen",
  criteria: [{ id: "c1", name: "Accuracy", weight: 1.0 }],
  raw_response: null,
  decomposition_tree: null,
  refinement_passes: null,
  stopping_metadata: null,
  conditioning_sample: null,
  is_frozen: true,
  setup_responses: null,
  strong_reference_text: null,
  weak_reference_text: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

function renderPage() {
  return render(
    <MemoryRouter>
      <RubricsPage />
    </MemoryRouter>
  );
}

describe("RubricsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(listRubrics).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("actions.loading")).toBeInTheDocument();
  });

  it("renders rubrics list after load", async () => {
    vi.mocked(listRubrics).mockResolvedValue([MOCK_RUBRIC]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("What is the burden of proof in civil cases?")).toBeInTheDocument();
    });
  });

  it("shows error state when fetch fails", async () => {
    vi.mocked(listRubrics).mockRejectedValue(new Error("error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("errors.generic")).toBeInTheDocument();
    });
  });

  it("renders page header and new rubric button", async () => {
    vi.mocked(listRubrics).mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("rubrics.title")).toBeInTheDocument();
    });
    expect(screen.getByRole("button", { name: /rubrics\.new/i })).toBeInTheDocument();
  });

  it("shows empty state when no rubrics exist", async () => {
    vi.mocked(listRubrics).mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("rubrics.table.empty")).toBeInTheDocument();
    });
  });
});
