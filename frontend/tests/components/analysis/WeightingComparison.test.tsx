import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { WeightingComparison } from "@/components/analysis/WeightingComparison";
import type { WeightingModeResult } from "@/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

const MOCK_COMPARISON: Record<string, WeightingModeResult> = {
  uniform: {
    scores: { "0": 0.85, "1": 0.72 },
    winning_cluster: 0,
    model_shares: { "openai/gpt-oss-20b": 0.6, "google/gemma": 0.4 },
  },
  heuristic: {
    scores: { "0": 0.8, "1": 0.75 },
    winning_cluster: 0,
    model_shares: { "openai/gpt-oss-20b": 0.55, "google/gemma": 0.45 },
  },
  whitened_uniform: {
    scores: { "0": 0.5, "1": 0.3 },
    winning_cluster: 0,
    model_shares: { "openai/gpt-oss-20b": 0.7, "google/gemma": 0.3 },
  },
};

describe("WeightingComparison", () => {
  it("renders three columns for uniform, heuristic, whitened_uniform", () => {
    render(<WeightingComparison weighting_comparison={MOCK_COMPARISON} />);
    expect(screen.getByText("results.weighting.uniform")).toBeInTheDocument();
    expect(screen.getByText("results.weighting.heuristic")).toBeInTheDocument();
    expect(screen.getByText("results.weighting.whitened")).toBeInTheDocument();
  });

  it("shows winning cluster and top model per mode", () => {
    render(<WeightingComparison weighting_comparison={MOCK_COMPARISON} />);
    // All modes have winning_cluster 0
    const clusterLabels = screen.getAllByText(/results\.cluster\.label/);
    expect(clusterLabels.length).toBeGreaterThanOrEqual(3);
    // Top model is openai/gpt-oss-20b in all modes
    const topModels = screen.getAllByText("openai/gpt-oss-20b");
    expect(topModels.length).toBeGreaterThanOrEqual(3);
  });

  it("highlights disagreement when winning clusters differ across modes", () => {
    const disagreement: Record<string, WeightingModeResult> = {
      uniform: { scores: { "0": 0.8, "1": 0.9 }, winning_cluster: 1, model_shares: { m1: 1 } },
      heuristic: { scores: { "0": 0.9, "1": 0.8 }, winning_cluster: 0, model_shares: { m1: 1 } },
      whitened_uniform: {
        scores: { "0": 0.5, "1": 0.6 },
        winning_cluster: 1,
        model_shares: { m1: 1 },
      },
    };
    render(<WeightingComparison weighting_comparison={disagreement} />);
    expect(screen.getAllByText("results.weighting.disagreement").length).toBeGreaterThan(0);
  });

  it("renders nothing when weighting_comparison is null", () => {
    const { container } = render(<WeightingComparison weighting_comparison={null} />);
    expect(container.firstChild).toBeNull();
  });
});
