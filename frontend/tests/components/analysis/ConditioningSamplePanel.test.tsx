import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ConditioningSamplePanel } from "@/components/analysis/ConditioningSamplePanel";
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
  criteria: null,
  raw_response: null,
  is_frozen: true,
  conditioning_sample: [
    "Centroid one text.",
    "Centroid two text.",
    "Centroid three text.",
    "Centroid four text.",
    "Centroid five text.",
    "Centroid six text.",
    "Centroid seven text.",
    "Centroid eight text.",
  ],
  decomposition_tree: null,
  refinement_passes: null,
  stopping_metadata: null,
  setup_responses: [
    { model: "setup-model-a", text: "Response A" },
    { model: "setup-model-a", text: "Response B" },
    { model: "setup-model-b", text: "Response C" },
  ],
  strong_reference_text: "This is the strong answer.",
  weak_reference_text: "This is the weak answer.",
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

async function openPanel() {
  const toggle = screen.getByText("results.conditioning.title");
  await userEvent.click(toggle);
}

describe("ConditioningSamplePanel", () => {
  it("renders 8 numbered centroid cards from conditioning_sample after expand", async () => {
    render(<ConditioningSamplePanel rubric={MOCK_RUBRIC} />);
    await openPanel();
    // There should be 8 centroid labels
    const labels = screen.getAllByText(/results\.conditioning\.centroid/);
    expect(labels).toHaveLength(8);
  });

  it("shows strong and weak reference texts side by side", async () => {
    render(<ConditioningSamplePanel rubric={MOCK_RUBRIC} />);
    await openPanel();
    expect(screen.getByText("results.conditioning.strong")).toBeInTheDocument();
    expect(screen.getByText("results.conditioning.weak")).toBeInTheDocument();
    expect(screen.getByText("This is the strong answer.")).toBeInTheDocument();
    expect(screen.getByText("This is the weak answer.")).toBeInTheDocument();
  });

  it("shows setup response count per model", async () => {
    render(<ConditioningSamplePanel rubric={MOCK_RUBRIC} />);
    await openPanel();
    const setupToggle = screen.getByText(/results\.conditioning\.setupResponses/);
    await userEvent.click(setupToggle);
    expect(screen.getByText("setup-model-a")).toBeInTheDocument();
    expect(screen.getByText("setup-model-b")).toBeInTheDocument();
  });

  it("renders nothing when no relevant data is present", () => {
    const emptyRubric: Rubric = {
      ...MOCK_RUBRIC,
      conditioning_sample: null,
      strong_reference_text: null,
      weak_reference_text: null,
      setup_responses: null,
    };
    const { container } = render(<ConditioningSamplePanel rubric={emptyRubric} />);
    expect(container.firstChild).toBeNull();
  });
});
