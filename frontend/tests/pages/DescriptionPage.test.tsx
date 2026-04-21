import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DescriptionPage } from "@/pages/description/DescriptionPage";
import type { ModelInfo } from "@/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

vi.mock("@/services/evaluationsApi", () => ({
  listAvailableModels: vi.fn(),
}));

const { listAvailableModels } = await import("@/services/evaluationsApi");

const COMPARISON_MODELS: ModelInfo[] = [
  { id: "LiquidAI/LFM2-24B-A2B", name: "LFM2 24B", provider: "LiquidAI" },
  { id: "openai/gpt-oss-20b", name: "GPT OSS 20B", provider: "OpenAI" },
];

function renderPage() {
  return render(
    <MemoryRouter>
      <DescriptionPage />
    </MemoryRouter>
  );
}

describe("DescriptionPage", () => {
  const scrollIntoView = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = scrollIntoView;
    vi.mocked(listAvailableModels).mockResolvedValue(COMPARISON_MODELS);
  });

  it("loads the implemented comparison model pool from the API service", async () => {
    renderPage();

    await waitFor(() => {
      expect(screen.getByText("LiquidAI/LFM2-24B-A2B")).toBeInTheDocument();
    });

    expect(listAvailableModels).toHaveBeenCalledTimes(1);
    expect(screen.getByText("openai/gpt-oss-20b")).toBeInTheDocument();
    expect(screen.queryByText("google/gemma-3n-E4B-it")).not.toBeInTheDocument();
  });

  it("renders internal model registry and Results weighting guidance", async () => {
    renderPage();

    expect(screen.getByText("description.modelRegistry.title")).toBeInTheDocument();
    expect(screen.getAllByText("deepseek-ai/DeepSeek-V3").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("description.stage9.resultsLabel")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("description.modelRegistry.comparisonNote")).toBeInTheDocument();
    });
  });

  it("renders project authors in last-name alphabetical order", () => {
    vi.mocked(listAvailableModels).mockReturnValue(new Promise(() => {}));
    renderPage();

    const authorKeys = ["carvalho", "chen", "hanlon", "liu", "syed", "tai"];
    const authorNodes = authorKeys.map((key) =>
      screen.getByText(`description.authors.people.${key}.name`)
    );

    expect(screen.getByText("description.authors.title")).toBeInTheDocument();
    expect(screen.getByText("description.authors.people.carvalho.affiliation")).toBeInTheDocument();
    for (let i = 0; i < authorNodes.length - 1; i += 1) {
      expect(
        authorNodes[i].compareDocumentPosition(authorNodes[i + 1]) &
          Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
    }
  });

  it("scrolls to a stage when the stage navigation is clicked", () => {
    vi.mocked(listAvailableModels).mockReturnValue(new Promise(() => {}));
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: /9/i }));

    expect(scrollIntoView).toHaveBeenCalledWith({ behavior: "smooth", block: "start" });
  });
});
