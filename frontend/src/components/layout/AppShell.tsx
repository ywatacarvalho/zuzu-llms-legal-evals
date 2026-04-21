import { ThemeProvider } from "next-themes";
import { Outlet } from "react-router-dom";

import { branding } from "@/config/branding";

import { Header } from "./Header";
import { Sidebar } from "./Sidebar";

export function AppShell() {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme={branding.defaultTheme}
      enableSystem={false}
      themes={["light", "dark", "clean"]}
    >
      <div className="min-h-screen bg-background">
        <Sidebar />
        <div className="ml-56 flex min-h-screen flex-col">
          <Header />
          <main className="flex-1 px-6 pb-8 pt-20">
            <Outlet />
          </main>
        </div>
      </div>
    </ThemeProvider>
  );
}
