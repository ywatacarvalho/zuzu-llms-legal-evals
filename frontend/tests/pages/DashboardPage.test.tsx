import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { DashboardPage } from "@/pages/DashboardPage";
import type { DashboardStats } from "@/types";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
}));

vi.mock("@/services/dashboardApi", () => ({
  getDashboardStats: vi.fn(),
}));

const { getDashboardStats } = await import("@/services/dashboardApi");

const MOCK_STATS: DashboardStats = {
  total_cases: 12,
  evaluations_run: 34,
  models_evaluated: 4,
  avg_clusters: 3.2,
};

function renderPage() {
  return render(
    <MemoryRouter>
      <DashboardPage />
    </MemoryRouter>
  );
}

describe("DashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    vi.mocked(getDashboardStats).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("dashboard.kpi.totalCases")).toBeInTheDocument();
  });

  it("renders all four KPI cards with live data", async () => {
    vi.mocked(getDashboardStats).mockResolvedValue(MOCK_STATS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("12")).toBeInTheDocument();
    });
    expect(screen.getByText("34")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("3.2")).toBeInTheDocument();
  });

  it("shows KPI labels", async () => {
    vi.mocked(getDashboardStats).mockResolvedValue(MOCK_STATS);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.kpi.totalCases")).toBeInTheDocument();
    });
    expect(screen.getByText("dashboard.kpi.evaluationsRun")).toBeInTheDocument();
    expect(screen.getByText("dashboard.kpi.modelsEvaluated")).toBeInTheDocument();
    expect(screen.getByText("dashboard.kpi.avgClusters")).toBeInTheDocument();
  });

  it("shows em-dash placeholders while loading", () => {
    vi.mocked(getDashboardStats).mockReturnValue(new Promise(() => {}));
    renderPage();
    const dashes = screen.getAllByText("—");
    expect(dashes.length).toBeGreaterThanOrEqual(4);
  });

  it("shows error message when fetch fails", async () => {
    vi.mocked(getDashboardStats).mockRejectedValue(new Error("Network error"));
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("dashboard.statsError")).toBeInTheDocument();
    });
  });
});
