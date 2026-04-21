import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CentroidCard } from "@/components/analysis/CentroidCard";
import type { ClusterResult } from "@/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, opts?: Record<string, unknown>) => {
      if (opts && "count" in opts) return `${opts.count} responses`;
      return key;
    },
    i18n: { changeLanguage: vi.fn() },
  }),
}));

const LONG_TEXT = "A ".repeat(300);

const CLUSTER: ClusterResult = {
  cluster_id: 1,
  response_indices: Array.from({ length: 40 }, (_, i) => i),
  centroid_index: 5,
  centroid_response_text: "The de novo standard applies here.",
  model_counts: { "openai/gpt-oss-20b": 20, "essentialai/rnj-1-instruct": 10, "LiquidAI/LFM2": 10 },
};

describe("CentroidCard", () => {
  it("renders cluster id, score, and response count", () => {
    render(<CentroidCard cluster={CLUSTER} score={0.85} isWinner={false} />);
    expect(screen.getByText(/results\.cluster\.label/)).toBeInTheDocument();
    // Score rendered as "85%"
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("40 responses")).toBeInTheDocument();
  });

  it("shows winner badge for winning cluster", () => {
    render(<CentroidCard cluster={CLUSTER} score={0.85} isWinner={true} />);
    expect(screen.getByText("results.cluster.winner")).toBeInTheDocument();
  });

  it("does not show winner badge for non-winner", () => {
    render(<CentroidCard cluster={CLUSTER} score={0.72} isWinner={false} />);
    expect(screen.queryByText("results.cluster.winner")).not.toBeInTheDocument();
  });

  it("truncates long centroid text with show more button", () => {
    const longCluster = { ...CLUSTER, centroid_response_text: LONG_TEXT };
    render(<CentroidCard cluster={longCluster} score={0.7} isWinner={false} />);
    expect(screen.getByText("results.cluster.showMore")).toBeInTheDocument();
  });

  it("expands text on show more click", async () => {
    const longCluster = { ...CLUSTER, centroid_response_text: LONG_TEXT };
    render(<CentroidCard cluster={longCluster} score={0.7} isWinner={false} />);
    await userEvent.click(screen.getByText("results.cluster.showMore"));
    expect(screen.getByText("results.cluster.showLess")).toBeInTheDocument();
  });

  it("shows model breakdown when model_counts is present", () => {
    render(<CentroidCard cluster={CLUSTER} score={0.85} isWinner={false} />);
    expect(screen.getByText(/gpt-oss-20b: 20/)).toBeInTheDocument();
  });

  it("adds full endpoint titles to model chips", () => {
    render(<CentroidCard cluster={CLUSTER} score={0.85} isWinner={false} />);
    expect(screen.getByTitle("openai/gpt-oss-20b")).toHaveTextContent("gpt-oss-20b: 20");
  });

  it("hides model breakdown when model_counts is absent", () => {
    const noCountsCluster = { ...CLUSTER, model_counts: null };
    render(<CentroidCard cluster={noCountsCluster} score={0.85} isWinner={false} />);
    expect(screen.queryByText("results.cluster.modelBreakdown")).not.toBeInTheDocument();
  });

  it("renders markdown bold without raw markers", () => {
    const markdownCluster = {
      ...CLUSTER,
      centroid_response_text: "**Issue** The oral agreement exceeds one year.",
    };
    render(<CentroidCard cluster={markdownCluster} score={0.85} isWinner={false} />);

    const issue = screen.getByText("Issue");
    expect(issue.tagName.toLowerCase()).toBe("strong");
    expect(screen.queryByText(/\*\*Issue\*\*/)).not.toBeInTheDocument();
  });

  it("renders markdown headings without heading markers", () => {
    const headingCluster = {
      ...CLUSTER,
      centroid_response_text: "### Part 1: Statute of Frauds",
    };
    render(<CentroidCard cluster={headingCluster} score={0.85} isWinner={false} />);

    expect(screen.getByRole("heading", { name: "Part 1: Statute of Frauds" })).toBeInTheDocument();
    expect(screen.queryByText(/###/)).not.toBeInTheDocument();
  });

  it("infers headings from plain legal section labels", () => {
    const sectionCluster = {
      ...CLUSTER,
      centroid_response_text:
        "Part 1: The Statute of Frauds and the Oral Agreement\n\nApplication to Agreement:\nThe agreement lasted five years.",
    };
    render(<CentroidCard cluster={sectionCluster} score={0.85} isWinner={false} />);

    expect(
      screen.getByRole("heading", { name: "Part 1: The Statute of Frauds and the Oral Agreement" })
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Application to Agreement:" })).toBeInTheDocument();
  });

  it("emphasizes plain prose labels and transition phrases", () => {
    const proseCluster = {
      ...CLUSTER,
      centroid_response_text:
        "Conclusion on Statute of Frauds: The oral agreement is barred.\n\nIn conclusion, the evidence supports the statutory analysis.",
    };
    render(<CentroidCard cluster={proseCluster} score={0.85} isWinner={false} />);

    expect(screen.getByText("Conclusion on Statute of Frauds:").tagName.toLowerCase()).toBe(
      "strong"
    );
    expect(screen.getByText("In conclusion").tagName.toLowerCase()).toBe("strong");
  });

  it("renders markdown bullet lists", () => {
    const listCluster = {
      ...CLUSTER,
      centroid_response_text: "- One-year rule applies\n- Writing is required",
    };
    render(<CentroidCard cluster={listCluster} score={0.85} isWinner={false} />);

    const list = screen.getByRole("list");
    expect(within(list).getByText("One-year rule applies")).toBeInTheDocument();
    expect(within(list).getByText("Writing is required")).toBeInTheDocument();
  });

  it("renders simple markdown tables", () => {
    const tableCluster = {
      ...CLUSTER,
      centroid_response_text: "| Issue | Conclusion |\n|---|---|\n| Statute of frauds | Barred |",
    };
    render(<CentroidCard cluster={tableCluster} score={0.85} isWinner={false} />);

    const table = screen.getByRole("table");
    expect(within(table).getByRole("columnheader", { name: "Issue" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "Conclusion" })).toBeInTheDocument();
    expect(within(table).getByText("Statute of frauds")).toBeInTheDocument();
    expect(within(table).getByText("Barred")).toBeInTheDocument();
    expect(screen.queryByText(/\|---\|---\|/)).not.toBeInTheDocument();
  });

  it("renders pipe table rows even when the trailing pipe is missing", () => {
    const tableCluster = {
      ...CLUSTER,
      centroid_response_text:
        "| Issue | Governing rule | Application | Conclusion |\n|---|---|---|---|\n| Whether the oral contract is barred | The one-year rule requires a writing | The agreement ran five years | Barred",
    };
    render(<CentroidCard cluster={tableCluster} score={0.85} isWinner={false} />);

    const table = screen.getByRole("table");
    expect(within(table).getByText("Whether the oral contract is barred")).toBeInTheDocument();
    expect(within(table).getByText("The one-year rule requires a writing")).toBeInTheDocument();
    expect(within(table).getByText("The agreement ran five years")).toBeInTheDocument();
    expect(within(table).getByText("Barred")).toBeInTheDocument();
  });

  it("shows an empty centroid placeholder when text is absent", () => {
    const emptyCluster = { ...CLUSTER, centroid_response_text: null };
    render(<CentroidCard cluster={emptyCluster} score={0.85} isWinner={false} />);

    expect(screen.getByText("results.cluster.emptyCentroid")).toBeInTheDocument();
  });

  it("clamps score display to a valid percentage range", () => {
    const { rerender } = render(<CentroidCard cluster={CLUSTER} score={1.25} isWinner={false} />);
    expect(screen.getByText("100")).toBeInTheDocument();

    rerender(<CentroidCard cluster={CLUSTER} score={-0.1} isWinner={false} />);
    expect(screen.getByText("0")).toBeInTheDocument();
  });
});
