import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CriterionHeatmap } from "@/components/analysis/CriterionHeatmap";
import type { RubricCriterion } from "@/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

const CRITERIA: RubricCriterion[] = [
  { id: "accuracy", name: "Accuracy", description: "Factual correctness.", weight: 0.6 },
  { id: "reasoning", name: "Reasoning", description: "Legal reasoning.", weight: 0.4 },
];

const BASELINE: Record<string, Record<string, number>> = {
  "0": { accuracy: 0.9, reasoning: 0.8 },
  "1": { accuracy: 0.5, reasoning: 0.7 },
};

describe("CriterionHeatmap", () => {
  it("renders a grid with rows=clusters, columns=criteria", () => {
    render(<CriterionHeatmap baseline_scores={BASELINE} criteria={CRITERIA} winning_cluster={0} />);
    expect(screen.getByText("results.heatmap.title")).toBeInTheDocument();
    expect(screen.getByText("Accuracy")).toBeInTheDocument();
    expect(screen.getByText("Reasoning")).toBeInTheDocument();
  });

  it("shows score values in cells", () => {
    render(<CriterionHeatmap baseline_scores={BASELINE} criteria={CRITERIA} winning_cluster={0} />);
    expect(screen.getByTitle("Accuracy: 0.90")).toBeInTheDocument();
    expect(screen.getByTitle("Reasoning: 0.80")).toBeInTheDocument();
  });

  it("highlights the winning cluster row", () => {
    render(<CriterionHeatmap baseline_scores={BASELINE} criteria={CRITERIA} winning_cluster={0} />);
    // Winning cluster should have the star marker
    expect(screen.getByText("★")).toBeInTheDocument();
  });

  it("renders nothing when baseline_scores is null", () => {
    const { container } = render(
      <CriterionHeatmap baseline_scores={null} criteria={CRITERIA} winning_cluster={0} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when criteria is null", () => {
    const { container } = render(
      <CriterionHeatmap baseline_scores={BASELINE} criteria={null} winning_cluster={0} />
    );
    expect(container.firstChild).toBeNull();
  });
});
