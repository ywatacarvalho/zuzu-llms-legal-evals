import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";

import { LanguageSwitcher } from "@/components/ui/LanguageSwitcher";
import { ThemeSwitcher } from "@/components/ui/ThemeSwitcher";

const ROUTE_TITLES: Record<string, string> = {
  "/": "nav.dashboard",
  "/cases": "nav.cases",
  "/evaluations": "nav.evaluations",
  "/results": "nav.results",
  "/settings": "nav.settings",
};

export function Header() {
  const { t } = useTranslation();
  const { pathname } = useLocation();

  const titleKey = ROUTE_TITLES[pathname] ?? "nav.dashboard";

  return (
    <header className="fixed left-56 right-0 top-0 z-30 flex h-14 items-center border-b border-border/50 bg-background/80 px-6 backdrop-blur-md">
      <h2 className="flex-1 text-sm font-medium text-foreground">{t(titleKey)}</h2>
      <div className="flex items-center gap-1">
        <LanguageSwitcher />
        <ThemeSwitcher />
      </div>
    </header>
  );
}
