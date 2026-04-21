import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { RubricSection } from "@/components/analysis/RubricSection";
import type { Rubric } from "@/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

const MOCK_RUBRIC: Rubric = {
  id: "rb-1",
  evaluation_id: "eval-1",
  criteria: [
    { id: "accuracy", name: "Accuracy", description: "Factual correctness.", weight: 0.6 },
    { id: "reasoning", name: "Reasoning", description: "Legal reasoning.", weight: 0.4 },
  ],
  raw_response: null,
  is_frozen: true,
  conditioning_sample: ["Centroid one", "Centroid two"],
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
  setup_responses: [{ model: "m1", text: "response" }],
  strong_reference_text: "Strong",
  weak_reference_text: "Weak",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

async function openSection() {
  const toggle = screen.getByText("results.rubric.title");
  await userEvent.click(toggle);
}

describe("RubricSection", () => {
  it("renders criteria list with names, descriptions, weights after expand", async () => {
    render(<RubricSection rubric={MOCK_RUBRIC} />);
    await openSection();
    expect(screen.getByText("Accuracy")).toBeInTheDocument();
    expect(screen.getByText("Reasoning")).toBeInTheDocument();
    expect(screen.getByText("Factual correctness.")).toBeInTheDocument();
  });

  it("shows refinement summary: passes, stopping reason, rejected count", async () => {
    render(<RubricSection rubric={MOCK_RUBRIC} />);
    await openSection();
    expect(screen.getByText("results.rubric.passes")).toBeInTheDocument();
    expect(screen.getByText("convergence")).toBeInTheDocument();
    // passes_completed = 1, total_rejected = 1 — use getAllByText
    expect(screen.getAllByText("1").length).toBeGreaterThanOrEqual(1);
  });

  it("renders decomposition tree when decomposition_tree is non-empty", async () => {
    render(<RubricSection rubric={MOCK_RUBRIC} />);
    await openSection();
    // Decomposition tree toggle is present
    expect(screen.getByText("results.rubric.decomposition")).toBeInTheDocument();
  });

  it("collapses decomposition tree contents by default", async () => {
    render(<RubricSection rubric={MOCK_RUBRIC} />);
    await openSection();
    // Tree contents not visible until clicked
    expect(screen.queryByText("Sub A")).not.toBeInTheDocument();
  });

  it("renders decomposition tree contents after expanding", async () => {
    render(<RubricSection rubric={MOCK_RUBRIC} />);
    await openSection();
    const treeToggle = screen.getByText("results.rubric.decomposition");
    await userEvent.click(treeToggle);
    expect(screen.getByText("Broad Criterion")).toBeInTheDocument();
    expect(screen.getByText("Sub A")).toBeInTheDocument();
  });

  it("renders refinement pass log entries after expanding", async () => {
    render(<RubricSection rubric={MOCK_RUBRIC} />);
    await openSection();
    const logToggle = screen.getByText("results.rubric.passLog");
    await userEvent.click(logToggle);
    expect(screen.getByText(/Pass 1/)).toBeInTheDocument();
    expect(screen.getByText(/\+3 accepted/)).toBeInTheDocument();
  });

  it("renders nothing when rubric is null", () => {
    const { container } = render(<RubricSection rubric={null as unknown as Rubric} />);
    expect(container.firstChild).toBeNull();
  });

  it("starts expanded when initialOpen is true", () => {
    render(<RubricSection rubric={MOCK_RUBRIC} initialOpen />);
    expect(screen.getByText("Accuracy")).toBeInTheDocument();
  });
});
