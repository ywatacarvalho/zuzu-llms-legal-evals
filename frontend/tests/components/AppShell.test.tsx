import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AppShell } from "@/components/layout/AppShell";
import { queryClient } from "@/lib/queryClient";

vi.mock("next-themes", () => ({
  ThemeProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  useTheme: () => ({ theme: "light", setTheme: vi.fn() }),
}));

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    i18n: { changeLanguage: vi.fn() },
  }),
  initReactI18next: { type: "3rdParty", init: vi.fn() },
}));

function renderAppShell() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/"]}>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<div data-testid="outlet-content">Dashboard</div>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("AppShell", () => {
  it("renders without crashing", () => {
    renderAppShell();
    expect(screen.getByTestId("outlet-content")).toBeInTheDocument();
  });

  it("renders the sidebar with the app logo text", () => {
    renderAppShell();
    expect(screen.getByText("LexEval")).toBeInTheDocument();
  });

  it("renders navigation links", () => {
    renderAppShell();
    // Header also renders the active route title, so nav.dashboard may appear twice
    expect(screen.getAllByText("nav.dashboard").length).toBeGreaterThan(0);
    expect(screen.getByText("nav.cases")).toBeInTheDocument();
    expect(screen.getByText("nav.evaluations")).toBeInTheDocument();
    expect(screen.getByText("nav.results")).toBeInTheDocument();
  });
});
