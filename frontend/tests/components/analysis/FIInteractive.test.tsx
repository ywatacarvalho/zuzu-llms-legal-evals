import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { FIReviewGate } from "@/components/rubrics/FIReviewGate";
import { ModeActionsPanel } from "@/components/rubrics/ModeActionsPanel";
import type { Rubric } from "@/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

vi.mock("@/services/rubricsApi", () => ({
  approveRubric: vi.fn(),
  extractOnly: vi.fn(),
}));

const { approveRubric, extractOnly } = await import("@/services/rubricsApi");

const BASE_RUBRIC: Rubric = {
  id: "rubric-1",
  evaluation_id: null,
  case_id: "case-1",
  question: "Is it enforceable?",
  status: "frozen",
  criteria: null,
  raw_response: null,
  is_frozen: true,
  conditioning_sample: null,
  decomposition_tree: null,
  refinement_passes: null,
  stopping_metadata: null,
  setup_responses: null,
  strong_reference_text: null,
  weak_reference_text: null,
  screening_result: null,
  source_extraction: null,
  gold_packet_mapping: null,
  doctrine_pack: null,
  routing_metadata: null,
  predicted_failure_modes: null,
  gold_answer: null,
  generated_question: null,
  self_audit_result: null,
  question_analysis: null,
  fi_status: null,
  fi_stream_id: null,
  review_notes: null,
  created_at: "2024-01-01T00:00:00Z",
  updated_at: "2024-01-01T00:00:00Z",
};

// ---------------------------------------------------------------------------
// FIReviewGate
// ---------------------------------------------------------------------------
describe("FIReviewGate", () => {
  it("renders null when fi_status is null", () => {
    const { container } = render(
      <FIReviewGate rubric={{ ...BASE_RUBRIC, fi_status: null }} onUpdate={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders null when fi_status is completed", () => {
    const { container } = render(
      <FIReviewGate rubric={{ ...BASE_RUBRIC, fi_status: "completed" }} onUpdate={vi.fn()} />
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders pipeline running message when extracting", () => {
    render(
      <FIReviewGate rubric={{ ...BASE_RUBRIC, fi_status: "extracting" }} onUpdate={vi.fn()} />
    );
    expect(screen.getByText("fi.reviewGate.pipelineRunning")).toBeInTheDocument();
  });

  it("renders rejected message when rejected", () => {
    render(<FIReviewGate rubric={{ ...BASE_RUBRIC, fi_status: "rejected" }} onUpdate={vi.fn()} />);
    expect(screen.getByText("fi.reviewGate.rejected")).toBeInTheDocument();
  });

  it("renders approve and reject buttons when awaiting_review", () => {
    render(
      <FIReviewGate rubric={{ ...BASE_RUBRIC, fi_status: "awaiting_review" }} onUpdate={vi.fn()} />
    );
    expect(screen.getByText("fi.reviewGate.approve")).toBeInTheDocument();
    expect(screen.getByText("fi.reviewGate.reject")).toBeInTheDocument();
  });

  it("calls approveRubric with approve action on button click", async () => {
    vi.mocked(approveRubric).mockResolvedValue({ status: "approved", rubric_id: "rubric-1" });
    const onUpdate = vi.fn();
    render(
      <FIReviewGate rubric={{ ...BASE_RUBRIC, fi_status: "awaiting_review" }} onUpdate={onUpdate} />
    );
    fireEvent.click(screen.getByText("fi.reviewGate.approve"));
    await waitFor(() =>
      expect(approveRubric).toHaveBeenCalledWith("rubric-1", { action: "approve" })
    );
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith({ fi_status: "approved" }));
  });
});

// ---------------------------------------------------------------------------
// ModeActionsPanel
// ---------------------------------------------------------------------------
describe("ModeActionsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows extract button when source_extraction is null", () => {
    render(
      <ModeActionsPanel rubric={{ ...BASE_RUBRIC, source_extraction: null }} onUpdate={vi.fn()} />
    );
    expect(screen.getByText("fi.modeActions.runExtract")).toBeInTheDocument();
  });

  it("does not show extract button when source_extraction exists", () => {
    render(
      <ModeActionsPanel
        rubric={{ ...BASE_RUBRIC, source_extraction: { clean_legal_issue: "SOF" } }}
        onUpdate={vi.fn()}
      />
    );
    expect(screen.queryByText("fi.modeActions.runExtract")).not.toBeInTheDocument();
  });

  it("calls extractOnly on button click and passes result to onUpdate", async () => {
    const result = {
      screening_result: { rating: "strong_lead" },
      source_extraction: { clean_legal_issue: "SOF" },
      routing_metadata: null,
      doctrine_pack: "pack_10",
    };
    vi.mocked(extractOnly).mockResolvedValue(result);
    const onUpdate = vi.fn();
    render(
      <ModeActionsPanel rubric={{ ...BASE_RUBRIC, source_extraction: null }} onUpdate={onUpdate} />
    );
    fireEvent.click(screen.getByText("fi.modeActions.runExtract"));
    await waitFor(() => expect(extractOnly).toHaveBeenCalledWith("rubric-1"));
    await waitFor(() => expect(onUpdate).toHaveBeenCalled());
  });
});
