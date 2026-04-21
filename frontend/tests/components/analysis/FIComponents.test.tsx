import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { DoctrinePackBadge } from "@/components/rubrics/DoctrinePackBadge";
import { DraftComparisonPanel } from "@/components/rubrics/DraftComparisonPanel";
import { FailureModesPanel } from "@/components/rubrics/FailureModesPanel";
import { GoldAnswerPanel } from "@/components/rubrics/GoldAnswerPanel";
import { GoldPacketMappingPanel } from "@/components/rubrics/GoldPacketMappingPanel";
import { QuestionAnalysisPanel } from "@/components/rubrics/QuestionAnalysisPanel";
import { SelfAuditPanel } from "@/components/rubrics/SelfAuditPanel";
import { SourceExtractionPanel } from "@/components/rubrics/SourceExtractionPanel";
import { SourceScreeningPanel } from "@/components/rubrics/SourceScreeningPanel";
import { FailureTagsTable } from "@/components/analysis/FailureTagsTable";
import { MetadataTagsPanel } from "@/components/analysis/MetadataTagsPanel";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

// ---------------------------------------------------------------------------
// SourceScreeningPanel
// ---------------------------------------------------------------------------
describe("SourceScreeningPanel", () => {
  it("renders null when screeningResult is null", () => {
    const { container } = render(<SourceScreeningPanel screeningResult={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders rating and reason", () => {
    render(
      <SourceScreeningPanel
        screeningResult={{ rating: "strong_lead", reason: "Clear SOF issue." }}
      />
    );
    expect(screen.getByText(/strong_lead/)).toBeInTheDocument();
    expect(screen.getByText(/Clear SOF issue./)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SourceExtractionPanel
// ---------------------------------------------------------------------------
describe("SourceExtractionPanel", () => {
  it("renders null when sourceExtraction is null", () => {
    const { container } = render(<SourceExtractionPanel sourceExtraction={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders key-value pairs from extraction dict", () => {
    render(
      <SourceExtractionPanel
        sourceExtraction={{ clean_legal_issue: "SOF writing", jurisdiction_forum: "CA" }}
      />
    );
    expect(screen.getByText("clean_legal_issue")).toBeInTheDocument();
    expect(screen.getByText("SOF writing")).toBeInTheDocument();
    expect(screen.getByText("CA")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// DoctrinePackBadge
// ---------------------------------------------------------------------------
describe("DoctrinePackBadge", () => {
  it("renders null when doctrinePack is null", () => {
    const { container } = render(<DoctrinePackBadge doctrinePack={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders pack name and confidence badge", () => {
    render(<DoctrinePackBadge doctrinePack="pack_10" routingMetadata={{ confidence: "high" }} />);
    expect(screen.getByText("pack_10")).toBeInTheDocument();
    expect(screen.getByText(/high/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// GoldPacketMappingPanel
// ---------------------------------------------------------------------------
describe("GoldPacketMappingPanel", () => {
  it("renders null when goldPacketMapping is null", () => {
    const { container } = render(<GoldPacketMappingPanel goldPacketMapping={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders key-value entries", () => {
    render(<GoldPacketMappingPanel goldPacketMapping={{ governing_rule: "SOF land" }} />);
    expect(screen.getByText("governing_rule")).toBeInTheDocument();
    expect(screen.getByText("SOF land")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// FailureModesPanel
// ---------------------------------------------------------------------------
describe("FailureModesPanel", () => {
  it("renders null when failureModes is null", () => {
    const { container } = render(<FailureModesPanel failureModes={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders failure mode items", () => {
    render(
      <FailureModesPanel
        failureModes={[
          { code: "SG", label: "Statute gap", description: "Missing statute", severity: "high" },
        ]}
      />
    );
    expect(screen.getByText("SG")).toBeInTheDocument();
    expect(screen.getByText("Statute gap")).toBeInTheDocument();
    expect(screen.getByText("Missing statute")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// GoldAnswerPanel
// ---------------------------------------------------------------------------
describe("GoldAnswerPanel", () => {
  it("renders null when goldAnswer is null", () => {
    const { container } = render(<GoldAnswerPanel goldAnswer={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders the gold answer text", () => {
    render(<GoldAnswerPanel goldAnswer="The contract is unenforceable under SOF." />);
    expect(screen.getByText(/unenforceable under SOF/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// SelfAuditPanel
// ---------------------------------------------------------------------------
describe("SelfAuditPanel", () => {
  it("renders null when selfAuditResult is null", () => {
    const { container } = render(<SelfAuditPanel selfAuditResult={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders classification badge and extra keys", () => {
    render(
      <SelfAuditPanel selfAuditResult={{ classification: "Ready", notes: "All checks pass." }} />
    );
    expect(screen.getByText("Ready")).toBeInTheDocument();
    expect(screen.getByText("notes")).toBeInTheDocument();
    expect(screen.getByText("All checks pass.")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// QuestionAnalysisPanel
// ---------------------------------------------------------------------------
describe("QuestionAnalysisPanel", () => {
  it("renders null when questionAnalysis is null", () => {
    const { container } = render(<QuestionAnalysisPanel questionAnalysis={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders analysis entries", () => {
    render(
      <QuestionAnalysisPanel
        questionAnalysis={{ target_doctrine: "SOF", distractors: ["consideration"] }}
      />
    );
    expect(screen.getByText("target_doctrine")).toBeInTheDocument();
    expect(screen.getByText("SOF")).toBeInTheDocument();
    expect(screen.getByText(/consideration/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// DraftComparisonPanel
// ---------------------------------------------------------------------------
describe("DraftComparisonPanel", () => {
  it("renders null when comparison is null", () => {
    const { container } = render(<DraftComparisonPanel comparison={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders 8 heading keys", () => {
    const comparison = {
      source_benchmark_alignment: "OK",
      controlling_doctrine_match: "Good",
      gate_order_correctness: "OK",
      trigger_test_accuracy: "Partial",
      exception_substitute_mapping: "OK",
      fallback_doctrine_treatment: "N/A",
      factual_fidelity: "OK",
      provenance_discipline: "Weak",
    };
    render(<DraftComparisonPanel comparison={comparison} />);
    expect(screen.getByText(/source benchmark alignment/)).toBeInTheDocument();
    expect(screen.getByText(/provenance discipline/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// FailureTagsTable
// ---------------------------------------------------------------------------
describe("FailureTagsTable", () => {
  it("renders null when failureTags is null", () => {
    const { container } = render(<FailureTagsTable failureTags={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders tags as badges", () => {
    render(<FailureTagsTable failureTags={{ statute_gap: true, writing_defect: "oral" }} />);
    expect(screen.getByText("statute_gap")).toBeInTheDocument();
    expect(screen.getByText(/writing_defect/)).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// MetadataTagsPanel
// ---------------------------------------------------------------------------
describe("MetadataTagsPanel", () => {
  it("renders null when tags is null", () => {
    const { container } = render(<MetadataTagsPanel tags={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders tag key-value pairs", () => {
    render(<MetadataTagsPanel tags={{ jurisdiction: "CA", doctrine: "SOF" }} />);
    expect(screen.getByText("jurisdiction")).toBeInTheDocument();
    expect(screen.getByText("CA")).toBeInTheDocument();
    expect(screen.getByText("doctrine")).toBeInTheDocument();
  });
});
