import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SilhouetteChart } from "@/components/analysis/SilhouetteChart";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

vi.mock("recharts", async (importOriginal) => {
  const actual = await importOriginal<typeof import("recharts")>();
  return {
    ...actual,
    ResponsiveContainer: ({ children }: { children: React.ReactNode }) => (
      <div data-testid="responsive-container">{children}</div>
    ),
  };
});

describe("SilhouetteChart", () => {
  it("renders a Recharts line chart card", () => {
    render(
      <SilhouetteChart silhouette_scores_by_k={{ "2": 0.42, "3": 0.61, "4": 0.55 }} selectedK={3} />
    );
    expect(screen.getByText("results.silhouette.title")).toBeInTheDocument();
    expect(screen.getByTestId("responsive-container")).toBeInTheDocument();
  });

  it("does not crash when selectedK is present", () => {
    // The reference line label requires recharts internals — just assert no crash
    expect(() =>
      render(<SilhouetteChart silhouette_scores_by_k={{ "2": 0.42, "3": 0.61 }} selectedK={3} />)
    ).not.toThrow();
  });

  it("renders nothing when silhouette_scores_by_k is null", () => {
    const { container } = render(<SilhouetteChart silhouette_scores_by_k={null} selectedK={3} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when silhouette_scores_by_k is empty", () => {
    const { container } = render(<SilhouetteChart silhouette_scores_by_k={{}} selectedK={3} />);
    expect(container.firstChild).toBeNull();
  });
});
